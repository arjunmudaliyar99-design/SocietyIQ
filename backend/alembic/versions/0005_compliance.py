"""M10: vendors, compliance items and events (docs/05 §6), compliance reminders.

Revision ID: 0005_compliance
Revises: 0005_complaints
"""

from app.migration_sql import enable_society_isolation, execute_script

revision = "0005_compliance"
down_revision = "0005_complaints"
branch_labels = None
depends_on = None

UPGRADE = r"""
CREATE TABLE vendors (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  name text NOT NULL CHECK (length(trim(name)) > 0),
  category text,
  phone_e164 text,
  email text,
  gstin text,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX vendors_society_name ON vendors (society_id, lower(name));

CREATE TABLE compliance_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  item_type text NOT NULL CHECK (item_type IN ('fire_audit','structural_audit','lift_amc',
    'pump_amc','generator_service','tank_cleaning','cctv_amc','insurance','pest_control','other')),
  title text NOT NULL CHECK (length(trim(title)) > 0),
  vendor_id uuid REFERENCES vendors(id),
  last_done_on date,
  next_due_on date NOT NULL,
  repeat_months smallint CHECK (repeat_months IS NULL OR repeat_months BETWEEN 1 AND 120),
  contract_value_paise bigint CHECK (contract_value_paise IS NULL OR contract_value_paise >= 0),
  notes text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX compliance_items_society_due ON compliance_items (society_id, next_due_on);

-- History of "marked done"; never edited or deleted.
CREATE TABLE compliance_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  compliance_item_id uuid NOT NULL REFERENCES compliance_items(id),
  done_on date NOT NULL,
  notes text,
  recorded_by uuid,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX compliance_events_item ON compliance_events (compliance_item_id);

-- One row per reminder step per due date (docs/06 §9), so the daily job is idempotent and
-- the committee home can list them. Delivery by email waits for the notify service (M9).
CREATE TABLE compliance_reminders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  compliance_item_id uuid NOT NULL REFERENCES compliance_items(id),
  due_on date NOT NULL,
  days_before smallint NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (compliance_item_id, due_on, days_before)
);

GRANT SELECT, INSERT, UPDATE ON vendors, compliance_items TO app_backend;
GRANT SELECT, INSERT ON compliance_events, compliance_reminders TO app_backend;
"""

SOCIETY_TABLES = ["vendors", "compliance_items", "compliance_events", "compliance_reminders"]

DOWNGRADE = """
DROP TABLE IF EXISTS compliance_reminders, compliance_events, compliance_items, vendors CASCADE;
"""


def upgrade() -> None:
    execute_script(UPGRADE)
    for table in SOCIETY_TABLES:
        enable_society_isolation(table)


def downgrade() -> None:
    execute_script(DOWNGRADE)
