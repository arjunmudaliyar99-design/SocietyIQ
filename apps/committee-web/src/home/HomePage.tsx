// Committee home (docs/02 §10): at most six tappable cards, then "What needs your attention".
// Cards whose module is not built yet show "Coming soon" (the API says which).
import { ChevronRight, FolderOpen } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import {
  ErrorText,
  LoadingBlock,
  StatCard,
  formatDate,
  formatPaise,
  messageKeyOf,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

import { useHome, type Home } from "../api/compliance";
import { useCanSeeRecords } from "../api/records";

type CardKey = Home["coming_soon"][number];
const SOON_CARDS: CardKey[] = ["collected", "outstanding", "payments_waiting"];
const isSoon = (h: Home, key: CardKey) => h.coming_soon.includes(key);

function attentionParams(params: Record<string, unknown>, language: string): Record<string, unknown> {
  const out = { ...params };
  if (typeof params.date === "string") out.date = formatDate(params.date, language);
  if (typeof params.period === "string")
    out.period = new Intl.DateTimeFormat(language, { month: "long", year: "numeric" }).format(
      new Date(`${params.period}T00:00:00`),
    );
  return out;
}

export function HomePage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const { language } = useSettings();
  const navigate = useNavigate();
  const home = useHome();
  const canSeeRecords = useCanSeeRecords();
  const h = home.data;

  return (
    <>
      <h1 className="mb-6 text-title font-bold">{t("home.title")}</h1>
      {home.isPending ? <LoadingBlock rows={4} /> : null}
      {home.isError ? <ErrorText>{tc(messageKeyOf(home.error))}</ErrorText> : null}
      {h ? (
        <>
          <div className="mb-8 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {SOON_CARDS.filter((key) => isSoon(h, key)).map((key) => (
              <StatCard key={key} label={t(`home.cards.${key}`)} value="—" note={tc("comingSoon")} />
            ))}
            {/* Money and counts stay out of usage analytics (docs/04 §10). */}
            {!isSoon(h, "collected") ? (
              <div className="ph-no-capture">
                <StatCard
                  label={t("home.cards.collected")}
                  value={formatPaise(h.collected_paise)}
                  note={t("home.cards.collectedNote", { count: h.collected_count })}
                  onClick={() => navigate("/payments")}
                />
              </div>
            ) : null}
            {!isSoon(h, "outstanding") ? (
              <div className="ph-no-capture">
                <StatCard
                  label={t("home.cards.outstanding")}
                  value={formatPaise(h.outstanding_paise)}
                  note={t("home.cards.outstandingNote", { count: h.flats_with_dues })}
                  onClick={() => navigate("/dues")}
                />
              </div>
            ) : null}
            {!isSoon(h, "payments_waiting") ? (
              <StatCard
                label={t("home.cards.payments_waiting")}
                value={h.payments_waiting}
                note={t("home.cards.waitingNote")}
                onClick={() => navigate("/payments")}
              />
            ) : null}
            <StatCard
              label={t("home.cards.open_complaints")}
              value={h.open_complaints}
              note={t("home.cards.complaintsNote")}
              onClick={() => navigate("/complaints")}
            />
            <StatCard
              label={t("home.cards.compliance")}
              value={h.compliance_due_soon}
              note={
                h.compliance_overdue > 0
                  ? t("home.cards.complianceOverdue", { count: h.compliance_overdue })
                  : t("home.cards.complianceNote")
              }
              onClick={() => navigate("/compliance")}
            />
            <StatCard
              label={t("home.cards.billing")}
              value={h.next_bill_date ? formatDate(h.next_bill_date, language) : t("home.cards.billingNotSet")}
              note={h.latest_run ? t(`home.cards.lastRun.${h.latest_run.status}`) : t("home.cards.noRuns")}
              onClick={() => navigate("/bills")}
            />
          </div>

          <h2 className="mb-3 text-section font-bold">{t("home.attentionTitle")}</h2>
          {h.attention.length === 0 ? (
            <p className="text-body">{t("home.attentionNone")}</p>
          ) : (
            <ul className="flex max-w-3xl flex-col gap-3">
              {h.attention.map((a) => (
                <li key={`${a.key}-${a.link}`}>
                  <Link
                    to={a.link}
                    className="flex items-center justify-between gap-3 rounded-card border border-line bg-surface p-4 text-body shadow-card hover:border-teal focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
                  >
                    <span>{t(a.key, attentionParams(a.params, language))}</span>
                    <ChevronRight size={22} aria-hidden="true" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {canSeeRecords ? (
            <Link
              to="/records"
              className="mt-8 inline-flex min-h-[48px] items-center gap-2 text-body font-semibold text-teal underline-offset-4 hover:underline focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
            >
              <FolderOpen size={22} aria-hidden="true" />
              {t("admin.homeLink")}
            </Link>
          ) : null}
        </>
      ) : null}
    </>
  );
}
