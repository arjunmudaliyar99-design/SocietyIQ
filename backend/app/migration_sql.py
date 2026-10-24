"""Run a multi-statement SQL script from an Alembic migration.

asyncpg runs one statement per call, so split on ';' at line end, but not inside
dollar-quoted bodies ($$ or $f$). Plain SQL keeps RLS policies and grants readable.
"""

import re

from alembic import op

_DOLLAR = re.compile(r"\$[a-z]*\$")


def execute_script(sql: str) -> None:
    statement: list[str] = []
    in_dollar = False
    for line in sql.splitlines():
        statement.append(line)
        if len(_DOLLAR.findall(line)) % 2 == 1:
            in_dollar = not in_dollar
        if not in_dollar and line.rstrip().endswith(";"):
            text = "\n".join(statement).strip()
            if text and not all(x.strip().startswith("--") for x in text.splitlines()):
                op.execute(text)
            statement = []


STANDARD_POLICY = """
ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {t} FORCE ROW LEVEL SECURITY;
CREATE POLICY society_isolation ON {t}
  USING (society_id = app_current_society())
  WITH CHECK (society_id = app_current_society());
"""


def enable_society_isolation(table: str) -> None:
    """The standard policy of docs/04 §6 for a table with a society_id column."""
    execute_script(STANDARD_POLICY.format(t=table))
