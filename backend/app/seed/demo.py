"""Fictional demo data from docs/02 §12. Safe to run again: it only adds what is missing.

Societies, flats, members and the listed dues (as opening balances). Charges, spending and
compliance items are seeded by the milestones that build those tables (M4, M10, M12).
Bill day 1 and due after 15 days are demo choices, not rules. Logins are @example.com and
work with the local dev sign-in (their user ids match `dev_user_id`).
"""

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthUser, dev_user_id
from app.db import get_sessionmaker, set_society_context, set_user_context
from app.models import Flat, Member, SocietyMembership, User, Wing
from app.services import auth as user_service
from app.services import flats as flat_service
from app.services import ledger
from app.services import societies as society_service
from app.timeutil import today_ist

DEMO_ADMIN_EMAIL = "demo-admin@example.com"
DEMO_RESIDENT_EMAIL = "resident.b207@example.com"
DEMO_RESIDENT_FLAT = ("A", "B-207")  # (society key, flat label) — Shanti Sadan B-207


@dataclass
class SeedSociety:
    key: str
    name: str
    city: str
    flat_count: int
    cost_per_flat_paise: int
    # flat label → dues in rupees (docs/02 §12)
    dues: dict[str, int]
    # wing name → flat numbers; a single unnamed wing uses the default wing
    layout: dict[str | None, list[str]]
    let_out: set[str] = field(default_factory=set)


def _numbers(floors: range, units: range, fmt: str) -> list[str]:
    return [fmt.format(floor=f, unit=u) for f in floors for u in units]


def _shanti_layout() -> dict[str | None, list[str]]:
    # Wings A-D, floors 1-4, units 01-08 minus x07/x08 on floor 4: 30 flats a wing, 120 in all,
    # covering every flat listed in docs/02 §12.
    numbers = [
        n
        for n in _numbers(range(1, 5), range(1, 9), "{floor}{unit:02d}")
        if n not in {"407", "408"}
    ]
    return {wing: numbers for wing in "ABCD"}


SOCIETIES = [
    SeedSociety(
        key="A",
        name="Shanti Sadan CHS",
        city="Mumbai",
        flat_count=120,
        cost_per_flat_paise=96000000,
        dues={
            "A-101": 0,
            "A-204": 4200,
            "A-305": 12600,
            "B-102": 0,
            "B-207": 29400,
            "B-401": 8400,
            "C-103": 0,
            "C-302": 16800,
            "C-404": 4200,
            "D-201": 0,
        },
        layout=_shanti_layout(),
        let_out={"A-305"},
    ),
    SeedSociety(
        key="B",
        name="Gulmohar Heights CHS",
        city="Thane",
        flat_count=64,
        cost_per_flat_paise=84000000,
        dues={
            "1-01": 0,
            "1-04": 3600,
            "2-02": 10800,
            "2-03": 0,
            "3-01": 0,
            "3-04": 25200,
            "4-02": 7200,
        },
        # 16 floors x 4 flats, written floor-flat as in docs/02 §12 (1-01 ... 16-04).
        layout={None: _numbers(range(1, 17), range(1, 5), "{floor}-{unit:02d}")},
    ),
    SeedSociety(
        key="C",
        name="Sagar Darshan CHS",
        city="Mumbai",
        flat_count=42,
        cost_per_flat_paise=72000000,
        dues={"101": 0, "102": 3000, "201": 0, "202": 0, "301": 6000},
        # 7 floors x 6 flats (101 ... 706).
        layout={None: _numbers(range(1, 8), range(1, 7), "{floor}{unit:02d}")},
    ),
]


def _label(wing: str | None, number: str) -> str:
    return f"{wing}-{number}" if wing else number


@dataclass
class SeedReport:
    societies_created: int = 0
    flats_created: int = 0
    balances_created: int = 0


async def _ensure_user(session: AsyncSession, email: str) -> User:
    user_id = dev_user_id(email)
    await set_user_context(session, user_id)
    return await user_service.ensure_user(session, AuthUser(id=user_id, email=email))


