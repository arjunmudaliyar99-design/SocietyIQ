// Record a payment (docs/02 §6): one tap, amount pre-filled with what the flat owes.
import { useMemo, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import {
  BigButton,
  Button,
  Card,
  ErrorText,
  Field,
  SelectField,
  formatPaise,
  messageKeyOf,
  useTranslation,
} from "@societyiq/shared";

import { useFlats } from "../api/flats";
import { useRecordPayment } from "../api/payments";
import { flatLabel, paiseToRupeesInput, rupeesToPaise } from "../flats/labels";

const METHODS = ["cash", "upi", "neft", "cheque", "other"] as const;

function localToday(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function RecordPaymentPage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const flats = useFlats();
  const record = useRecordPayment();
  const [flatId, setFlatId] = useState(params.get("flat") ?? "");
  const [amount, setAmount] = useState("");
  const [touchedAmount, setTouchedAmount] = useState(false);
  const [method, setMethod] = useState<(typeof METHODS)[number]>("cash");
  const [received, setReceived] = useState(localToday);
  const [reference, setReference] = useState("");
  const [bank, setBank] = useState("");
  const [chequeDate, setChequeDate] = useState("");
  const [confirmNow, setConfirmNow] = useState(true);
  const [problem, setProblem] = useState<string | null>(null);

  const list = useMemo(() => flats.data ?? [], [flats.data]);
  const wings = new Set(list.map((f) => f.wing_name)).size;
  const flat = list.find((f) => f.id === flatId);
  const owed = flat && flat.balance_paise > 0 ? flat.balance_paise : 0;
  const shownAmount = touchedAmount ? amount : paiseToRupeesInput(owed || null);
  const options = useMemo(
    () => [
      { value: "", label: t("payments.chooseFlat") },
      ...list.map((f) => ({ value: f.id, label: `${flatLabel(f, wings)}${f.primary_member ? ` · ${f.primary_member}` : ""}` })),
    ],
    [list, wings, t],
  );

  function submit(e: FormEvent) {
    e.preventDefault();
    const paise = rupeesToPaise(shownAmount);
    if (!flatId) return setProblem(t("payments.needFlat"));
    if (!paise) return setProblem(t("flats.invalidAmount"));
    if (method === "cheque" && !reference.trim()) return setProblem(t("payments.needChequeNumber"));
    setProblem(null);
    record.mutate(
      {
        flat_id: flatId,
        amount_paise: paise,
        method,
        received_on: received,
        reference: reference.trim() || null,
        cheque_bank: method === "cheque" ? bank.trim() || null : null,
        cheque_date: method === "cheque" && chequeDate ? chequeDate : null,
        notes: null,
        confirm_now: method !== "cheque" && confirmNow,
      },
      { onSuccess: (p) => navigate(`/payments/${p.id}`) },
    );
  }

  return (
    <>
      <h1 className="mb-6 text-title font-bold">{t("payments.record")}</h1>
      <Card className="max-w-2xl">
        <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
          <SelectField label={t("payments.flat")} options={options} value={flatId} onChange={(e) => setFlatId(e.target.value)} />
          {flat ? (
            <p className="text-body">
              {owed ? t("payments.owes", { amount: formatPaise(owed) }) : t("flats.nothingDue")}
            </p>
          ) : null}
          <Field
            label={t("payments.amount")}
            inputMode="decimal"
            value={shownAmount}
            onChange={(e) => {
              setTouchedAmount(true);
              setAmount(e.target.value);
            }}
          />
          <SelectField
            label={t("payments.howPaid")}
            options={METHODS.map((m) => ({ value: m, label: t(`payments.method.${m}`) }))}
            value={method}
            onChange={(e) => setMethod(e.target.value as (typeof METHODS)[number])}
          />
          <Field label={t("payments.receivedOn")} type="date" value={received} onChange={(e) => setReceived(e.target.value)} />
          {method !== "cash" ? (
            <Field
              label={method === "cheque" ? t("payments.chequeNumber") : t("payments.reference")}
              help={method === "cheque" ? undefined : t("payments.referenceHelp")}
              value={reference}
              onChange={(e) => setReference(e.target.value)}
            />
          ) : null}
          {method === "cheque" ? (
            <>
              <Field label={t("payments.chequeBank")} value={bank} onChange={(e) => setBank(e.target.value)} />
              <Field label={t("payments.chequeDate")} type="date" value={chequeDate} onChange={(e) => setChequeDate(e.target.value)} />
              <p className="text-small text-muted">{t("payments.chequeNote")}</p>
            </>
          ) : (
            <label className="flex items-start gap-3 text-body">
              <input type="checkbox" checked={confirmNow} onChange={(e) => setConfirmNow(e.target.checked)} className="mt-1 h-7 w-7 accent-teal" />
              {t("payments.confirmNow")}
            </label>
          )}
          {problem ? <ErrorText>{problem}</ErrorText> : null}
          {record.isError ? <ErrorText>{tc(messageKeyOf(record.error))}</ErrorText> : null}
          <BigButton type="submit" disabled={record.isPending}>
            {method !== "cheque" && confirmNow ? t("payments.saveAndReceipt") : t("payments.save")}
          </BigButton>
          <Button variant="secondary" onClick={() => navigate(-1)}>
            {tc("back")}
          </Button>
        </form>
      </Card>
    </>
  );
}
