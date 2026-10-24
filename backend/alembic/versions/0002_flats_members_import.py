"""M3: flats, members, attachments, import jobs, ledger entries (docs/05 §2, §4, §5, §8).

Revision ID: 0002
Revises: 0001
"""

from app.migration_sql import enable_society_isolation, execute_script

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

UPGRADE = r"""
CREATE TABLE flats (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  wing_id uuid NOT NULL REFERENCES wings(id),
  flat_number text NOT NULL,
  carpet_area_sqft numeric(9,2) CHECK (carpet_area_sqft > 0),
  flat_type text,
  usage text NOT NULL DEFAULT 'residential' CHECK (usage IN ('residential','commercial')),
  certified_construction_cost_paise bigint CHECK (certified_construction_cost_paise >= 0),
  water_points numeric(6,2) CHECK (water_points >= 0),
  municipal_property_account text,
  occupancy text NOT NULL DEFAULT 'owner_occupied'
    CHECK (occupancy IN ('owner_occupied','family_occupied','let_out','vacant')),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (society_id, wing_id, flat_number)
);
CREATE INDEX flats_society ON flats (society_id);

CREATE TABLE members (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  flat_id uuid NOT NULL REFERENCES flats(id),
  full_name text NOT NULL,
  phone_e164 text,
  email text,
  member_type text NOT NULL CHECK (member_type IN ('owner','joint_owner','tenant','delegate')),
  is_primary boolean NOT NULL DEFAULT false,
  user_id uuid REFERENCES users(id),
  from_date date,
  to_date date,
  tenant_can_pay boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid,
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (to_date IS NULL OR from_date IS NULL OR to_date >= from_date)
);
CREATE INDEX members_society_flat ON members (society_id, flat_id);

CREATE TABLE attachments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  owner_type text NOT NULL,
  owner_id uuid,
  storage_path text NOT NULL,
  mime text NOT NULL,
  size_bytes int NOT NULL,
  sha256 text NOT NULL,
  original_filename text,
  uploaded_by uuid,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX attachments_society_sha ON attachments (society_id, sha256);

CREATE TABLE import_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  kind text NOT NULL CHECK (kind IN ('flats_members')),
  attachment_id uuid REFERENCES attachments(id),
  status text NOT NULL CHECK (status IN ('uploaded','previewed','imported','failed')),
  row_count int NOT NULL DEFAULT 0,
  ok_count int NOT NULL DEFAULT 0,
  error_count int NOT NULL DEFAULT 0,
  preview jsonb NOT NULL DEFAULT '{}',
  created_by uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Append-only: the app role gets no UPDATE or DELETE (docs/05 §4).
CREATE TABLE ledger_entries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  flat_id uuid NOT NULL REFERENCES flats(id),
  entry_date date NOT NULL,
  entry_type text NOT NULL
    CHECK (entry_type IN ('opening_balance','bill','interest','payment','adjustment','reversal')),
  amount_paise bigint NOT NULL,
  source_type text NOT NULL,
  source_id uuid,
  reverses_entry_id uuid REFERENCES ledger_entries(id),
  reason text,
  created_by uuid,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ledger_entries_society_flat ON ledger_entries (society_id, flat_id);
-- A flat has at most one opening balance; corrections are reversals plus a new entry.
CREATE UNIQUE INDEX ledger_one_opening_balance ON ledger_entries (flat_id)
  WHERE entry_type = 'opening_balance';

-- Memberships of owners, tenants and delegates point at a real flat now.
ALTER TABLE society_memberships
  ADD CONSTRAINT society_memberships_flat_fk FOREIGN KEY (flat_id) REFERENCES flats(id);

GRANT SELECT, INSERT, UPDATE ON flats, members, import_jobs TO app_backend;
GRANT SELECT, INSERT ON attachments, ledger_entries TO app_backend;
"""

SOCIETY_TABLES = ["flats", "members", "attachments", "import_jobs", "ledger_entries"]


DOWNGRADE = """
ALTER TABLE society_memberships DROP CONSTRAINT IF EXISTS society_memberships_flat_fk;
DROP TABLE IF EXISTS ledger_entries, import_jobs, attachments, members, flats CASCADE;
"""


def upgrade() -> None:
    execute_script(UPGRADE)
    for table in SOCIETY_TABLES:
        enable_society_isolation(table)


def downgrade() -> None:
    execute_script(DOWNGRADE)
