// Billing and interest settings (docs/02 §3 step 2, docs/06 §1, §5). Admin only. Interest is
// off by default and needs the general body rate and resolution date; the cap is checked by
// the backend against legal_parameters.
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { BigButton, Button, ErrorText, Field, SelectField, messageKeyOf, useTranslation } from "@societyiq/shared";

import { useSaveSettings, useSocietySettings, type SocietySettings } from "../api/charges";
import { LegalProblems } from "./LegalProblems";
import { problemsOf } from "./problems";

export function SettingsPage() {
  const { t: tc } = useTranslation();
  const settings = useSocietySettings();
  if (settings.isPending) return <p role="status">{tc("loading")}</p>;
  if (settings.isError) return <ErrorText>{tc(messageKeyOf(settings.error))}</ErrorText>;
  return <SettingsForm initial={settings.data} />;
}

function SettingsForm({ initial }: { initial: SocietySettings }) {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const save = useSaveSettings();
  const [frequency, setFrequency] = useState(initial.billing_frequency);
  const [billDay, setBillDay] = useState(String(initial.bill_day ?? ""));
  const [dueDays, setDueDays] = useState(String(initial.due_days));
  const [rounding, setRounding] = useState(initial.rounding_rule);
  const [interestOn, setInterestOn] = useState(initial.interest_enabled);
  const [rate, setRate] = useState(initial.interest_rate_annual_pct ? String(Number(initial.interest_rate_annual_pct)) : "");
  const [resolutionDate, setResolutionDate] = useState(initial.interest_gb_resolution_date ?? "");
  const [grace, setGrace] = useState(initial.interest_grace_days === null || initial.interest_grace_days === undefined ? "" : String(initial.interest_grace_days));
  const [problem, setProblem] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  function submit(event: FormEvent) {
    event.preventDefault();
    setSaved(false);
    const day = Number(billDay);
    if (!Number.isInteger(day) || day < 1 || day > 28) return setProblem(t("setup.invalidBillDay"));
    if (!/^\d+$/.test(dueDays)) return setProblem(t("setup.invalidNumber"));
    if (rate && !/^\d+(\.\d{1,4})?$/.test(rate)) return setProblem(t("charges.invalidPercent"));
    if (grace && !/^\d+$/.test(grace)) return setProblem(t("setup.invalidNumber"));
    setProblem(null);
    save.mutate(
      {
        billing_frequency: frequency,
        bill_day: day,
        due_days: Number(dueDays),
        rounding_rule: rounding,
        interest_enabled: interestOn,
        interest_rate_annual_pct: rate || null,
        interest_gb_resolution_date: resolutionDate || null,
        interest_grace_days: grace ? Number(grace) : null,
      },
      { onSuccess: () => setSaved(true) },
    );
  }

  return (
    <>
      <h1 className="mb-6 text-title font-bold">{t("billingSettings.title")}</h1>
      <form className="flex max-w-2xl flex-col gap-4" onSubmit={submit} noValidate>
        <SelectField
          label={t("setup.billingFrequency")}
          options={[
            { value: "monthly", label: t("setup.monthly") },
            { value: "quarterly", label: t("setup.quarterly") },
          ]}
          value={frequency}
          onChange={(e) => setFrequency(e.target.value === "quarterly" ? "quarterly" : "monthly")}
        />
        <Field label={t("setup.billDay")} help={t("setup.billDayHelp")} inputMode="numeric" value={billDay} onChange={(e) => setBillDay(e.target.value)} />
        <Field label={t("setup.dueDays")} inputMode="numeric" value={dueDays} onChange={(e) => setDueDays(e.target.value)} />
        <SelectField
          label={t("billingSettings.rounding")}
          help={t("billingSettings.roundingHelp")}
          options={[
            { value: "nearest_rupee", label: t("billingSettings.nearestRupee") },
            { value: "none", label: t("billingSettings.exactPaise") },
          ]}
          value={rounding}
          onChange={(e) => setRounding(e.target.value === "none" ? "none" : "nearest_rupee")}
        />

        <h2 className="mt-4 text-section font-bold">{t("billingSettings.interestTitle")}</h2>
        <p className="text-body">{t("billingSettings.interestBody")}</p>
        <label className="flex items-center gap-3 text-body">
          <input type="checkbox" checked={interestOn} onChange={(e) => setInterestOn(e.target.checked)} className="h-7 w-7 accent-teal" />
          {t("billingSettings.interestOn")}
        </label>
        {interestOn ? (
          <>
            <Field label={t("billingSettings.rate")} help={t("billingSettings.rateHelp")} inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value)} />
            <Field label={t("billingSettings.resolutionDate")} type="date" value={resolutionDate} onChange={(e) => setResolutionDate(e.target.value)} />
            <Field label={t("billingSettings.grace")} help={t("billingSettings.graceHelp")} inputMode="numeric" value={grace} onChange={(e) => setGrace(e.target.value)} />
          </>
        ) : null}

        <LegalProblems problems={problemsOf(save.error)} />
        {problem ? <ErrorText>{problem}</ErrorText> : null}
        {save.isError && !problemsOf(save.error).length ? <ErrorText>{tc(messageKeyOf(save.error))}</ErrorText> : null}
        {saved ? <p role="status" className="text-body font-semibold text-green">{t("billingSettings.saved")}</p> : null}
        <BigButton type="submit" disabled={save.isPending}>
          {t("billingSettings.save")}
        </BigButton>
        <Button variant="secondary" onClick={() => navigate("/charges")}>
          {tc("back")}
        </Button>
      </form>
    </>
  );
}
