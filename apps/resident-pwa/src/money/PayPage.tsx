// Pay (docs/02 §11): the amount, a UPI QR, "Open UPI app", and "I have paid". SocietyIQ never
// holds money: payment goes straight to the society's own account (CLAUDE.md §4.6).
import { CheckCircle2, Copy, ExternalLink } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import {
  BigButton,
  Button,
  Card,
  ErrorText,
  Field,
  LoadingBlock,
  MoneyText,
  SelectField,
  messageKeyOf,
  useTranslation,
} from "@societyiq/shared";

import { useMyFlat, useReportPayment } from "../api/money";

const METHODS = ["upi", "neft", "cash", "cheque"] as const;

function localToday(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function toPaise(text: string): number | null {
  const clean = text.replace(/[₹,\s]/g, "");
  if (!/^\d+(\.\d{1,2})?$/.test(clean)) return null;
  const [whole = "0", fraction = ""] = clean.split(".");
  return Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
}

export function PayPage() {
  const { t } = useTranslation("resident");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const { flat, isPending, isError, error } = useMyFlat();
  const report = useReportPayment(flat?.flat_id);
  const [amount, setAmount] = useState<string | null>(null);
  const [method, setMethod] = useState<(typeof METHODS)[number]>("upi");
  const [paidOn, setPaidOn] = useState(localToday);
  const [reference, setReference] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  if (isPending) return <LoadingBlock rows={2} />;
  if (isError) return <ErrorText>{tc(messageKeyOf(error))}</ErrorText>;
  if (!flat) return <p className="text-body">{t("money.noFlat")}</p>;
  if (!flat.can_pay) return <p className="text-body">{t("money.ownerPays")}</p>;

  const due = Math.max(flat.balance_paise ?? 0, 0);
  const shown = amount ?? (due ? String(due / 100) : "");

  if (report.isSuccess) {
    return (
      <Card className="flex flex-col items-start gap-4 border-2 border-green">
        <CheckCircle2 size={40} className="text-green" aria-hidden="true" />
        <p className="text-section font-bold">{t("money.reported")}</p>
        <p className="text-body">{t("money.reportedBody")}</p>
        <BigButton onClick={() => navigate("/")}>{t("nav.home")}</BigButton>
      </Card>
    );
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    const paise = toPaise(shown);
    if (!paise) return setProblem(t("money.badAmount"));
    if (method !== "cash" && !reference.trim()) return setProblem(t("money.needReference"));
    setProblem(null);
    report.mutate({
      amount_paise: paise,
      method,
      received_on: paidOn,
      reference: reference.trim() || null,
      notes: null,
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <Card className="flex flex-col items-center gap-3 text-center">
        <p className="text-body text-muted">{t("money.flat", { label: flat.label })}</p>
        {due ? (
          <>
            <p className="text-body">{t("money.toPay")}</p>
            <MoneyText paise={due} className="text-stat font-bold" />
          </>
        ) : (
          <p className="text-section font-bold">{t("money.nothingDue")}</p>
        )}
        {flat.pay ? (
          <>
            <img
              src={flat.pay.qr_data_uri}
              alt={t("money.qrAlt", { payee: flat.pay.payee })}
              className="h-56 w-56 rounded-lg border border-line bg-surface p-2"
            />
            <a
              href={flat.pay.upi_link}
              className="inline-flex min-h-[56px] w-full items-center justify-center gap-2 rounded-lg bg-teal px-5 text-section font-semibold text-surface shadow-card transition hover:bg-teal-dark active:scale-[0.98] focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
            >
              <ExternalLink size={24} aria-hidden="true" />
              {t("money.openUpi")}
            </a>
            <p className="text-body">
              {t("money.upiId")}: <strong className="break-all">{flat.pay.upi_id}</strong>
            </p>
            <Button
              variant="secondary"
              icon={<Copy size={20} />}
              onClick={() => void navigator.clipboard?.writeText(flat.pay?.upi_id ?? "").then(() => setCopied(true))}
            >
              {copied ? t("money.copied") : t("money.copyUpi")}
            </Button>
            <p className="text-small text-muted">{t("money.directNote")}</p>
          </>
        ) : due ? (
          <p className="text-body">{t("money.noUpi")}</p>
        ) : null}
      </Card>

      <Card>
        <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
          <h2 className="text-section font-bold">{t("money.iPaid")}</h2>
          <p className="text-body">{t("money.iPaidBody")}</p>
          <Field label={t("money.amount")} inputMode="decimal" value={shown} onChange={(e) => setAmount(e.target.value)} />
          <SelectField
            label={t("money.howPaid")}
            options={METHODS.map((m) => ({ value: m, label: t(`money.method.${m}`) }))}
            value={method}
            onChange={(e) => setMethod(e.target.value as (typeof METHODS)[number])}
          />
          <Field label={t("money.paidOn")} type="date" value={paidOn} onChange={(e) => setPaidOn(e.target.value)} />
          {method !== "cash" ? (
            <Field
              label={method === "cheque" ? t("money.chequeNumber") : t("money.reference")}
              help={method === "cheque" ? undefined : t("money.referenceHelp")}
              value={reference}
              onChange={(e) => setReference(e.target.value)}
            />
          ) : null}
          {problem ? <ErrorText>{problem}</ErrorText> : null}
          {report.isError ? <ErrorText>{tc(messageKeyOf(report.error))}</ErrorText> : null}
          <BigButton type="submit" disabled={report.isPending} className="sm:w-full">
            {t("money.send")}
          </BigButton>
        </form>
      </Card>
    </div>
  );
}
