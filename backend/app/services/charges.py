"""Charge setup and the per-flat preview (docs/02 §5, docs/06 §2).

The arithmetic lives in app/calc (pure, fully tested); this module loads the inputs, applies
the legal checks from legal_parameters and writes the audit log.
"""

import re
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calc.charges import (
    ChargesResult,
    FlatData,
    HeadConfig,
    Period,
    bill_rounding,
    compute_charges,
)
from app.calc.legal import (
    FUND_MINIMUM,
    STANDARD_HEADS,
    HeadDraft,
    LegalValue,
    Problem,
    needs_reason,
    validate_head,
    validate_interest,
)
from app.errors import AppError, not_found
from app.models import (
    ChargeHead,
    Flat,
    FlatChargeOverride,
    LegalParameter,
    Member,
    ParkingAllotment,
    PropertyTaxAssessment,
    Society,
    User,
    Wing,
)
from app.services import audit
from app.services.flats import get_flat, snapshot
from app.timeutil import today_ist

HEAD_FIELDS = (
    "name",
    "code",
    "standard_code",
    "calc_type",
    "period_total_paise",
    "fixed_amount_paise",
    "percent",
    "percent_of_head_id",
    "applies_to",
    "gb_resolution_ref",
    "gb_resolution_date",
    "method_deviation_reason",
    "frequency",
    "one_time_period",
    "sort_order",
    "is_active",
)


# --- legal parameters ----------------------------------------------------------------


async def legal_values(session: AsyncSession, on: date) -> dict[str, LegalValue]:
    """Limits in force on a date (docs/05 §3). Banded values (applies_when) are not used
    by charge setup and are skipped."""
    rows = await session.scalars(
        select(LegalParameter)
        .where(
            LegalParameter.applies_when.is_(None),
            LegalParameter.effective_from <= on,
            or_(LegalParameter.effective_to.is_(None), LegalParameter.effective_to >= on),
        )
        .order_by(LegalParameter.effective_from)
    )
    return {p.code: LegalValue(p.value, p.source) for p in rows}


def _problems_json(problems: list[Problem]) -> list[dict[str, Any]]:
    return [asdict(p) for p in problems]


# --- society billing and interest settings --------------------------------------------

SETTINGS_FIELDS = (
    "billing_frequency",
    "bill_day",
    "due_days",
    "upi_id",
    "upi_payee_name",
    "bank_name",
    "bank_account_last4",
    "interest_enabled",
    "interest_rate_annual_pct",
    "interest_gb_resolution_date",
    "interest_grace_days",
    "rounding_rule",
)


async def update_settings(
    session: AsyncSession, society_id: UUID, actor: User, changes: dict[str, Any]
) -> Society:
    society = await session.get(Society, society_id)
    if society is None:
        raise not_found()
    before = snapshot(society, SETTINGS_FIELDS)
    for key, value in changes.items():
        setattr(society, key, value)

    problems: list[Problem] = []
    if society.interest_rate_annual_pct is not None:
        problems += validate_interest(
            Decimal(society.interest_rate_annual_pct), await legal_values(session, today_ist())
        )
    # docs/06 §5: interest only at a general body rate, with the resolution date recorded.
    if society.interest_enabled and (
        society.interest_rate_annual_pct is None or society.interest_gb_resolution_date is None
    ):
        problems.append(Problem("block", "interestNeedsResolution"))
    if problems:
        raise AppError(422, "LEGAL_BLOCK", "errors.legalBlock", _problems_json(problems))

    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="society.settings",
        entity_type="society",
        entity_id=society_id,
        before=before,
        after=snapshot(society, SETTINGS_FIELDS),
    )
    await session.refresh(society)
    return society


# --- charge heads --------------------------------------------------------------------


async def list_heads(session: AsyncSession, society_id: UUID) -> list[ChargeHead]:
    rows = await session.scalars(
        select(ChargeHead)
        .where(ChargeHead.society_id == society_id)
        .order_by(ChargeHead.is_active.desc(), ChargeHead.sort_order, ChargeHead.name)
    )
    return list(rows)


