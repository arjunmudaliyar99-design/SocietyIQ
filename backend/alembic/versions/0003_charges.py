"""M4: charge heads, per-flat overrides, parking allotments, property tax (docs/05 §3).

Revision ID: 0003
Revises: 0002
"""

from app.migration_sql import enable_society_isolation, execute_script

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

UPGRADE = r"""
CREATE TABLE charge_heads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  name text NOT NULL,
  code text NOT NULL,
  standard_code text CHECK (standard_code IN ('service','property_tax','water','lift','parking',
    'non_occupancy','insurance','lease_rent','major_repair','sinking_fund','repair_fund',
    'election_fund','education_fund','welfare_fund','other')),
  calc_type text NOT NULL CHECK (calc_type IN ('equal_per_flat','equal_per_flat_with_lift',
    'per_carpet_area','per_water_point','as_assessed_per_flat','pct_of_head',
    'pct_of_construction_cost','per_parking_allotment','per_member_fixed','fixed_per_flat',
    'custom_per_flat','voluntary')),
  period_total_paise bigint CHECK (period_total_paise >= 0),
  fixed_amount_paise bigint CHECK (fixed_amount_paise >= 0),
  percent numeric(7,4) CHECK (percent >= 0),
  percent_of_head_id uuid REFERENCES charge_heads(id),
  applies_to text NOT NULL DEFAULT 'all' CHECK (applies_to IN ('all','let_out_only')),
  gb_resolution_ref text,
  gb_resolution_date date,
  method_deviation_reason text,
  frequency text NOT NULL DEFAULT 'every_bill' CHECK (frequency IN ('every_bill','one_time')),
  one_time_period date,
  sort_order smallint NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  approved_by uuid,
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (society_id, code),
  CHECK (frequency <> 'one_time' OR one_time_period IS NOT NULL)
);

CREATE TABLE flat_charge_overrides (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  flat_id uuid NOT NULL REFERENCES flats(id),
  charge_head_id uuid NOT NULL REFERENCES charge_heads(id),
  amount_paise bigint NOT NULL CHECK (amount_paise >= 0),
  reason text NOT NULL CHECK (length(trim(reason)) > 0),
  valid_from date NOT NULL,
  valid_to date,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid,
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (valid_to IS NULL OR valid_to >= valid_from)
);
CREATE INDEX flat_charge_overrides_flat ON flat_charge_overrides (society_id, flat_id);

CREATE TABLE parking_allotments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  flat_id uuid NOT NULL REFERENCES flats(id),
  slot_label text NOT NULL,
  slot_type text NOT NULL
    CHECK (slot_type IN ('open','stilt','covered','podium','mechanical','other')),
  vehicle_type text NOT NULL CHECK (vehicle_type IN ('two_wheeler','four_wheeler','other')),
  vehicle_number text,
  monthly_rate_paise bigint NOT NULL CHECK (monthly_rate_paise >= 0),
  from_date date NOT NULL,
  to_date date,
  gb_resolution_ref text,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid,
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (to_date IS NULL OR to_date >= from_date)
);
CREATE INDEX parking_allotments_flat ON parking_allotments (society_id, flat_id);

-- Amounts are copied from the municipal bill; SocietyIQ never computes municipal tax.
-- Append-only: a correction is a new row; the newest row per flat and year is used.
CREATE TABLE property_tax_assessments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  flat_id uuid REFERENCES flats(id),
  authority text NOT NULL,
  financial_year text NOT NULL CHECK (financial_year ~ '^\d{4}-\d{2}$'),
  annual_amount_paise bigint NOT NULL CHECK (annual_amount_paise >= 0),
  is_exempt boolean NOT NULL DEFAULT false,
  exemption_reason text,
  source_document_id uuid REFERENCES attachments(id),
  entered_by uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (NOT is_exempt OR (annual_amount_paise = 0 AND exemption_reason IS NOT NULL))
);
CREATE INDEX property_tax_flat_year
  ON property_tax_assessments (society_id, flat_id, financial_year);

ALTER TABLE import_jobs DROP CONSTRAINT import_jobs_kind_check;
ALTER TABLE import_jobs ADD CONSTRAINT import_jobs_kind_check
  CHECK (kind IN ('flats_members','property_tax'));

GRANT SELECT, INSERT, UPDATE ON charge_heads, flat_charge_overrides, parking_allotments
  TO app_backend;
GRANT SELECT, INSERT ON property_tax_assessments TO app_backend;
"""

SOCIETY_TABLES = [
    "charge_heads",
    "flat_charge_overrides",
    "parking_allotments",
    "property_tax_assessments",
]

DOWNGRADE = """
ALTER TABLE import_jobs DROP CONSTRAINT import_jobs_kind_check;
ALTER TABLE import_jobs ADD CONSTRAINT import_jobs_kind_check CHECK (kind IN ('flats_members'));
DROP TABLE IF EXISTS property_tax_assessments, parking_allotments, flat_charge_overrides,
  charge_heads CASCADE;
"""


def upgrade() -> None:
    execute_script(UPGRADE)
    for table in SOCIETY_TABLES:
        enable_society_isolation(table)


def downgrade() -> None:
    execute_script(DOWNGRADE)
