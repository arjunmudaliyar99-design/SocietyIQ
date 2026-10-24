// One payment (docs/02 §6): confirm (or cheque cleared / bounced), see what it paid, open the
// receipt, or reverse it with a reason. Nothing is ever deleted.
import { ArrowLeft, CheckCircle2, FileDown } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  BigButton,
  Button,
  Card,
  ConfirmDialog,
  ErrorText,
  Field,
  LoadingBlock,
  MoneyText,
  formatDate,
  formatPaise,
  messageKeyOf,
  useCurrentSociety,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

import { MONEY_ROLES, useFile, usePayment, usePaymentAction } from "../api/payments";
import { PaymentStatus } from "./PaymentsPage";

export function PaymentPage() {
  const { paymentId = "" } = useParams();
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const { language } = useSettings();
  const navigate = useNavigate();
  const payment = usePayment(paymentId);
  const action = usePaymentAction(paymentId);
  const file = useFile();
  const roles = useCurrentSociety()?.society.roles ?? [];
  const canAct = roles.some((r) => MONEY_ROLES.includes(r));
  const [asking, setAsking] = useState(false);
  const [undo, setUndo] = useState<"bounce" | "reverse" | null>(null);
  const [reason, setReason] = useState("");

  if (payment.isPending) return <LoadingBlock rows={2} />;
  if (payment.isError) return <ErrorText>{tc(messageKeyOf(payment.error))}</ErrorText>;
  const p = payment.data;
  const open = p.status === "pending" || p.status === "recorded";
  const isCheque = p.method === "cheque";

  return (
    <>
      <div className="mb-4">
        <Button variant="secondary" icon={<ArrowLeft size={22} />} onClick={() => navigate("/payments")}>
          {t("payments.title")}
        </Button>
      </div>
      <h1 className="mb-2 flex flex-wrap items-center gap-3 text-title font-bold">
        <MoneyText paise={p.amount_paise} /> · {p.flat_label} <PaymentStatus status={p.status} />
      </h1>
      <p className="mb-6 text-body">
        {t(`payments.method.${p.method}`)} · {formatDate(p.received_on, language)}
        {p.reference ? ` · ${p.reference}` : ""}
        {p.cheque_bank ? ` · ${p.cheque_bank}` : ""}
        {p.reported_by_resident ? ` · ${t("payments.byResident")}` : ""}
      </p>
      {p.reason ? <p className="mb-6 text-body">{t("payments.reasonLine", { reason: p.reason })}</p> : null}

      {p.allocations.length ? (
        <Card className="mb-6 max-w-2xl">
          <h2 className="mb-3 text-section font-bold">{t("payments.paidTowards")}</h2>
          <ul className="flex flex-col gap-2 text-body">
            {p.allocations.map((a, i) => (
              <li key={i} className="flex justify-between gap-3 border-b border-line pb-2 last:border-b-0">
                <span>{a.settles === "opening" ? t("payments.openingBalance") : a.settles}</span>
                <MoneyText paise={a.amount_paise} />
              </li>
            ))}
            {p.amount_paise > p.allocations.reduce((s, a) => s + a.amount_paise, 0) ? (
              <li className="flex justify-between gap-3">
                <span>{t("payments.advance")}</span>
                <MoneyText paise={p.amount_paise - p.allocations.reduce((s, a) => s + a.amount_paise, 0)} />
              </li>
            ) : null}
          </ul>
        </Card>
      ) : null}

      <div className="flex max-w-2xl flex-col gap-3">
        {canAct && open ? (
          <BigButton icon={<CheckCircle2 size={24} />} onClick={() => setAsking(true)} disabled={action.isPending}>
            {isCheque ? t("payments.cleared") : t("payments.confirm")}
          </BigButton>
        ) : null}
        {p.receipt_number ? (
          <Button variant="secondary" icon={<FileDown size={22} />} onClick={() => file.mutate({ path: `/payments/${p.id}/receipt` })}>
            {t("payments.openReceipt", { number: p.receipt_number })}
          </Button>
        ) : open ? (
          <p className="text-body text-muted">{t("payments.noReceiptYet")}</p>
        ) : null}
        {file.isError ? <ErrorText>{tc(messageKeyOf(file.error))}</ErrorText> : null}
        <Link to={`/flats/${p.flat_id}/ledger`} className="text-body underline">
          {t("ledger.open", { flat: p.flat_label })}
        </Link>

        {canAct && isCheque && p.status === "recorded" && undo === null ? (
          <Button variant="secondary" onClick={() => setUndo("bounce")}>{t("payments.bounced")}</Button>
        ) : null}
        {canAct && (open || p.status === "confirmed") && undo === null ? (
          <Button variant="secondary" onClick={() => setUndo("reverse")}>
            {p.status === "confirmed" ? t("payments.reverse") : t("payments.reject")}
          </Button>
        ) : null}
        {undo ? (
          <Card className="flex flex-col gap-3">
            <p className="text-body">{undo === "bounce" ? t("payments.bounceNote") : t("payments.reverseNote")}</p>
            <Field label={t("billing.cancelReason")} value={reason} onChange={(e) => setReason(e.target.value)} />
            <Button
              variant="danger"
              disabled={reason.trim().length < 3 || action.isPending}
              onClick={() => action.mutate({ action: undo, reason: reason.trim() }, { onSuccess: () => setUndo(null) })}
            >
              {undo === "bounce" ? t("payments.bounced") : p.status === "confirmed" ? t("payments.reverse") : t("payments.reject")}
            </Button>
            <Button variant="secondary" onClick={() => setUndo(null)}>{tc("back")}</Button>
          </Card>
        ) : null}
        {action.isError ? <ErrorText>{tc(messageKeyOf(action.error))}</ErrorText> : null}
      </div>

      <ConfirmDialog
        open={asking}
        question={t("payments.confirmQuestion", { amount: formatPaise(p.amount_paise), flat: p.flat_label })}
        confirmLabel={t("payments.confirmYes")}
        onCancel={() => setAsking(false)}
        onConfirm={() => {
          setAsking(false);
          action.mutate({ action: "confirm" });
        }}
      />
    </>
  );
}