async def get_head(session: AsyncSession, society_id: UUID, head_id: UUID) -> ChargeHead:
    head = await session.get(ChargeHead, head_id)
    if head is None or head.society_id != society_id:
        raise not_found()
    return head


def _code_for(name: str, standard_code: str | None) -> str:
    if standard_code and standard_code != "other":
        return standard_code
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40]
    return f"other_{slug or 'charge'}"


async def check_head(
    session: AsyncSession, society_id: UUID, values: dict[str, Any], self_id: UUID | None
) -> list[Problem]:
    base_code: str | None = None
    has_base = False
    if values.get("percent_of_head_id"):
        if values["percent_of_head_id"] == self_id:
            raise AppError(422, "HEAD_SELF_REFERENCE", "errors.headSelfReference")
        base = await get_head(session, society_id, values["percent_of_head_id"])
        base_code, has_base = base.standard_code, True
    draft = HeadDraft(
        standard_code=values.get("standard_code"),
        calc_type=values["calc_type"],
        period_total_paise=values.get("period_total_paise"),
        fixed_amount_paise=values.get("fixed_amount_paise"),
        percent=values.get("percent"),
        base_standard_code=base_code,
        has_base_head=has_base,
        applies_to=values.get("applies_to", "all"),
    )
    return validate_head(draft, await legal_values(session, today_ist()))


async def save_head(
    session: AsyncSession,
    society_id: UUID,
    actor: User,
    fields: dict[str, Any],
    head_id: UUID | None = None,
) -> tuple[ChargeHead, list[Problem]]:
    head = await get_head(session, society_id, head_id) if head_id else None
    before = snapshot(head, HEAD_FIELDS) if head else None
    values = {**(snapshot(head, HEAD_FIELDS) if head else {}), **fields}
    if head:
        # snapshot() stringifies; keep the typed values for checks and the model.
        for key in ("percent_of_head_id",):
            values[key] = fields.get(key, getattr(head, key))
        values["percent"] = fields.get("percent", head.percent)

    problems = await check_head(session, society_id, values, head_id)
    if any(p.level == "block" for p in problems):
        raise AppError(422, "LEGAL_BLOCK", "errors.legalBlock", _problems_json(problems))
    reason_needed, resolution_needed = needs_reason(problems)
    if reason_needed and not (values.get("method_deviation_reason") or "").strip():
        raise AppError(422, "REASON_REQUIRED", "errors.reasonRequired", _problems_json(problems))
    if resolution_needed and not (values.get("gb_resolution_ref") or "").strip():
        raise AppError(
            422, "RESOLUTION_REQUIRED", "errors.resolutionRequired", _problems_json(problems)
        )

    if head is None:
        code = _code_for(fields["name"], fields.get("standard_code"))
        taken = await session.scalar(
            select(ChargeHead.id).where(
                ChargeHead.society_id == society_id, ChargeHead.code == code
            )
        )
        if taken:
            raise AppError(409, "HEAD_EXISTS", "errors.headExists")
        head = ChargeHead(society_id=society_id, code=code, created_by=actor.id, **fields)
        session.add(head)
    else:
        for key, value in fields.items():
            setattr(head, key, value)
    # The person saving has the charge-setup role; their save is the approval (docs/02 §5).
    head.approved_by = actor.id
    head.approved_at = datetime.now(UTC)
    await session.flush()
    await session.refresh(head)
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="charge_head.update" if before else "charge_head.create",
        entity_type="charge_head",
        entity_id=head.id,
        before=before,
        after={**snapshot(head, HEAD_FIELDS), "legal_warnings": _problems_json(problems)},
        reason=head.method_deviation_reason if problems else None,
    )
    return head, problems


# --- overrides, parking, property tax ------------------------------------------------

