"""M2: base tables, app_backend role, row-level security (docs/05 §1, §8; docs/04 §6).

Revision ID: 0001
Revises:
"""

import re

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Tables carrying society data; each gets the standard isolation policy unless it has its own.
SOCIETY_TABLES_STANDARD = ["wings"]

UPGRADE = r"""
-- The app role is created here without LOGIN or password; each environment enables login
-- with its own secret password (docs/09 §6a).
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_backend') THEN
    CREATE ROLE app_backend NOLOGIN NOBYPASSRLS;
  END IF;
END $$;

GRANT USAGE ON SCHEMA public TO app_backend;

-- Tenant context set per transaction with SET LOCAL / set_config(..., true).
-- An unset custom setting reads as '' after a transaction, so nullif before the cast.
CREATE FUNCTION app_current_society() RETURNS uuid
  LANGUAGE sql STABLE
  AS $f$ SELECT nullif(current_setting('app.current_society_id', true), '')::uuid $f$;

CREATE FUNCTION app_current_user() RETURNS uuid
  LANGUAGE sql STABLE
  AS $f$ SELECT nullif(current_setting('app.current_user_id', true), '')::uuid $f$;

GRANT EXECUTE ON FUNCTION app_current_society(), app_current_user() TO app_backend;

CREATE TABLE users (
  id uuid PRIMARY KEY,
  full_name text,
  email text UNIQUE,
  phone_e164 text UNIQUE,
  preferred_language text NOT NULL DEFAULT 'en'
    CHECK (preferred_language IN ('en','mr','hi','gu','ta')),
  text_size text NOT NULL DEFAULT 'normal' CHECK (text_size IN ('normal','large','xlarge')),
  simple_mode boolean NOT NULL DEFAULT true,
  analytics_opt_out boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE societies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  registration_number text,
  address_line text,
  city text,
  state text NOT NULL DEFAULT 'Maharashtra',
  pincode text,
  financial_year_start_month smallint NOT NULL DEFAULT 4
    CHECK (financial_year_start_month BETWEEN 1 AND 12),
  default_language text NOT NULL DEFAULT 'en'
    CHECK (default_language IN ('en','mr','hi','gu','ta')),
  billing_frequency text NOT NULL DEFAULT 'monthly'
    CHECK (billing_frequency IN ('monthly','quarterly')),
  bill_day smallint CHECK (bill_day BETWEEN 1 AND 28),
  due_days smallint NOT NULL DEFAULT 15,
  upi_id text,
  upi_payee_name text,
  bank_name text,
  bank_account_last4 text,
  interest_enabled boolean NOT NULL DEFAULT false,
  interest_rate_annual_pct numeric(7,4),
  interest_gb_resolution_date date,
  interest_grace_days smallint,
  rounding_rule text NOT NULL DEFAULT 'nearest_rupee'
    CHECK (rounding_rule IN ('none','nearest_rupee')),
  auto_approve_billing boolean NOT NULL DEFAULT false,
  plan text NOT NULL DEFAULT 'pilot',
  champion_name text,
  champion_phone_e164 text,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE wings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  name text NOT NULL,
  has_lift boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (society_id, name)
);

-- flat_id has no FK yet: flats arrive in M3, which adds the constraint.
CREATE TABLE society_memberships (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  user_id uuid REFERENCES users(id),
  role text NOT NULL CHECK (role IN
    ('admin','treasurer','committee','consultant','auditor','owner','tenant','delegate')),
  flat_id uuid,
  status text NOT NULL CHECK (status IN ('invited','active','removed')),
  invited_name text,
  invited_email text,
  invited_phone_e164 text,
  invite_token_hash text UNIQUE,
  invite_expires_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid,
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (role NOT IN ('owner','tenant','delegate') OR flat_id IS NOT NULL)
);
CREATE UNIQUE INDEX society_memberships_unique
  ON society_memberships (society_id, user_id, role, flat_id) NULLS NOT DISTINCT
  WHERE user_id IS NOT NULL;
CREATE INDEX society_memberships_user ON society_memberships (user_id);

CREATE TABLE audit_log (
  id bigserial PRIMARY KEY,
  society_id uuid REFERENCES societies(id),
  actor_user_id uuid,
  action text NOT NULL,
  entity_type text NOT NULL,
  entity_id uuid,
  before jsonb,
  after jsonb,
  reason text,
  ip inet,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_log_society ON audit_log (society_id, created_at);

CREATE TABLE consents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id),
  society_id uuid REFERENCES societies(id),
  purpose text NOT NULL CHECK (purpose IN ('terms','privacy','analytics','notifications')),
  policy_version text NOT NULL,
  granted_at timestamptz NOT NULL DEFAULT now(),
  withdrawn_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE legal_parameters (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code text NOT NULL,
  value numeric NOT NULL,
  applies_when jsonb,
  state text NOT NULL DEFAULT 'Maharashtra',
  effective_from date NOT NULL,
  effective_to date,
  source text NOT NULL,
  verified_by text,
  verified_on date,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Seed from docs/08 §3. Unverified until the consultant or a lawyer checks them.
-- effective_from: Amendment Rules 2026 in force from 18 June 2026 (docs/08 §1).
INSERT INTO legal_parameters (code, value, applies_when, effective_from, source) VALUES
  ('interest_max_annual_pct', 12, NULL, '2026-06-18', 'MCS Rules 106C-12 (2026)'),
  ('non_occupancy_pct_of_service', 10, NULL, '2026-06-18',
   'MCS Rules 106C-12 (2026); earlier Govt order of Aug 2001 under s.79A'),
  ('sinking_fund_min_annual_pct', 0.25, NULL, '2026-06-18', 'MCS Rules 106C-11 (2026)'),
  ('repair_fund_min_annual_pct', 0.75, NULL, '2026-06-18', 'MCS Rules 106C-11 (2026)'),
  ('education_fund_per_member_month_paise', 1000, NULL, '2026-06-18', 'MCS Rules 106C-7 (2026)'),
  ('committee_repair_limit_paise', 10000000, '{"members_min": 1, "members_max": 25}',
   '2026-06-18', 'MCS Rules 106C-13 (2026)'),
  ('committee_repair_limit_paise', 20000000, '{"members_min": 26, "members_max": 50}',
   '2026-06-18', 'MCS Rules 106C-13 (2026)'),
  ('committee_repair_limit_paise', 30000000, '{"members_min": 51, "members_max": 100}',
   '2026-06-18', 'MCS Rules 106C-13 (2026)'),
  ('committee_repair_limit_paise', 40000000, '{"members_min": 101, "members_max": 1000}',
   '2026-06-18', 'MCS Rules 106C-13 (2026)'),
  ('committee_repair_limit_paise', 50000000, '{"members_min": 1001}',
   '2026-06-18', 'MCS Rules 106C-13 (2026)');

-- Grants: no DELETE anywhere; audit_log is insert-only (docs/05 §8).
GRANT SELECT, INSERT, UPDATE ON users, societies, wings, society_memberships, consents
  TO app_backend;
GRANT SELECT, INSERT ON audit_log TO app_backend;
GRANT USAGE ON SEQUENCE audit_log_id_seq TO app_backend;
GRANT SELECT ON legal_parameters TO app_backend;

-- Row-level security (docs/04 §6, docs/05 §10). FORCE so even the owner is filtered.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;
CREATE POLICY own_row ON users
  USING (id = app_current_user()) WITH CHECK (id = app_current_user());

ALTER TABLE consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE consents FORCE ROW LEVEL SECURITY;
CREATE POLICY own_rows ON consents
  USING (user_id = app_current_user()) WITH CHECK (user_id = app_current_user());

-- Picker: a user sees their own memberships across societies; inside a society, all of it.
ALTER TABLE society_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE society_memberships FORCE ROW LEVEL SECURITY;
CREATE POLICY society_isolation ON society_memberships
  USING (user_id = app_current_user() OR society_id = app_current_society())
  WITH CHECK (society_id = app_current_society());

-- A society row is visible in its own context, or for the picker when the user is an
-- active member. Writes only in its own context.
ALTER TABLE societies ENABLE ROW LEVEL SECURITY;
ALTER TABLE societies FORCE ROW LEVEL SECURITY;
CREATE POLICY society_isolation ON societies
  USING (
    id = app_current_society()
    OR id IN (SELECT society_id FROM society_memberships
              WHERE user_id = app_current_user() AND status = 'active')
  )
  WITH CHECK (id = app_current_society());

-- Rows without a society (e.g. preference changes) belong to the acting user.
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;
CREATE POLICY society_isolation ON audit_log
  USING (society_id = app_current_society()
         OR (society_id IS NULL AND actor_user_id = app_current_user()))
  WITH CHECK (society_id = app_current_society()
              OR (society_id IS NULL AND actor_user_id = app_current_user()));
"""

