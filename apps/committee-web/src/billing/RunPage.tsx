// One billing run: review a draft (warnings, every flat's amount) and approve it, or see the
// bills of an approved run and print them all (docs/02 §5).
import { ArrowLeft, CheckCircle2, Printer, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  BigButton,
  Button,
  Card,
  ConfirmDialog,
  ErrorText,
  Field,
  MoneyText,
  StatCard,
  formatDate,
  formatPaise,
  messageKeyOf,
  useCurrentSociety,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

import { useOpenPdf, useRun, useRunAction } from "../api/billing";
import { RunStatus } from "./BillsPage";

export function RunPage() {
  const { runId = "" } = useParams();
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const { language } = useSettings();
  const navigate = useNavigate();
  const run = useRun(runId);
  const action = useRunAction(runId);
  const openPdf = useOpenPdf();
  const roles = useCurrentSociety()?.society.roles ?? [];
  const canApprove = roles.some((r) => ["admin", "treasurer"].includes(r));
  const [asking, setAsking] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [reason, setReason] = useState("");
  const [query, setQuery] = useState("");

  if (run.isPending) return <p role="status">{tc("loading")}</p>;
  if (run.isError) return <ErrorText>{tc(messageKeyOf(run.error))}</ErrorText>;
  const r = run.data;
  const needle = query.trim().toLowerCase();
  const period = new Intl.DateTimeFormat(language, { month: "long", year: "numeric" }).format(new Date(`${r.period_start}T00:00:00`));

  return (
    <>
      <div className="mb-4">
        <Button variant="secondary" icon={<ArrowLeft size={22} />} onClick={() => navigate("/bills")}>
          {t("billing.title")}
        </Button>
      </div>
      <h1 className="mb-2 flex flex-wrap items-center gap-3 text-title font-bold">
        {t("billing.runTitle", { period })} <RunStatus status={r.status} />
      </h1>
      <p className="mb-6 text-body">
        {t("billing.dates", { bill: formatDate(r.bill_date, language), due: formatDate(r.due_date, language) })}
      </p>

      <div className="mb-6 grid max-w-3xl gap-3 sm:grid-cols-2">
        <StatCard label={t("billing.flats")} value={r.flat_count} />
        <StatCard label={r.status === "draft" ? t("billing.toBill") : t("billing.billed")} value={<MoneyText paise={r.total_paise} />} />
      </div>

      {r.warnings.length ? (
        <Card className="mb-6 max-w-3xl border-2 border-terracotta">
          <h2 className="mb-2 flex items-center gap-2 text-section font-bold">
            <TriangleAlert size={22} aria-hidden="true" className="text-terracotta" />
            {t("billing.warningsTitle")}
          </h2>
          <ul className="list-disc pl-6 text-body">
            {r.warnings.map((w, i) => (
              <li key={i}>
                {t(`billing.warnings.${w.key}`, {
                  flat: w.flat ?? "",
                  reasons: (w.reasons ?? []).map((x) => t(`preview.reasons.${x}`)).join(", "),
                })}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {r.status === "draft" ? (
        <div className="mb-8 flex max-w-3xl flex-col gap-3">
          {canApprove ? (
            <BigButton icon={<CheckCircle2 size={24} />} onClick={() => setAsking(true)} disabled={action.isPending}>
              {t("billing.approve", { count: r.flat_count })}
            </BigButton>
          ) : (
            <p className="text-body">{t("billing.approverOnly")}</p>
          )}
          {canApprove && !cancelling ? (
            <Button variant="secondary" onClick={() => setCancelling(true)}>
              {t("billing.cancelDraft")}
            </Button>
          ) : null}
          {cancelling ? (
            <Card className="flex flex-col gap-3">
              <Field label={t("billing.cancelReason")} value={reason} onChange={(e) => setReason(e.target.value)} />
              <Button
                variant="danger"
                disabled={reason.trim().length < 3 || action.isPending}
                onClick={() => action.mutate({ action: "cancel", reason: reason.trim() })}
              >
                {t("billing.cancelDraft")}
              </Button>
            </Card>
          ) : null}
          {action.isError ? <ErrorText>{tc(messageKeyOf(action.error))}</ErrorText> : null}
          <ConfirmDialog
            open={asking}
            question={t("billing.approveQuestion", { count: r.flat_count, total: formatPaise(r.total_paise) })}
            confirmLabel={t("billing.approveYes")}
            onCancel={() => setAsking(false)}
            onConfirm={() => {
              setAsking(false);
              action.mutate({ action: "approve" });
            }}
          />
        </div>
      ) : null}

      {r.status === "approved" || r.status === "sent" ? (
        <div className="mb-6 flex flex-wrap gap-3">
          <Button icon={<Printer size={22} />} onClick={() => openPdf.mutate(`/billing-runs/${r.id}/pdf`)} disabled={openPdf.isPending}>
            {t("billing.printAll")}
          </Button>
          {openPdf.isError ? <ErrorText>{tc(messageKeyOf(openPdf.error))}</ErrorText> : null}
        </div>
      ) : null}

      <Field label={t("flats.search")} value={query} onChange={(e) => setQuery(e.target.value)} className="mb-4 w-64" />
      <div className="overflow-x-auto rounded-card border border-line bg-surface">
        <table className="min-w-full text-body">
          <caption className="sr-only">{t("billing.runTitle", { period })}</caption>
          <thead>
            <tr className="border-b border-line text-left">
              <th scope="col" className="p-3">{t("preview.flat")}</th>
              {r.status === "draft" ? null : <th scope="col" className="p-3">{t("billing.number")}</th>}
              <th scope="col" className="p-3 text-right">{t("billing.charges")}</th>
              {r.status === "draft" ? null : <th scope="col" className="p-3 text-right">{t("billing.totalDue")}</th>}
            </tr>
          </thead>
          <tbody>
            {r.status === "draft"
              ? r.draft_flats
                  .filter((f) => !needle || f.label.toLowerCase().includes(needle))
                  .map((f) => (
                    <tr key={f.flat_id} className="border-b border-line last:border-b-0">
                      <th scope="row" className="p-3 text-left font-semibold">{f.label}</th>
                      <td className="p-3 text-right"><MoneyText paise={f.charges_paise} /></td>
                    </tr>
                  ))
              : r.bills
                  .filter((b) => !needle || b.flat_label.toLowerCase().includes(needle) || b.bill_number.toLowerCase().includes(needle))
                  .map((b) => (
                    <tr key={b.id} className="border-b border-line last:border-b-0">
                      <th scope="row" className="p-3 text-left font-semibold">
                        <Link to={`/bills/${b.id}`} className="underline">{b.flat_label}</Link>
                        {b.status === "cancelled" ? <span className="block text-small text-muted">{t("billing.billStatus.cancelled")}</span> : null}
                      </th>
                      <td className="p-3">{b.bill_number}</td>
                      <td className="p-3 text-right"><MoneyText paise={b.charges_paise} /></td>
                      <td className="p-3 text-right font-bold"><MoneyText paise={b.total_due_paise} /></td>
                    </tr>
                  ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