OVERRIDE_FIELDS = ("charge_head_id", "amount_paise", "reason", "valid_from", "valid_to")
PARKING_FIELDS = (
    "slot_label",
    "slot_type",
    "vehicle_type",
    "vehicle_number",
    "monthly_rate_paise",
    "from_date",
    "to_date",
    "gb_resolution_ref",
)
TAX_FIELDS = (
    "authority",
    "financial_year",
    "annual_amount_paise",
    "is_exempt",
    "exemption_reason",
)


async def list_overrides(
    session: AsyncSession, society_id: UUID, flat_id: UUID
) -> list[FlatChargeOverride]:
    await get_flat(session, society_id, flat_id)
    rows = await session.scalars(
        select(FlatChargeOverride)
        .where(FlatChargeOverride.flat_id == flat_id)
        .order_by(FlatChargeOverride.valid_from.desc())
    )
    return list(rows)


async def create_override(
    session: AsyncSession, society_id: UUID, actor: User, flat_id: UUID, fields: dict[str, Any]
) -> FlatChargeOverride:
    await get_flat(session, society_id, flat_id)
    await get_head(session, society_id, fields["charge_head_id"])
    row = FlatChargeOverride(society_id=society_id, flat_id=flat_id, created_by=actor.id, **fields)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="charge_override.create",
        entity_type="flat_charge_override",
        entity_id=row.id,
        after={"flat_id": str(flat_id), **snapshot(row, OVERRIDE_FIELDS)},
        reason=row.reason,
    )
    return row


async def end_override(
    session: AsyncSession,
    society_id: UUID,
    actor: User,
    flat_id: UUID,
    row_id: UUID,
    valid_to: date,
) -> FlatChargeOverride:
    row = await session.get(FlatChargeOverride, row_id)
    if row is None or row.society_id != society_id or row.flat_id != flat_id:
        raise not_found()
    if valid_to < row.valid_from:
        raise AppError(422, "DATES_REVERSED", "errors.datesReversed")
    before = snapshot(row, OVERRIDE_FIELDS)
    row.valid_to = valid_to
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="charge_override.end",
        entity_type="flat_charge_override",
        entity_id=row.id,
        before=before,
        after=snapshot(row, OVERRIDE_FIELDS),
    )
    return row


async def list_parking(
    session: AsyncSession, society_id: UUID, flat_id: UUID
) -> list[ParkingAllotment]:
    await get_flat(session, society_id, flat_id)
    rows = await session.scalars(
        select(ParkingAllotment)
        .where(ParkingAllotment.flat_id == flat_id)
        .order_by(ParkingAllotment.from_date.desc())
    )
    return list(rows)


async def create_parking(
    session: AsyncSession, society_id: UUID, actor: User, flat_id: UUID, fields: dict[str, Any]
) -> ParkingAllotment:
    await get_flat(session, society_id, flat_id)
    row = ParkingAllotment(society_id=society_id, flat_id=flat_id, created_by=actor.id, **fields)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="parking.allot",
        entity_type="parking_allotment",
        entity_id=row.id,
        after={"flat_id": str(flat_id), **snapshot(row, PARKING_FIELDS)},
    )
    return row


async def end_parking(
    session: AsyncSession, society_id: UUID, actor: User, flat_id: UUID, row_id: UUID, to_date: date
) -> ParkingAllotment:
    row = await session.get(ParkingAllotment, row_id)
    if row is None or row.society_id != society_id or row.flat_id != flat_id:
        raise not_found()
    if to_date < row.from_date:
        raise AppError(422, "DATES_REVERSED", "errors.datesReversed")
    before = snapshot(row, PARKING_FIELDS)
    row.to_date = to_date
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="parking.end",
        entity_type="parking_allotment",
        entity_id=row.id,
        before=before,
        after=snapshot(row, PARKING_FIELDS),
    )
    return row


