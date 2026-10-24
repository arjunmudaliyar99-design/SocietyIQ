"""M8: complaints and complaint updates (docs/05 §5).

Revision ID: 0005
Revises: 0004
"""

from app.migration_sql import enable_society_isolation, execute_script

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

UPGRADE = r"""
CREATE TABLE complaints (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  flat_id uuid REFERENCES flats(id),
  raised_by_user_id uuid REFERENCES users(id),
  raised_on_behalf boolean NOT NULL DEFAULT false,
  category text NOT NULL
    CHECK (category IN ('water','lift','electricity','cleaning','security','parking','other')),
  location text NOT NULL CHECK (location IN ('my_flat','common_area')),
  description text,
  status text NOT NULL DEFAULT 'open'
    CHECK (status IN ('open','in_progress','resolved','closed')),
  assigned_to_text text,
  resident_feedback text CHECK (resident_feedback IN ('fixed','not_fixed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz,
  closed_at timestamptz,
  -- A problem inside a flat must say which flat.
  CHECK (location <> 'my_flat' OR flat_id IS NOT NULL)
);
CREATE INDEX complaints_society_flat ON complaints (society_id, flat_id);
CREATE INDEX complaints_society_status ON complaints (society_id, status);

CREATE TABLE complaint_updates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  complaint_id uuid NOT NULL REFERENCES complaints(id),
  author_user_id uuid REFERENCES users(id),
  message text NOT NULL,
  new_status text CHECK (new_status IN ('open','in_progress','resolved','closed')),
  visible_to_resident boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX complaint_updates_complaint ON complaint_updates (complaint_id, created_at);

GRANT SELECT, INSERT, UPDATE ON complaints TO app_backend;
-- The history is append-only: a correction is a new update.
GRANT SELECT, INSERT ON complaint_updates TO app_backend;
"""

SOCIETY_TABLES = ["complaints", "complaint_updates"]

DOWNGRADE = """
DROP TABLE IF EXISTS complaint_updates, complaints CASCADE;
"""


def upgrade() -> None:
    execute_script(UPGRADE)
    for table in SOCIETY_TABLES:
        enable_society_isolation(table)


def downgrade() -> None:
    execute_script(DOWNGRADE)