STANDARD_POLICY = """
ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {t} FORCE ROW LEVEL SECURITY;
CREATE POLICY society_isolation ON {t}
  USING (society_id = app_current_society())
  WITH CHECK (society_id = app_current_society());
"""

DOWNGRADE = """
DROP TABLE IF EXISTS legal_parameters, consents, audit_log, society_memberships, wings,
  societies, users CASCADE;
DROP FUNCTION IF EXISTS app_current_society(), app_current_user();
"""


def _execute_script(sql: str) -> None:
    # asyncpg runs one statement per call. Split on ';' at line end, but not inside
    # dollar-quoted bodies ($$ or $f$).
    statement: list[str] = []
    in_dollar = False
    for line in sql.splitlines():
        statement.append(line)
        if len(re.findall(r"\$[a-z]*\$", line)) % 2 == 1:
            in_dollar = not in_dollar
        if not in_dollar and line.rstrip().endswith(";"):
            text = "\n".join(statement).strip()
            if text and not all(x.strip().startswith("--") for x in text.splitlines()):
                op.execute(text)
            statement = []


def upgrade() -> None:
    _execute_script(UPGRADE)
    for table in SOCIETY_TABLES_STANDARD:
        _execute_script(STANDARD_POLICY.format(t=table))


def downgrade() -> None:
    _execute_script(DOWNGRADE)
