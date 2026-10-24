"""uv run python -m app.seed — load the fictional demo societies (idempotent)."""

import asyncio

from app.config import get_settings
from app.seed.demo import DEMO_ADMIN_EMAIL, DEMO_RESIDENT_EMAIL, run


def main() -> None:
    if get_settings().app_env == "production":
        raise SystemExit("The demo seed never runs in production.")
    report = asyncio.run(run())
    print(
        f"Societies created: {report.societies_created}; flats created: {report.flats_created}; "
        f"opening balances created: {report.balances_created}; "
        f"charge heads created: {report.heads_created}; "
        f"compliance items created: {report.compliance_created}."
    )
    print(f"Demo logins (local dev sign-in): {DEMO_ADMIN_EMAIL}, {DEMO_RESIDENT_EMAIL}")


if __name__ == "__main__":
    main()