def financial_year(day: date, start_month: int) -> str:
    """'2026-27' for 1 Nov 2026 with an April start."""
    first = day.year if day.month >= start_month else day.year - 1
    return f"{first}-{(first + 1) % 100:02d}"


async def list_tax(
    session: AsyncSession, society_id: UUID, flat_id: UUID
) -> list[PropertyTaxAssessment]:
    await get_flat(session, society_id, flat_id)
    rows = await session.scalars(
        select(PropertyTaxAssessment)
        .where(PropertyTaxAssessment.flat_id == flat_id)
        .order_by(
            PropertyTaxAssessment.financial_year.desc(), PropertyTaxAssessment.created_at.desc()
        )
    )
    return list(rows)


async def add_tax(
    session: AsyncSession, society_id: UUID, actor: User, flat_id: UUID, fields: dict[str, Any]
) -> PropertyTaxAssessment:
    """Append-only: a correction is a newer row for the same flat and year."""
    await get_flat(session, society_id, flat_id)
    if fields.get("is_exempt"):
        if not (fields.get("exemption_reason") or "").strip():
            raise AppError(422, "EXEMPTION_REASON", "errors.exemptionReason")
        fields["annual_amount_paise"] = 0
    row = PropertyTaxAssessment(
        society_id=society_id, flat_id=flat_id, entered_by=actor.id, **fields
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="property_tax.add",
        entity_type="property_tax_assessment",
        entity_id=row.id,
        after={"flat_id": str(flat_id), **snapshot(row, TAX_FIELDS)},
    )
    return row


# --- preview -------------------------------------------------------------------------


