"""M6: payments, allocations, receipts; months pending on opening balances (docs/05 §4).

Revision ID: 0006_payments
Revises: 0005_complaints
"""

from app.migration_sql import enable_society_isolation, execute_script

revision = "0006_payments"
down_revision = "0005_complaints"
branch_labels = None
depends_on = None

UPGRADE = r"""
CREATE TABLE payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  flat_id uuid NOT NULL REFERENCES flats(id),
  amount_paise bigint NOT NULL CHECK (amount_paise > 0),
  method text NOT NULL CHECK (method IN ('cash','cheque','upi','neft','gateway','other')),
  status text NOT NULL CHECK (status IN ('pending','recorded','confirmed','bounced','reversed')),
  received_on date NOT NULL,
  reference text,
  cheque_bank text,
  cheque_date date,
  reported_by_resident boolean NOT NULL DEFAULT false,
  proof_file_path text,
  recorded_by uuid,
  resident_confirmed_at timestamptz,
  confirmed_by uuid,
  confirmed_at timestamptz,
  reversal_of uuid REFERENCES payments(id),
  reason text,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (status <> 'reversed' OR reason IS NOT NULL OR reversal_of IS NOT NULL)
);
CREATE INDEX payments_society_flat ON payments (society_id, flat_id);
CREATE INDEX payments_society_status ON payments (society_id, status);

-- Settles a bill or an opening balance. Undone by setting reversed_at, never deleted.
CREATE TABLE payment_allocations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  payment_id uuid NOT NULL REFERENCES payments(id),
  bill_id uuid REFERENCES bills(id),
  ledger_entry_id uuid REFERENCES ledger_entries(id),
  amount_paise bigint NOT NULL CHECK (amount_paise > 0),
  reversed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((bill_id IS NULL) <> (ledger_entry_id IS NULL))
);
CREATE INDEX payment_allocations_payment ON payment_allocations (payment_id);
CREATE INDEX payment_allocations_bill ON payment_allocations (bill_id);

CREATE TABLE receipts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  payment_id uuid NOT NULL UNIQUE REFERENCES payments(id),
  receipt_number text NOT NULL,
  issued_at timestamptz NOT NULL DEFAULT now(),
  pdf_path text,
  cancelled_at timestamptz,
  cancelled_reason text,
  UNIQUE (society_id, receipt_number)
);

-- How many months an opening balance covers, for dues ageing (docs/06 §6).
ALTER TABLE ledger_entries ADD COLUMN months_pending smallint CHECK (months_pending > 0);

GRANT SELECT, INSERT, UPDATE ON payments, payment_allocations, receipts TO app_backend;
"""

SOCIETY_TABLES = ["payments", "payment_allocations", "receipts"]

DOWNGRADE = """
ALTER TABLE ledger_entries DROP COLUMN IF EXISTS months_pending;
DROP TABLE IF EXISTS receipts, payment_allocations, payments CASCADE;
"""


def upgrade() -> None:
    execute_script(UPGRADE)
    for table in SOCIETY_TABLES:
        enable_society_isolation(table)


def downgrade() -> None:
    execute_script(DOWNGRADE)
