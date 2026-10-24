// Dues and defaulters (docs/02 §7, docs/06 §6): who owes what, how long, and a suggested
// next step. Committee roles only; never shown to residents.
import { useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorText, LoadingBlock, MoneyText, StatCard, messageKeyOf, useTranslation } from "@societyiq/shared";

import { useDues, type Dues } from "../api/payments";

const BUCKETS = ["friendly", "formal", "long"] as const;
type Bucket = Dues["rows"][number]["bucket"];

const TONE: Record<Bucket, string> = {
  paid_up: "border-green",
  friendly: "border-mint",
  formal: "border-terracotta",
  long: "border-red",
};

export function DuesPage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const [bucket, setBucket] = useState<Bucket | "">("");
  const dues = useDues(bucket || undefined);
  const all = useDues();

  return (
    <>
      <h1 className="mb-2 text-title font-bold">{t("dues.title")}</h1>
      <p className="mb-6 max-w-3xl text-body">{t("dues.body")}</p>
      {all.data ? (
        <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label={t("dues.outstanding")} value={<MoneyText paise={all.data.outstanding_paise} />} />
          {BUCKETS.map((b) => (
            <StatCard
              key={b}
              label={t(`dues.bucket.${b}`)}
              value={all.data.counts[b] ?? 0}
              note={t("dues.flats")}
              onClick={() => setBucket(bucket === b ? "" : b)}
            />
          ))}
        </div>
      ) : null}
      <div role="group" aria-label={t("dues.filter")} className="mb-4 flex flex-wrap gap-2">
        {(["", ...BUCKETS] as const).map((b) => (
          <button
            key={b || "all"}
            type="button"
            aria-pressed={bucket === b}
            onClick={() => setBucket(b)}
            className={`min-h-[48px] rounded-full border-2 px-5 text-body font-semibold transition-colors focus-visible:outline-3 focus-visible:outline-ink ${
              bucket === b ? "border-teal bg-teal text-surface" : "border-line bg-surface text-ink hover:border-teal"
            }`}
          >
            {b ? t(`dues.bucket.${b}`) : t("dues.all")}
          </button>
        ))}
      </div>
      {dues.isPending ? <LoadingBlock /> : null}
      {dues.isError ? <ErrorText>{tc(messageKeyOf(dues.error))}</ErrorText> : null}
      {dues.data && dues.data.rows.length === 0 ? <EmptyState message={t("dues.none")} /> : null}
      <ul className="flex max-w-4xl flex-col gap-3">
        {dues.data?.rows.map((r) => (
          <li key={r.flat_id}>
            <Link
              to={`/flats/${r.flat_id}/ledger`}
              className={`flex flex-wrap items-center justify-between gap-3 rounded-card border border-l-8 border-line bg-surface p-4 shadow-card transition hover:shadow-raised focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink ${TONE[r.bucket]}`}
            >
              <span>
                <span className="block text-body font-bold">{r.flat_label}</span>
                <span className="block text-small text-muted">
                  {t("dues.months", { count: r.months_pending })} · {t(`dues.bucket.${r.bucket}`)}
                </span>
                <span className="block text-small">{t(`dues.step.${r.bucket}`)}</span>
              </span>
              <MoneyText paise={r.balance_paise} className="text-section font-bold" />
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
