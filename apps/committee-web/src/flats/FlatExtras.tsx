// Per-flat charge inputs (docs/02 §5): parking allotments, property tax from the municipal
// bill, and special amounts (overrides) that always carry a reason.
import { Plus } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";

import {
  BigButton,
  Button,
  Card,
  ErrorText,
  Field,
  MoneyText,
  SelectField,
  formatDate,
  messageKeyOf,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

import {
  useAddPropertyTax,
  useChargeHeads,
  useOverrides,
  useParking,
  usePropertyTax,
  useSaveOverride,
  useSaveParking,
} from "../api/charges";
import { rupeesToPaise } from "./labels";

function localToday(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function currentFinancialYear(): string {
  // Display default only; the person can type another year.
  const d = new Date();
  const first = d.getMonth() >= 3 ? d.getFullYear() : d.getFullYear() - 1;
  return `${first}-${String((first + 1) % 100).padStart(2, "0")}`;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-10">
      <h2 className="mb-4 text-section font-bold">{title}</h2>
      <div className="flex max-w-3xl flex-col gap-3">{children}</div>
    </section>
  );
}

export function FlatExtras({ flatId, canManage }: { flatId: string; canManage: boolean }) {
  return (
    <>
      <ParkingSection flatId={flatId} canManage={canManage} />
      <TaxSection flatId={flatId} canManage={canManage} />
      <OverrideSection flatId={flatId} canManage={canManage} />
    </>
  );
}

const SLOT_TYPES = ["open", "stilt", "covered", "podium", "mechanical", "other"] as const;
const VEHICLES = ["two_wheeler", "four_wheeler", "other"] as const;

function ParkingSection({ flatId, canManage }: { flatId: string; canManage: boolean }) {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const { language } = useSettings();
  const list = useParking(flatId);
  const save = useSaveParking(flatId);
  const [open, setOpen] = useState(false);
  const [slot, setSlot] = useState("");
  const [slotType, setSlotType] = useState<(typeof SLOT_TYPES)[number]>("open");
  const [vehicle, setVehicle] = useState<(typeof VEHICLES)[number]>("four_wheeler");
  const [number, setNumber] = useState("");
  const [rate, setRate] = useState("");
  const [problem, setProblem] = useState<string | null>(null);

  function submit(e: FormEvent) {
    e.preventDefault();
    const paise = rupeesToPaise(rate);
    if (!slot.trim()) return setProblem(t("setup.required"));
    if (paise === null) return setProblem(t("flats.invalidAmount"));
    setProblem(null);
    save.mutate(
      {
        body: {
          slot_label: slot.trim(),
          slot_type: slotType,
          vehicle_type: vehicle,
          vehicle_number: number.trim() || null,
          monthly_rate_paise: paise,
          from_date: localToday(),
          to_date: null,
          gb_resolution_ref: null,
        },
      },
      { onSuccess: () => setOpen(false) },
    );
  }

  return (
    <Section title={t("parking.title")}>
      <p className="text-small text-muted">{t("parking.note")}</p>
      {list.data?.length === 0 ? <p className="text-body">{t("parking.none")}</p> : null}
      {list.data?.map((p) => (
        <Card key={p.id} className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-body font-bold">
              {p.slot_label} · {t(`parking.slot.${p.slot_type}`)} · {t(`parking.vehicle.${p.vehicle_type}`)}
            </p>
            <p className="text-small text-muted">
              <MoneyText paise={p.monthly_rate_paise} /> {t("parking.perMonth")}
              {p.to_date ? ` · ${t("parking.ended", { date: formatDate(p.to_date, language) })}` : ""}
            </p>
          </div>
          {canManage && !p.to_date ? (
            <Button variant="secondary" onClick={() => save.mutate({ id: p.id, body: { end_date: localToday() } })}>
              {t("parking.end")}
            </Button>
          ) : null}
        </Card>
      ))}
      {canManage && !open ? (
        <div>
          <Button icon={<Plus size={22} />} onClick={() => setOpen(true)}>
            {t("parking.add")}
          </Button>
        </div>
      ) : null}
      {open ? (
        <Card>
          <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
            <Field label={t("parking.slotLabel")} value={slot} onChange={(e) => setSlot(e.target.value)} />
            <SelectField
              label={t("parking.slotType")}
              options={SLOT_TYPES.map((s) => ({ value: s, label: t(`parking.slot.${s}`) }))}
              value={slotType}
              onChange={(e) => setSlotType(e.target.value as (typeof SLOT_TYPES)[number])}
            />
            <SelectField
              label={t("parking.vehicleType")}
              options={VEHICLES.map((v) => ({ value: v, label: t(`parking.vehicle.${v}`) }))}
              value={vehicle}
              onChange={(e) => setVehicle(e.target.value as (typeof VEHICLES)[number])}
            />
            <Field label={t("parking.vehicleNumber")} help={t("setup.optional")} value={number} onChange={(e) => setNumber(e.target.value)} />
            <Field label={t("parking.rate")} help={t("parking.rateHelp")} inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value)} />
            {problem ? <ErrorText>{problem}</ErrorText> : null}
            {save.isError ? <ErrorText>{tc(messageKeyOf(save.error))}</ErrorText> : null}
            <BigButton type="submit" disabled={save.isPending}>
              {t("parking.save")}
            </BigButton>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              {tc("back")}
            </Button>
          </form>
        </Card>
      ) : null}
    </Section>
  );
}

