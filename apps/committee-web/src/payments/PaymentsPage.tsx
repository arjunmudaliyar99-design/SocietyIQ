// Payments (docs/02 §6): what waits for confirmation first, then everything recorded.
import { Plus } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  Button,
  EmptyState,
  ErrorText,
  LoadingBlock,
  MoneyText,
  formatDate,
  messageKeyOf,
  useCurrentSociety,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

import { MONEY_ROLES, usePayments, type Payment } from "../api/payments";

const TABS = ["waiting", "all"] as const;

export function PaymentStatus({ status }: { status: Payment["status"] }) {
  const { t } = useTranslation("committee");
  const style: Record<Payment["status"], string> = {
    pending: "border-terracotta text-ink",
    recorded: "border-terracotta text-ink",
    confirmed: "border-green text-green",
    bounced: "border-red text-red",
    reversed: "border-muted text-muted",
  };
  return (
    <span className={`inline-block rounded-full border-2 px-3 py-1 text-small font-semibold ${style[status]}`}>
      {t(`payments.status.${status}`)}
    </span>
  );
}

function Row({ p }: { p: Payment }) {
  const { t } = useTranslation("committee");
  const { language } = useSettings();
  return (
    <li>
      <Link
        to={`/payments/${p.id}`}
        className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-line bg-surface p-4 shadow-card transition hover:border-teal hover:shadow-raised focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
      >
        <span>
          <span className="block text-body font-bold">
            {p.flat_label} · <MoneyText paise={p.amount_paise} />
          </span>
          <span className="block text-small text-muted">
            {t(`payments.method.${p.method}`)} · {formatDate(p.received_on, language)}
            {p.reference ? ` · ${p.reference}` : ""}
            {p.reported_by_resident ? ` · ${t("payments.byResident")}` : ""}
          </span>
        </span>
        <span className="flex items-center gap-2">
          {p.receipt_number ? <span className="text-small text-muted">{p.receipt_number}</span> : null}
          <PaymentStatus status={p.status} />
        </span>
      </Link>
    </li>
  );
}

export function PaymentsPage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const roles = useCurrentSociety()?.society.roles ?? [];
  const canRecord = roles.some((r) => MONEY_ROLES.includes(r));
  const [tab, setTab] = useState<(typeof TABS)[number]>("waiting");
  const payments = usePayments();
  const rows = (payments.data ?? []).filter((p) => tab === "all" || p.status === "pending" || p.status === "recorded");

  return (
    <>
      <h1 className="mb-2 text-title font-bold">{t("payments.title")}</h1>
      <p className="mb-6 max-w-3xl text-body">{t("payments.body")}</p>
      {canRecord ? (
        <div className="mb-6">
          <Button icon={<Plus size={22} />} onClick={() => navigate("/payments/new")}>
            {t("payments.record")}
          </Button>
        </div>
      ) : null}
      <div role="tablist" aria-label={t("payments.title")} className="mb-4 flex gap-2">
        {TABS.map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`min-h-[48px] rounded-full border-2 px-5 text-body font-semibold transition-colors focus-visible:outline-3 focus-visible:outline-ink ${
              tab === key ? "border-teal bg-teal text-surface" : "border-line bg-surface text-ink hover:border-teal"
            }`}
          >
            {t(`payments.tab.${key}`)}
          </button>
        ))}
      </div>
      {payments.isPending ? <LoadingBlock /> : null}
      {payments.isError ? <ErrorText>{tc(messageKeyOf(payments.error))}</ErrorText> : null}
      {payments.data && rows.length === 0 ? (
        <EmptyState message={tab === "waiting" ? t("payments.noneWaiting") : t("payments.none")} />
      ) : null}
      <ul className="flex max-w-3xl flex-col gap-3">
        {rows.map((p) => (
          <Row key={p.id} p={p} />
        ))}
      </ul>
    </>
  );
}