async def _seed_society(session: AsyncSession, spec: SeedSociety, report: SeedReport) -> UUID:
    admin = await _ensure_user(session, DEMO_ADMIN_EMAIL)
    existing = {
        s.society.name: s.society.id
        for s in await society_service.list_my_societies(session, admin)
    }
    society_id = existing.get(spec.name)
    if society_id is None:
        society, _ = await society_service.create_society(
            session,
            admin,
            {"name": spec.name, "city": spec.city, "bill_day": 1, "due_days": 15},
            [],
        )
        society_id = society.id
        report.societies_created += 1
    await set_society_context(session, society_id)

    wings = {w.name: w for w in await flat_service.list_wings(session, society_id)}
    saved = {
        (wing_id, number)
        for wing_id, number in await session.execute(
            select(Flat.wing_id, Flat.flat_number).where(Flat.society_id == society_id)
        )
    }
    entry_date = today_ist()
    for wing_name, numbers in spec.layout.items():
        if wing_name is None:
            wing = wings[society_service.DEFAULT_WING_NAME]
        elif wing_name in wings:
            wing = wings[wing_name]
        else:
            wing = await flat_service.create_wing(session, society_id, admin, wing_name, False)
            wings[wing_name] = wing
        for number in numbers:
            if (wing.id, number) in saved:
                continue
            label = _label(wing_name, number)
            flat = Flat(
                society_id=society_id,
                wing_id=wing.id,
                flat_number=number,
                certified_construction_cost_paise=spec.cost_per_flat_paise,
                occupancy="let_out" if label in spec.let_out else "owner_occupied",
                created_by=admin.id,
            )
            session.add(flat)
            await session.flush()
            session.add(
                Member(
                    society_id=society_id,
                    flat_id=flat.id,
                    full_name=f"Member {label}",
                    member_type="owner",
                    is_primary=True,
                    created_by=admin.id,
                )
            )
            if label in spec.let_out:
                session.add(
                    Member(
                        society_id=society_id,
                        flat_id=flat.id,
                        full_name=f"Tenant {label}",
                        member_type="tenant",
                        created_by=admin.id,
                    )
                )
            rupees = spec.dues.get(label, 0)
            if rupees:
                await ledger.add_opening_balance(
                    session,
                    society_id=society_id,
                    flat_id=flat.id,
                    amount_paise=rupees * 100,
                    entry_date=entry_date,
                    source_type="seed",
                    source_id=None,
                    created_by=admin.id,
                )
                report.balances_created += 1
            report.flats_created += 1
    await session.flush()
    return society_id


async def _seed_resident(session: AsyncSession, society_id: UUID, flat_label: str) -> None:
    resident = await _ensure_user(session, DEMO_RESIDENT_EMAIL)
    await set_society_context(session, society_id)
    wing_name, number = flat_label.split("-", 1)
    flat_id = await session.scalar(
        select(Flat.id)
        .join(Wing, Wing.id == Flat.wing_id)
        .where(Flat.society_id == society_id, Wing.name == wing_name, Flat.flat_number == number)
    )
    already = await session.scalar(
        select(SocietyMembership.id).where(
            SocietyMembership.society_id == society_id,
            SocietyMembership.user_id == resident.id,
        )
    )
    if flat_id is None or already:
        return
    session.add(
        SocietyMembership(
            society_id=society_id,
            user_id=resident.id,
            role="owner",
            flat_id=flat_id,
            status="active",
            invited_name=f"Member {flat_label}",
            invited_email=DEMO_RESIDENT_EMAIL,
        )
    )
    await session.flush()


async def run() -> SeedReport:
    report = SeedReport()
    ids: dict[str, UUID] = {}
    for spec in SOCIETIES:
        # One transaction per society keeps each society all-or-nothing.
        async with get_sessionmaker()() as session, session.begin():
            ids[spec.key] = await _seed_society(session, spec, report)
    async with get_sessionmaker()() as session, session.begin():
        await _seed_resident(session, ids[DEMO_RESIDENT_FLAT[0]], DEMO_RESIDENT_FLAT[1])
    return report