function TaxSection({ flatId, canManage }: { flatId: string; canManage: boolean }) {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const list = usePropertyTax(flatId);
  const add = useAddPropertyTax(flatId);
  const [open, setOpen] = useState(false);
  const [authority, setAuthority] = useState("");
  const [year, setYear] = useState(currentFinancialYear);
  const [amount, setAmount] = useState("");
  const [exempt, setExempt] = useState(false);
  const [reason, setReason] = useState("");
  const [problem, setProblem] = useState<string | null>(null);

  function submit(e: FormEvent) {
    e.preventDefault();
    const paise = exempt ? 0 : rupeesToPaise(amount);
    if (!authority.trim()) return setProblem(t("setup.required"));
    if (!/^\d{4}-\d{2}$/.test(year)) return setProblem(t("tax.badYear"));
    if (paise === null) return setProblem(t("flats.invalidAmount"));
    if (exempt && !reason.trim()) return setProblem(t("tax.needReason"));
    setProblem(null);
    add.mutate(
      {
        body: {
          authority: authority.trim(),
          financial_year: year,
          annual_amount_paise: paise,
          is_exempt: exempt,
          exemption_reason: exempt ? reason.trim() : null,
        },
      },
      { onSuccess: () => setOpen(false) },
    );
  }

  return (
    <Section title={t("tax.title")}>
      <p className="text-small text-muted">{t("tax.note")}</p>
      {list.data?.length === 0 ? <p className="text-body">{t("tax.none")}</p> : null}
      {list.data?.map((row, i) => (
        <Card key={row.id} className={i > 0 && list.data[i - 1]?.financial_year === row.financial_year ? "opacity-60" : ""}>
          <p className="text-body font-bold">
            {row.financial_year} · {row.authority}
          </p>
          <p className="text-body">
            {row.is_exempt ? t("tax.exemptWith", { reason: row.exemption_reason ?? "" }) : <MoneyText paise={row.annual_amount_paise} />}
            {i > 0 && list.data[i - 1]?.financial_year === row.financial_year ? ` · ${t("tax.replaced")}` : ""}
          </p>
        </Card>
      ))}
      {canManage && !open ? (
        <div>
          <Button icon={<Plus size={22} />} onClick={() => setOpen(true)}>
            {t("tax.add")}
          </Button>
        </div>
      ) : null}
      {open ? (
        <Card>
          <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
            <Field label={t("import.fields.authority")} help={t("tax.authorityHelp")} value={authority} onChange={(e) => setAuthority(e.target.value)} />
            <Field label={t("import.fields.financial_year")} help={t("tax.yearHelp")} value={year} onChange={(e) => setYear(e.target.value)} />
            <label className="flex items-center gap-3 text-body">
              <input type="checkbox" checked={exempt} onChange={(e) => setExempt(e.target.checked)} className="h-7 w-7 accent-teal" />
              {t("tax.exempt")}
            </label>
            {exempt ? (
              <Field label={t("tax.reason")} help={t("tax.reasonHelp")} value={reason} onChange={(e) => setReason(e.target.value)} />
            ) : (
              <Field label={t("import.fields.annual_amount")} inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
            )}
            {problem ? <ErrorText>{problem}</ErrorText> : null}
            {add.isError ? <ErrorText>{tc(messageKeyOf(add.error))}</ErrorText> : null}
            <BigButton type="submit" disabled={add.isPending}>
              {t("tax.save")}
            </BigButton>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              {tc("back")}
            </Button>
          </form>
        </Card>
      ) : null}
    </Section>
  );
}

