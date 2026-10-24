// Billing runs (docs/02 §5): one per period. "Create bills now" makes a draft for review;
// nothing reaches residents until it is approved.
import { FilePlus2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  BigButton,
  Card,
  EmptyState,
  ErrorText,
  Field,
  MoneyText,
  formatDate,
  messageKeyOf,
  useCurrentSociety,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

import { useCreateRun, useRuns, type Run } from "../api/billing";

function thisMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function RunStatus({ status }: { status: Run["status"] }) {
  const { t } = useTranslation("committee");
  const style: Record<Run["status"], string> = {
    draft: "border-terracotta text-ink",
    approved: "border-green text-green",
    sent: "border-green text-green",
    cancelled: "border-muted text-muted",
  };
  return (
    <span className={`inline-block rounded-full border-2 px-3 py-1 text-small font-semibold ${style[status]}`}>
      {t(`billing.status.${status}`)}
    </span>
  );
}

export function BillsPage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const { language } = useSettings();
  const navigate = useNavigate();
  const runs = useRuns();
  const create = useCreateRun();
  const roles = useCurrentSociety()?.society.roles ?? [];
  const canCreate = roles.some((r) => ["admin", "treasurer", "consultant"].includes(r));
  const [month, setMonth] = useState(thisMonth);

  return (
    <>
      <h1 className="mb-2 text-title font-bold">{t("billing.title")}</h1>
      <p className="mb-6 max-w-3xl text-body">{t("billing.body")}</p>

      {canCreate ? (
        <Card className="mb-8 max-w-2xl">
          <h2 className="mb-3 text-section font-bold">{t("billing.createTitle")}</h2>
          <div className="flex flex-wrap items-end gap-4">
            <Field label={t("preview.month")} type="month" value={month} onChange={(e) => e.target.value && setMonth(e.target.value)} className="w-64" />
            <BigButton
              icon={<FilePlus2 size={24} />}
              disabled={create.isPending}
              onClick={() => create.mutate(`${month}-01`, { onSuccess: (run) => navigate(`/bills/runs/${run.id}`) })}
            >
              {t("billing.create")}
            </BigButton>
          </div>
          <p className="mt-2 text-small text-muted">{t("billing.createNote")}</p>
          {create.isError ? <ErrorText>{tc(messageKeyOf(create.error))}</ErrorText> : null}
        </Card>
      ) : null}

      {runs.isPending ? <p role="status">{tc("loading")}</p> : null}
      {runs.isError ? <ErrorText>{tc(messageKeyOf(runs.error))}</ErrorText> : null}
      {runs.data && runs.data.length === 0 ? <EmptyState message={t("billing.empty")} /> : null}
      <ul className="flex max-w-3xl flex-col gap-3">
        {runs.data?.map((r) => (
          <li key={r.id}>
            <Link
              to={`/bills/runs/${r.id}`}
              className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-line bg-surface p-4 hover:border-teal focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
            >
              <span>
                <span className="block text-body font-bold">
                  {new Intl.DateTimeFormat(language, { month: "long", year: "numeric" }).format(new Date(`${r.period_start}T00:00:00`))}
                </span>
                <span className="block text-small text-muted">
                  {t("billing.runLine", { count: r.flat_count, date: formatDate(r.bill_date, language) })}
                  {r.created_by_job ? ` · ${t("billing.byJob")}` : ""}
                </span>
              </span>
              <span className="flex items-center gap-3">
                <MoneyText paise={r.total_paise} className="text-body font-bold" />
                <RunStatus status={r.status} />
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
