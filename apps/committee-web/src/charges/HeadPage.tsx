// Add or change a charge head (docs/02 §5). Starts from the statutory head with its legal
// method pre-set; the committee enters only the GB-approved amounts. The backend decides what
// is blocked or needs a reason; this screen shows it in plain words.
import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  ApiError,
  BigButton,
  Button,
  Card,
  ErrorText,
  Field,
  SelectField,
  messageKeyOf,
  useTranslation,
} from "@societyiq/shared";

import {
  useChargeHeads,
  useSaveHead,
  useStandardHeads,
  type ChargeHead,
  type ChargeHeadInput,
  type StandardHead,
} from "../api/charges";
import { paiseToRupeesInput, rupeesToPaise } from "../flats/labels";
import { LegalProblems } from "./LegalProblems";
import { problemsOf } from "./problems";

const METHODS = [
  "equal_per_flat",
  "equal_per_flat_with_lift",
  "per_carpet_area",
  "per_water_point",
  "as_assessed_per_flat",
  "pct_of_head",
  "pct_of_construction_cost",
  "per_parking_allotment",
  "per_member_fixed",
  "fixed_per_flat",
  "custom_per_flat",
  "voluntary",
] as const;
type Method = (typeof METHODS)[number];

const TOTAL = new Set<Method>(["equal_per_flat", "equal_per_flat_with_lift", "per_carpet_area", "per_water_point"]);
const PERCENT = new Set<Method>(["pct_of_head", "pct_of_construction_cost"]);
const FIXED = new Set<Method>(["per_member_fixed", "fixed_per_flat"]);

interface Draft {
  standardCode: string;
  name: string;
  method: Method;
  total: string;
  percent: string;
  fixed: string;
  baseHeadId: string;
  appliesTo: "all" | "let_out_only";
  resolutionRef: string;
  resolutionDate: string;
  reason: string;
  oneTime: boolean;
  oneTimePeriod: string;
}

function fromHead(head: ChargeHead): Draft {
  return {
    standardCode: head.standard_code ?? "other",
    name: head.name,
    method: head.calc_type,
    total: paiseToRupeesInput(head.period_total_paise),
    percent: head.percent !== null && head.percent !== undefined ? String(Number(head.percent)) : "",
    fixed: paiseToRupeesInput(head.fixed_amount_paise),
    baseHeadId: head.percent_of_head_id ?? "",
    appliesTo: head.applies_to,
    resolutionRef: head.gb_resolution_ref ?? "",
    resolutionDate: head.gb_resolution_date ?? "",
    reason: head.method_deviation_reason ?? "",
    oneTime: head.frequency === "one_time",
    oneTimePeriod: head.one_time_period?.slice(0, 7) ?? "",
  };
}

function fromStandard(std: StandardHead, name: string, heads: ChargeHead[]): Draft {
  const service = heads.find((h) => h.standard_code === "service");
  const isNonOccupancy = std.standard_code === "non_occupancy";
  return {
    standardCode: std.standard_code,
    name,
    method: std.calc_type,
    total: "",
    // The fixed percent comes from legal_parameters via the API; the backend checks it again.
    percent: isNonOccupancy && std.legal_percent != null ? String(Number(std.legal_percent)) : "",
    fixed: "",
    baseHeadId: isNonOccupancy ? (service?.id ?? "") : "",
    appliesTo: std.applies_to,
    resolutionRef: "",
    resolutionDate: "",
    reason: "",
    oneTime: false,
    oneTimePeriod: "",
  };
}

export function HeadPage() {
  const { headId } = useParams();
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const standard = useStandardHeads();
  const heads = useChargeHeads();

  if (standard.isPending || heads.isPending) return <p role="status">{tc("loading")}</p>;
  if (standard.isError || heads.isError) return <ErrorText>{tc(messageKeyOf(standard.error ?? heads.error))}</ErrorText>;
  const existing = headId ? heads.data.find((h) => h.id === headId) : undefined;
  if (headId && !existing) return <ErrorText>{tc("errors.notFound")}</ErrorText>;
  return (
    <>
      <h1 className="mb-6 text-title font-bold">{existing ? existing.name : t("charges.add")}</h1>
      <HeadForm key={headId ?? "new"} standard={standard.data} heads={heads.data} existing={existing} />
    </>
  );
}

