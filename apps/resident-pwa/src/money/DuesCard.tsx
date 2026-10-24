// Home banner (docs/02 §11): "Flat B-207 · Due ₹4,200 · Pay by 16 Nov".
import { Clock } from "lucide-react";

import { MoneyText, Skeleton, formatDate, useCurrentSociety, useSettings, useTranslation } from "@societyiq/shared";

import { useMyFlat } from "../api/money";

const CARD = "rounded-card bg-gradient-to-br from-teal to-teal-dark p-5 text-surface shadow-raised";

export function DuesCard() {
  const { t } = useTranslation("resident");
  const current = useCurrentSociety();
  if (!current) {
    // Outside the sign-in gate (previews, tests) there is nothing to load.
    return (
      <section aria-label={t("home.pay")} className={CARD}>
        <p className="text-body">{t("home.duesPlaceholder")}</p>
      </section>
    );
  }
  return <SignedInDues />;
}

function SignedInDues() {
  const { t } = useTranslation("resident");
  const { language } = useSettings();
  const { flat, isPending, isError } = useMyFlat();

  if (isPending) {
    return (
      <section aria-label={t("home.pay")} className={CARD}>
        <Skeleton className="mb-3 h-5 w-1/3 opacity-40" />
        <Skeleton className="h-9 w-1/2 opacity-40" />
      </section>
    );
  }
  if (isError || !flat) {
    return (
      <section aria-label={t("home.pay")} className={CARD}>
        <p className="text-body">{isError ? t("money.cannotLoad") : t("money.noFlat")}</p>
      </section>
    );
  }
  const due = flat.balance_paise ?? 0;
  return (
    <section aria-label={t("home.pay")} className={CARD}>
      <p className="text-body font-semibold opacity-90">{t("money.flat", { label: flat.label })}</p>
      {!flat.can_pay ? (
        <p className="mt-2 text-body">{t("money.ownerPays")}</p>
      ) : due > 0 ? (
        <>
          <p className="mt-1 text-small opacity-90">{t("money.due")}</p>
          <MoneyText paise={due} className="block text-stat font-bold" />
          {flat.latest_bill ? (
            <p className="mt-1 text-body">{t("money.payBy", { date: formatDate(flat.latest_bill.due_date, language) })}</p>
          ) : null}
        </>
      ) : (
        <p className="mt-2 text-section font-bold">
          {due < 0 ? t("money.advance", { amount: "" }) : t("money.nothingDue")}
          {due < 0 ? <MoneyText paise={-due} className="ml-1" /> : null}
        </p>
      )}
      {flat.pending_reports ? (
        <p className="mt-3 flex items-center gap-2 rounded-lg bg-surface/15 px-3 py-2 text-body">
          <Clock size={20} aria-hidden="true" />
          {t("money.waiting", { count: flat.pending_reports })}
        </p>
      ) : null}
    </section>
  );
}
