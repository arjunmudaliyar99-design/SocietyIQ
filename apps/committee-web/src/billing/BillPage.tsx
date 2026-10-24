// One bill (docs/02 §5): lines, arrears, interest and total; download the PDF. A bill is never
// edited: cancel it with a reason, then issue a corrected one.
import { ArrowLeft, FileDown, RotateCcw } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  BigButton,
  Button,
  Card,
  ErrorText,
  Field,
  MoneyText,
  formatDate,
  messageKeyOf,
  useCurrentSociety,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

import { useBill, useBillAction, useOpenPdf } from "../api/billing";

export function BillPage() {
  const { billId = "" } = useParams();
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const { language } = useSettings();
  const navigate = useNavigate();
  const bill = useBill(billId);
  const action = useBillAction(billId);
  const openPdf = useOpenPdf();
  const roles = useCurrentSociety()?.society.roles ?? [];
  const canChange = roles.some((r) => ["admin", "treasurer"].includes(r));
  const [cancelling, setCancelling] = useState(false);
  const [reason, setReason] = useState("");

  if (bill.isPending) return <p role="status">{tc("loading")}</p>;
  if (bill.isError) return <ErrorText>{tc(messageKeyOf(bill.error))}</ErrorText>;
  const b = bill.data;
  const charges = b.lines.filter((l) => l.line_type !== "interest");

  return (
    <>
      <div className="mb-4">
        <Button variant="secondary" icon={<ArrowLeft size={22} />} onClick={() => navigate(`/bills/runs/${b.billing_run_id}`)}>
          {t("billing.backToRun")}
        </Button>
      </div>
      <h1 className="mb-2 text-title font-bold">{t("billing.billTitle", { number: b.bill_number })}</h1>
      <p className="mb-6 text-body">
        <Link to={`/flats/${b.flat_id}`} className="font-semibold underline">{b.flat_label}</Link>
        {b.member_name ? ` · ${b.member_name}` : ""} · {t(`billing.billStatus.${b.status}`)}
      </p>
      {b.status === "cancelled" ? (
        <Card className="mb-6 max-w-2xl border-2 border-red">
          <p className="text-body font-semibold">{t("billing.cancelledWith", { reason: b.cancelled_reason ?? "" })}</p>
          {b.replaced_by_bill_id ? (
            <Link to={`/bills/${b.replaced_by_bill_id}`} className="text-body underline">{t("billing.seeCorrected")}</Link>
          ) : null}
        </Card>
      ) : null}

      <Card className="mb-6 max-w-2xl">
        <p className="mb-3 text-small text-muted">
          {t("billing.dates", { bill: formatDate(b.bill_date, language), due: formatDate(b.due_date, language) })}
        </p>
        <table className="w-full text-body">
          <caption className="sr-only">{t("billing.billTitle", { number: b.bill_number })}</caption>
          <tbody>
            {charges.map((l) => (
              <tr key={l.id} className="border-b border-line">
                <th scope="row" className="py-2 text-left font-normal">{l.line_type === "rounding" ? t("preview.rounding") : l.description}</th>
                <td className="py-2 text-right"><MoneyText paise={l.amount_paise} /></td>
              </tr>
            ))}
            <tr className="border-b border-line font-semibold">
              <th scope="row" className="py-2 text-left">{t("billing.charges")}</th>
              <td className="py-2 text-right"><MoneyText paise={b.charges_paise} /></td>
            </tr>
            {b.arrears_paise ? (
              <tr className="border-b border-line">
                <th scope="row" className="py-2 text-left font-normal">{t("billing.arrears")}</th>
                <td className="py-2 text-right"><MoneyText paise={b.arrears_paise} /></td>
              </tr>
            ) : null}
            {b.advance_paise ? (
              <tr className="border-b border-line">
                <th scope="row" className="py-2 text-left font-normal">{t("billing.advance")}</th>
                <td className="py-2 text-right">− <MoneyText paise={b.advance_paise} /></td>
              </tr>
            ) : null}
            {b.interest_paise ? (
              <tr className="border-b border-line">
                <th scope="row" className="py-2 text-left font-normal">{t("billing.interest")}</th>
                <td className="py-2 text-right"><MoneyText paise={b.interest_paise} /></td>
              </tr>
            ) : null}
            <tr className="text-section font-bold">
              <th scope="row" className="pt-3 text-left">{t("billing.totalDue")}</th>
              <td className="pt-3 text-right"><MoneyText paise={b.total_due_paise} /></td>
            </tr>
          </tbody>
        </table>
      </Card>

      <div className="flex max-w-2xl flex-col gap-3">
        <BigButton icon={<FileDown size={24} />} onClick={() => openPdf.mutate(`/bills/${b.id}/pdf`)} disabled={openPdf.isPending}>
          {t("billing.openPdf")}
        </BigButton>
        {openPdf.isError ? <ErrorText>{tc(messageKeyOf(openPdf.error))}</ErrorText> : null}

        {canChange && b.status === "issued" && !cancelling ? (
          <Button variant="secondary" onClick={() => setCancelling(true)}>{t("billing.cancelBill")}</Button>
        ) : null}
        {cancelling ? (
          <Card className="flex flex-col gap-3">
            <p className="text-body">{t("billing.cancelBillNote")}</p>
            <Field label={t("billing.cancelReason")} value={reason} onChange={(e) => setReason(e.target.value)} />
            <Button
              variant="danger"
              disabled={reason.trim().length < 3 || action.isPending}
              onClick={() => action.mutate({ action: "cancel", reason: reason.trim() }, { onSuccess: () => setCancelling(false) })}
            >
              {t("billing.cancelBill")}
            </Button>
          </Card>
        ) : null}
        {canChange && b.status === "cancelled" && !b.replaced_by_bill_id ? (
          <Button
            icon={<RotateCcw size={22} />}
            disabled={action.isPending}
            onClick={() => action.mutate({ action: "reissue" }, { onSuccess: (nb) => navigate(`/bills/${nb.id}`) })}
          >
            {t("billing.reissue")}
          </Button>
        ) : null}
        {action.isError ? <ErrorText>{tc(messageKeyOf(action.error))}</ErrorText> : null}
      </div>
    </>
  );
}
