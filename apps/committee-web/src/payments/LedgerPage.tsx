// A flat's account (docs/02 §7): every bill, payment, interest line and reversal with a
// running balance, and the statement for a recovery application as PDF or Excel.
import { ArrowLeft, FileDown, FileSpreadsheet, Wallet } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import {
  Button,
  Card,
  ErrorText,
  LoadingBlock,
  MoneyText,
  StatCard,
  formatDate,
  messageKeyOf,
  useCurrentSociety,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

import { MONEY_ROLES, useFile, useFlatLedger } from "../api/payments";

export function LedgerPage() {
  const { flatId = "" } = useParams();
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const { language } = useSettings();
  const navigate = useNavigate();
  const ledger = useFlatLedger(flatId);
  const file = useFile();
  const roles = useCurrentSociety()?.society.roles ?? [];
  const canRecord = roles.some((r) => MONEY_ROLES.includes(r));

  if (ledger.isPending) return <LoadingBlock />;
  if (ledger.isError) return <ErrorText>{tc(messageKeyOf(ledger.error))}</ErrorText>;
  const l = ledger.data;

  return (
    <>
      <div className="mb-4">
        <Button variant="secondary" icon={<ArrowLeft size={22} />} onClick={() => navigate(`/flats/${l.flat_id}`)}>
          {t("flats.flatTitle", { label: l.flat_label })}
        </Button>
      </div>
      <h1 className="mb-6 text-title font-bold">{t("ledger.title", { flat: l.flat_label })}</h1>
      <div className="mb-6 grid max-w-3xl gap-3 sm:grid-cols-2">
        <StatCard
          label={l.balance_paise < 0 ? t("flats.advance") : t("flats.balance")}
          value={<MoneyText paise={Math.abs(l.balance_paise)} />}
        />
        <StatCard label={t("ledger.monthsPending")} value={l.months_pending} />
      </div>
      <div className="mb-6 flex flex-wrap gap-3">
        {canRecord ? (
          <Button icon={<Wallet size={22} />} onClick={() => navigate(`/payments/new?flat=${l.flat_id}`)}>
            {t("payments.record")}
          </Button>
        ) : null}
        <Button variant="secondary" icon={<FileDown size={22} />} onClick={() => file.mutate({ path: `/flats/${l.flat_id}/ledger/export?format=pdf` })}>
          {t("ledger.exportPdf")}
        </Button>
        <Button
          variant="secondary"
          icon={<FileSpreadsheet size={22} />}
          onClick={() => file.mutate({ path: `/flats/${l.flat_id}/ledger/export?format=xlsx`, filename: `ledger-${l.flat_label}.xlsx` })}
        >
          {t("ledger.exportExcel")}
        </Button>
      </div>
      {file.isError ? <ErrorText>{tc(messageKeyOf(file.error))}</ErrorText> : null}
      <p className="mb-4 max-w-3xl text-small text-muted">{t("ledger.recoveryNote")}</p>

      {l.lines.length === 0 ? (
        <Card>
          <p className="text-body">{t("ledger.empty")}</p>
        </Card>
      ) : (
        <div className="overflow-x-auto rounded-card border border-line bg-surface shadow-card">
          <table className="min-w-full text-body">
            <caption className="sr-only">{t("ledger.title", { flat: l.flat_label })}</caption>
            <thead>
              <tr className="border-b border-line text-left">
                <th scope="col" className="p-3">{t("ledger.date")}</th>
                <th scope="col" className="p-3">{t("ledger.details")}</th>
                <th scope="col" className="p-3 text-right">{t("ledger.charged")}</th>
                <th scope="col" className="p-3 text-right">{t("ledger.paid")}</th>
                <th scope="col" className="p-3 text-right">{t("ledger.balance")}</th>
              </tr>
            </thead>
            <tbody>
              {l.lines.map((line) => (
                <tr key={line.id} className="border-b border-line last:border-b-0">
                  <td className="whitespace-nowrap p-3">{formatDate(line.entry_date, language)}</td>
                  <td className="p-3">
                    {t(`ledger.type.${line.entry_type}`)}
                    {line.document ? ` · ${line.document}` : ""}
                    {line.reason ? <span className="block text-small text-muted">{line.reason}</span> : null}
                  </td>
                  <td className="p-3 text-right">{line.amount_paise > 0 ? <MoneyText paise={line.amount_paise} /> : null}</td>
                  <td className="p-3 text-right">{line.amount_paise < 0 ? <MoneyText paise={-line.amount_paise} /> : null}</td>
                  <td className="p-3 text-right font-semibold"><MoneyText paise={line.running_paise} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
