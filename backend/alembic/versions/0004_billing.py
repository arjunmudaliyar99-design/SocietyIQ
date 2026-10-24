"""M5: billing runs, bills, bill lines, gap-free numbering, job runs (docs/05 §3, §8).

Revision ID: 0004
Revises: 0003
"""

from app.migration_sql import enable_society_isolation, execute_script

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

UPGRADE = r"""
CREATE TABLE billing_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  period_start date NOT NULL,
  period_end date NOT NULL,
  bill_date date NOT NULL,
  due_date date NOT NULL,
  status text NOT NULL CHECK (status IN ('draft','approved','sent','cancelled')),
  flat_count int NOT NULL DEFAULT 0,
  total_paise bigint NOT NULL DEFAULT 0,
  warnings jsonb NOT NULL DEFAULT '[]',
  charges_snapshot jsonb NOT NULL DEFAULT '{}',
  created_by_job boolean NOT NULL DEFAULT false,
  approved_by uuid,
  approved_at timestamptz,
  sent_at timestamptz,
  cancelled_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid,
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (period_end >= period_start),
  CHECK (due_date >= bill_date)
);
-- One live run per period; the scheduled job relies on this to be idempotent.
CREATE UNIQUE INDEX billing_runs_one_per_period ON billing_runs (society_id, period_start)
  WHERE status <> 'cancelled';

CREATE TABLE bills (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  billing_run_id uuid NOT NULL REFERENCES billing_runs(id),
  flat_id uuid NOT NULL REFERENCES flats(id),
  bill_number text NOT NULL,
  period_start date NOT NULL,
  period_end date NOT NULL,
  bill_date date NOT NULL,
  due_date date NOT NULL,
  charges_paise bigint NOT NULL CHECK (charges_paise >= 0),
  arrears_paise bigint NOT NULL CHECK (arrears_paise >= 0),
  advance_paise bigint NOT NULL DEFAULT 0 CHECK (advance_paise >= 0),
  interest_paise bigint NOT NULL DEFAULT 0 CHECK (interest_paise >= 0),
  total_due_paise bigint NOT NULL CHECK (total_due_paise >= 0),
  status text NOT NULL CHECK (status IN ('issued','partially_paid','paid','cancelled')),
  cancelled_reason text,
  cancelled_at timestamptz,
  replaces_bill_id uuid REFERENCES bills(id),
  pdf_path text,
  language text NOT NULL DEFAULT 'en',
  member_name text,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid,
  UNIQUE (society_id, bill_number),
  CHECK (status <> 'cancelled' OR cancelled_reason IS NOT NULL)
);
CREATE INDEX bills_society_flat ON bills (society_id, flat_id);
CREATE INDEX bills_society_status ON bills (society_id, status);
CREATE INDEX bills_run ON bills (billing_run_id);

CREATE TABLE bill_lines (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  bill_id uuid NOT NULL REFERENCES bills(id),
  society_id uuid NOT NULL REFERENCES societies(id),
  charge_head_id uuid REFERENCES charge_heads(id),
  line_type text NOT NULL DEFAULT 'charge' CHECK (line_type IN ('charge','rounding','interest')),
  description text NOT NULL,
  amount_paise bigint NOT NULL,
  sort_order smallint NOT NULL DEFAULT 0
);
CREATE INDEX bill_lines_bill ON bill_lines (bill_id);

CREATE TABLE number_sequences (
  society_id uuid NOT NULL REFERENCES societies(id),
  kind text NOT NULL CHECK (kind IN ('bill','receipt')),
  financial_year text NOT NULL,
  next_value int NOT NULL DEFAULT 1 CHECK (next_value >= 1),
  PRIMARY KEY (society_id, kind, financial_year)
);

-- System table, not society data: one row per scheduled job run.
CREATE TABLE job_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_name text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  status text NOT NULL CHECK (status IN ('running','succeeded','failed')),
  details jsonb NOT NULL DEFAULT '{}'
);

-- The scheduler must find societies whose bill day is today without a society context.
-- Read-only and only when the request marks itself as the scheduler (docs/04 §13).
CREATE POLICY scheduler_read ON societies FOR SELECT
  USING (current_setting('app.job', true) = 'scheduler');

GRANT SELECT, INSERT, UPDATE ON billing_runs, bills, number_sequences TO app_backend;
GRANT SELECT, INSERT ON bill_lines TO app_backend;
GRANT SELECT, INSERT, UPDATE ON job_runs TO app_backend;
"""

SOCIETY_TABLES = ["billing_runs", "bills", "bill_lines", "number_sequences"]

DOWNGRADE = """
DROP POLICY IF EXISTS scheduler_read ON societies;
DROP TABLE IF EXISTS job_runs, number_sequences, bill_lines, bills, billing_runs CASCADE;
"""


def upgrade() -> None:
    execute_script(UPGRADE)
    for table in SOCIETY_TABLES:
        enable_society_isolation(table)


def downgrade() -> None:
    execute_script(DOWNGRADE)