function OverrideSection({ flatId, canManage }: { flatId: string; canManage: boolean }) {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const { language } = useSettings();
  const list = useOverrides(flatId);
  const heads = useChargeHeads();
  const save = useSaveOverride(flatId);
  const [open, setOpen] = useState(false);
  const [headId, setHeadId] = useState("");
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [from, setFrom] = useState(localToday);
  const [problem, setProblem] = useState<string | null>(null);
  const names = new Map((heads.data ?? []).map((h) => [h.id, h.name]));

  function submit(e: FormEvent) {
    e.preventDefault();
    const paise = rupeesToPaise(amount);
    if (!headId) return setProblem(t("overrides.needHead"));
    if (paise === null) return setProblem(t("flats.invalidAmount"));
    if (reason.trim().length < 3) return setProblem(t("overrides.needReason"));
    setProblem(null);
    save.mutate(
      { body: { charge_head_id: headId, amount_paise: paise, reason: reason.trim(), valid_from: from, valid_to: null } },
      { onSuccess: () => setOpen(false) },
    );
  }

  return (
    <Section title={t("overrides.title")}>
      <p className="text-small text-muted">{t("overrides.note")}</p>
      {list.data?.length === 0 ? <p className="text-body">{t("overrides.none")}</p> : null}
      {list.data?.map((o) => (
        <Card key={o.id} className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-body font-bold">
              {names.get(o.charge_head_id) ?? ""}: <MoneyText paise={o.amount_paise} />
            </p>
            <p className="text-small text-muted">
              {t("overrides.from", { date: formatDate(o.valid_from, language) })}
              {o.valid_to ? ` · ${t("overrides.until", { date: formatDate(o.valid_to, language) })}` : ""}
            </p>
            <p className="text-small">{t("overrides.reasonLine", { reason: o.reason })}</p>
          </div>
          {canManage && !o.valid_to ? (
            <Button variant="secondary" onClick={() => save.mutate({ id: o.id, body: { end_date: localToday() } })}>
              {t("overrides.end")}
            </Button>
          ) : null}
        </Card>
      ))}
      {canManage && !open ? (
        <div>
          <Button icon={<Plus size={22} />} onClick={() => setOpen(true)}>
            {t("overrides.add")}
          </Button>
        </div>
      ) : null}
      {open ? (
        <Card>
          <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
            <SelectField
              label={t("overrides.head")}
              options={[{ value: "", label: t("overrides.chooseHead") }, ...(heads.data ?? []).filter((h) => h.is_active).map((h) => ({ value: h.id, label: h.name }))]}
              value={headId}
              onChange={(e) => setHeadId(e.target.value)}
            />
            <Field label={t("overrides.amount")} inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
            <Field label={t("overrides.reason")} help={t("overrides.reasonHelp")} value={reason} onChange={(e) => setReason(e.target.value)} />
            <Field label={t("overrides.fromLabel")} type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
            {problem ? <ErrorText>{problem}</ErrorText> : null}
            {save.isError ? <ErrorText>{tc(messageKeyOf(save.error))}</ErrorText> : null}
            <BigButton type="submit" disabled={save.isPending}>
              {t("overrides.save")}
            </BigButton>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              {tc("back")}
            </Button>
          </form>
        </Card>
      ) : null}
    </Section>
  );
}
