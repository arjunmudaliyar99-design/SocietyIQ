"""M9: notices, notice reads, notification log (docs/05 §5, §8).

Revision ID: 0007_notices
Revises: 0005_compliance
"""

from app.migration_sql import enable_society_isolation, execute_script

revision = "0007_notices"
down_revision = "0005_compliance"
branch_labels = None
depends_on = None

UPGRADE = r"""
CREATE TABLE notices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  title text NOT NULL,
  body text NOT NULL,
  language text NOT NULL DEFAULT 'en' CHECK (language IN ('en','mr','hi','gu','ta')),
  translations jsonb NOT NULL DEFAULT '{}',
  audience text NOT NULL DEFAULT 'all' CHECK (audience IN ('all','owners','tenants','wing')),
  audience_wing_id uuid REFERENCES wings(id),
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published','archived')),
  ai_assisted boolean NOT NULL DEFAULT false,
  published_at timestamptz,
  published_by uuid REFERENCES users(id),
  created_by uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (audience <> 'wing' OR audience_wing_id IS NOT NULL),
  CHECK (status <> 'published' OR published_at IS NOT NULL)
);
CREATE INDEX notices_society_status ON notices (society_id, status, published_at DESC);

-- docs/05 gives (notice_id, user_id, read_at); society_id is added so RLS applies.
CREATE TABLE notice_reads (
  notice_id uuid NOT NULL REFERENCES notices(id),
  user_id uuid NOT NULL REFERENCES users(id),
  society_id uuid NOT NULL REFERENCES societies(id),
  read_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (notice_id, user_id)
);

CREATE TABLE notification_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id uuid NOT NULL REFERENCES societies(id),
  channel text NOT NULL CHECK (channel IN ('email','sms','whatsapp','in_app')),
  template text NOT NULL,
  language text NOT NULL,
  to_member_id uuid REFERENCES members(id),
  to_address_masked text NOT NULL,
  -- What the message was about, so a notice's sends can be counted.
  source_type text,
  source_id uuid,
  status text NOT NULL CHECK (status IN ('sent','failed','skipped')),
  provider_message_id text,
  error text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX notification_log_source ON notification_log (society_id, source_type, source_id);

GRANT SELECT, INSERT, UPDATE ON notices TO app_backend;
GRANT SELECT, INSERT ON notice_reads TO app_backend;
-- A log: never changed after the send.
GRANT SELECT, INSERT ON notification_log TO app_backend;
"""

SOCIETY_TABLES = ["notices", "notice_reads", "notification_log"]

DOWNGRADE = """
DROP TABLE IF EXISTS notification_log, notice_reads, notices CASCADE;
"""


def upgrade() -> None:
    execute_script(UPGRADE)
    for table in SOCIETY_TABLES:
        enable_society_isolation(table)


def downgrade() -> None:
    execute_script(DOWNGRADE)