def make_period(start: date, frequency: str) -> Period:
    if start.day != 1:
        raise AppError(422, "PERIOD_START", "errors.periodStart")
    months = 3 if frequency == "quarterly" else 1
    month_index = start.month - 1 + months
    next_start = date(start.year + month_index // 12, month_index % 12 + 1, 1)
    return Period(start, next_start - timedelta(days=1), months, 12 // months)


@dataclass
class PreviewFlat:
    flat: Flat
    wing: Wing
    label: str


@dataclass
class Preview:
    period: Period
    heads: list[ChargeHead]
    flats: dict[str, PreviewFlat]
    result: ChargesResult
    rounding: dict[str, int]
    missing: dict[str, int]


def _label(wing: Wing, flat: Flat, wing_count: int) -> str:
    return f"{wing.name}-{flat.flat_number}" if wing_count > 1 else flat.flat_number


async def preview(session: AsyncSession, society_id: UUID, period_start: date) -> Preview:
    society = await session.get(Society, society_id)
    if society is None:
        raise not_found()
    period = make_period(period_start, society.billing_frequency)

    wings = {
        w.id: w for w in await session.scalars(select(Wing).where(Wing.society_id == society_id))
    }
    flats = list(
        await session.scalars(
            select(Flat).where(Flat.society_id == society_id, Flat.is_active.is_(True))
        )
    )
    # "Per member" counts owners and joint owners living as members in the period.
    member_rows = await session.execute(
        select(Member.flat_id, func.count())
        .where(
            Member.society_id == society_id,
            Member.member_type.in_(("owner", "joint_owner")),
            or_(Member.from_date.is_(None), Member.from_date <= period.end),
            or_(Member.to_date.is_(None), Member.to_date >= period.start),
        )
        .group_by(Member.flat_id)
    )
    members = {flat_id: count for flat_id, count in member_rows}

    heads = [h for h in await list_heads(session, society_id) if h.is_active]
    in_period = and_(
        FlatChargeOverride.valid_from <= period.end,
        or_(FlatChargeOverride.valid_to.is_(None), FlatChargeOverride.valid_to >= period.start),
    )
    overrides: dict[UUID, dict[str, int]] = {}
    for row in await session.scalars(
        select(FlatChargeOverride)
        .where(FlatChargeOverride.society_id == society_id, in_period)
        .order_by(FlatChargeOverride.valid_from)
    ):
        overrides.setdefault(row.charge_head_id, {})[str(row.flat_id)] = row.amount_paise

    parking: dict[str, int] = {}
    for row in await session.scalars(
        select(ParkingAllotment).where(
            ParkingAllotment.society_id == society_id,
            ParkingAllotment.from_date <= period.end,
            or_(ParkingAllotment.to_date.is_(None), ParkingAllotment.to_date >= period.start),
        )
    ):
        key = str(row.flat_id)
        parking[key] = parking.get(key, 0) + row.monthly_rate_paise

    year = financial_year(period.start, society.financial_year_start_month)
    assessed: dict[str, int] = {}
    for row in await session.scalars(
        select(PropertyTaxAssessment)
        .where(
            PropertyTaxAssessment.society_id == society_id,
            PropertyTaxAssessment.financial_year == year,
            PropertyTaxAssessment.flat_id.is_not(None),
        )
        .order_by(PropertyTaxAssessment.created_at)
    ):
        # Newest row for the flat wins (corrections are appended).
        assessed[str(row.flat_id)] = 0 if row.is_exempt else row.annual_amount_paise

    flat_data = [
        FlatData(
            id=str(f.id),
            wing=wings[f.wing_id].name,
            number=f.flat_number,
            wing_has_lift=wings[f.wing_id].has_lift,
            carpet_area_sqft=f.carpet_area_sqft,
            water_points=f.water_points,
            construction_cost_paise=f.certified_construction_cost_paise,
            occupancy=f.occupancy,
            member_count=members.get(f.id, 0),
        )
        for f in flats
    ]
    head_configs = [
        HeadConfig(
            id=str(h.id),
            name=h.name,
            calc_type=h.calc_type,
            standard_code=h.standard_code,
            period_total_paise=h.period_total_paise,
            fixed_amount_paise=h.fixed_amount_paise,
            percent=h.percent,
            percent_of_head_id=str(h.percent_of_head_id) if h.percent_of_head_id else None,
            applies_to=h.applies_to,
            frequency=h.frequency,
            one_time_period=h.one_time_period,
            assessed_annual_paise=assessed,
            parking_monthly_paise=parking,
            overrides=overrides.get(h.id, {}),
        )
        for h in heads
    ]
    result = compute_charges(flat_data, head_configs, period)
    rounding = {
        fid: bill_rounding(total, society.rounding_rule) for fid, total in result.totals.items()
    }
    labels = {
        str(f.id): PreviewFlat(f, wings[f.wing_id], _label(wings[f.wing_id], f, len(wings)))
        for f in flats
    }
    missing = {
        "carpet_area": sum(1 for f in flats if f.carpet_area_sqft is None),
        "construction_cost": sum(1 for f in flats if f.certified_construction_cost_paise is None),
        "water_points": sum(1 for f in flats if f.water_points is None),
        "no_member": sum(1 for f in flats if members.get(f.id, 0) == 0),
    }
    return Preview(period, heads, labels, result, rounding, missing)


async def standard_head_list(session: AsyncSession) -> list[dict[str, Any]]:
    """Statutory heads with their method, plus the legal percent that applies to them today
    (fixed for non-occupancy, a minimum for the funds) so screens never hard-code law."""
    legal = await legal_values(session, today_ist())
    percents = {"non_occupancy": "non_occupancy_pct_of_service", **FUND_MINIMUM}
    result = []
    for code, head in STANDARD_HEADS.items():
        param = legal.get(percents.get(code, ""))
        result.append(
            {
                "standard_code": code,
                "calc_type": head.calc_type,
                "applies_to": head.applies_to,
                "rule": head.rule,
                "legal_percent": param.value if param else None,
                "legal_percent_kind": (
                    None if param is None else "fixed" if code == "non_occupancy" else "minimum"
                ),
                "legal_source": param.source if param else None,
            }
        )
    return result