function HeadForm({ standard, heads, existing }: { standard: StandardHead[]; heads: ChargeHead[]; existing?: ChargeHead }) {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const save = useSaveHead();
  const [draft, setDraft] = useState<Draft | null>(() => (existing ? fromHead(existing) : null));
  const [problem, setProblem] = useState<string | null>(null);

  if (!draft) {
    const taken = new Set(heads.map((h) => h.standard_code));
    return (
      <Card className="max-w-2xl">
        <h2 className="mb-2 text-section font-bold">{t("charges.chooseTitle")}</h2>
        <p className="mb-4 text-body">{t("charges.chooseBody")}</p>
        <ul className="flex flex-col gap-2">
          {standard.map((s) => {
            const used = s.standard_code !== "other" && taken.has(s.standard_code);
            return (
              <li key={s.standard_code}>
                <button
                  type="button"
                  disabled={used}
                  onClick={() => setDraft(fromStandard(s, t(`charges.standard.${s.standard_code}`), heads))}
                  className="flex w-full min-h-[56px] flex-col items-start rounded-lg border-2 border-line bg-surface px-4 py-2 text-left hover:border-teal focus-visible:outline-3 focus-visible:outline-ink disabled:opacity-50"
                >
                  <span className="text-body font-bold">{t(`charges.standard.${s.standard_code}`)}</span>
                  <span className="text-small text-muted">
                    {used ? t("charges.alreadyAdded") : t(`charges.method.${s.calc_type}`)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </Card>
    );
  }

  const d = draft;
  const set = (key: keyof Draft) => (e: { target: { value: string } }) => setDraft({ ...d, [key]: e.target.value });
  const statutory = standard.find((s) => s.standard_code === d.standardCode);
  const isNonOccupancy = d.standardCode === "non_occupancy";
  const deviates = statutory && d.standardCode !== "other" && statutory.calc_type !== d.method;
  const serverProblems = problemsOf(save.error);
  const askReason =
    deviates || serverProblems.some((p) => p.level === "warn") || Boolean(existing?.method_deviation_reason);

  function submit(event: FormEvent) {
    event.preventDefault();
    const total = d.total.trim() ? rupeesToPaise(d.total) : null;
    const fixed = d.fixed.trim() ? rupeesToPaise(d.fixed) : null;
    if ((d.total.trim() && total === null) || (d.fixed.trim() && fixed === null)) {
      setProblem(t("flats.invalidAmount"));
      return;
    }
    if (d.percent.trim() && !/^\d+(\.\d{1,4})?$/.test(d.percent.trim())) {
      setProblem(t("charges.invalidPercent"));
      return;
    }
    if (d.oneTime && !d.oneTimePeriod) {
      setProblem(t("charges.needMonth"));
      return;
    }
    setProblem(null);
    const body: ChargeHeadInput = {
      name: d.name.trim(),
      standard_code: d.standardCode as ChargeHeadInput["standard_code"],
      calc_type: d.method,
      period_total_paise: TOTAL.has(d.method) ? total : null,
      fixed_amount_paise: FIXED.has(d.method) ? fixed : null,
      percent: PERCENT.has(d.method) && d.percent.trim() ? d.percent.trim() : null,
      percent_of_head_id: d.method === "pct_of_head" && d.baseHeadId ? d.baseHeadId : null,
      applies_to: d.appliesTo,
      gb_resolution_ref: d.resolutionRef.trim() || null,
      gb_resolution_date: d.resolutionDate || null,
      method_deviation_reason: d.reason.trim() || null,
      frequency: d.oneTime ? "one_time" : "every_bill",
      one_time_period: d.oneTime && d.oneTimePeriod ? `${d.oneTimePeriod}-01` : null,
      sort_order: existing?.sort_order ?? heads.length + 1,
    };
    if (existing) {
      // The statutory head is fixed once created; everything else can change.
      const update: Partial<ChargeHeadInput> = { ...body };
      delete update.standard_code;
      save.mutate({ id: existing.id, body: update }, { onSuccess: () => navigate("/charges") });
    } else {
      save.mutate({ body }, { onSuccess: () => navigate("/charges") });
    }
  }

  const baseOptions = heads.filter((h) => h.calc_type !== "pct_of_head" && h.id !== existing?.id);

  return (
    <form className="flex max-w-2xl flex-col gap-4" onSubmit={submit} noValidate>
      <Field label={t("charges.name")} value={d.name} onChange={set("name")} />
      <SelectField
        label={t("charges.howSplit")}
        help={statutory && d.standardCode !== "other" ? t("charges.statutoryHelp", { rule: statutory.rule }) : undefined}
        options={METHODS.map((m) => ({ value: m, label: t(`charges.method.${m}`) }))}
        value={d.method}
        disabled={isNonOccupancy}
        onChange={(e) => setDraft({ ...d, method: e.target.value as Method })}
      />
      {isNonOccupancy && statutory?.legal_percent != null ? (
        <p className="text-body">
          {t("charges.nonOccupancyNote", { percent: Number(statutory.legal_percent), rule: statutory.legal_source })}
        </p>
      ) : null}
      {statutory?.legal_percent_kind === "minimum" ? (
        <p className="text-body">
          {t("charges.fundMinimumNote", { percent: Number(statutory.legal_percent), rule: statutory.legal_source })}
        </p>
      ) : null}
      {deviates ? <p className="text-body text-terracotta">{t("charges.deviationHint")}</p> : null}

      {TOTAL.has(d.method) ? (
        <Field
          label={t("charges.total")}
          help={t("charges.totalHelp")}
          inputMode="decimal"
          value={d.total}
          onChange={set("total")}
        />
      ) : null}
      {PERCENT.has(d.method) ? (
        <Field
          label={d.method === "pct_of_construction_cost" ? t("charges.percentOfCost") : t("charges.percentOfHead")}
          inputMode="decimal"
          value={d.percent}
          disabled={isNonOccupancy}
          onChange={set("percent")}
        />
      ) : null}
      {d.method === "pct_of_head" && !isNonOccupancy ? (
        <SelectField
          label={t("charges.baseHead")}
          options={[{ value: "", label: t("charges.chooseBase") }, ...baseOptions.map((h) => ({ value: h.id, label: h.name }))]}
          value={d.baseHeadId}
          onChange={set("baseHeadId")}
        />
      ) : null}
      {FIXED.has(d.method) ? (
        <Field
          label={d.method === "per_member_fixed" ? t("charges.perMemberMonth") : t("charges.fixedPerFlat")}
          inputMode="decimal"
          value={d.fixed}
          onChange={set("fixed")}
        />
      ) : null}
      {d.method === "custom_per_flat" || d.method === "voluntary" ? <p className="text-body">{t("charges.perFlatNote")}</p> : null}
      {d.method === "as_assessed_per_flat" ? <p className="text-body">{t("charges.assessedNote")}</p> : null}
      {d.method === "per_parking_allotment" ? <p className="text-body">{t("charges.parkingNote")}</p> : null}

      <Field label={t("charges.resolutionRef")} help={t("charges.resolutionHelp")} value={d.resolutionRef} onChange={set("resolutionRef")} />
      <Field label={t("charges.resolutionDate")} type="date" value={d.resolutionDate} onChange={set("resolutionDate")} />
      {askReason ? <Field label={t("charges.reason")} help={t("charges.reasonHelp")} value={d.reason} onChange={set("reason")} /> : null}

      <label className="flex items-center gap-3 text-body">
        <input
          type="checkbox"
          checked={d.oneTime}
          onChange={(e) => setDraft({ ...d, oneTime: e.target.checked })}
          className="h-7 w-7 accent-teal"
        />
        {t("charges.oneTime")}
      </label>
      {d.oneTime ? <Field label={t("charges.oneTimeMonth")} type="month" value={d.oneTimePeriod} onChange={set("oneTimePeriod")} /> : null}

      <LegalProblems problems={serverProblems} />
      {problem ? <ErrorText>{problem}</ErrorText> : null}
      {save.isError && !(save.error instanceof ApiError && serverProblems.length) ? (
        <ErrorText>{tc(messageKeyOf(save.error))}</ErrorText>
      ) : null}
      <BigButton type="submit" disabled={save.isPending}>
        {t("charges.save")}
      </BigButton>
      {existing ? (
        <Button
          variant="secondary"
          onClick={() =>
            save.mutate({ id: existing.id, body: { is_active: !existing.is_active } }, { onSuccess: () => navigate("/charges") })
          }
        >
          {existing.is_active ? t("charges.stop") : t("charges.restart")}
        </Button>
      ) : null}
      <Button variant="secondary" onClick={() => (existing ? navigate("/charges") : setDraft(null))}>
        {tc("back")}
      </Button>
    </form>
  );
}
