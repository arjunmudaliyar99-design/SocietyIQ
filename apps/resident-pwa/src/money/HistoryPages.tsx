// My bills and My receipts (docs/02 §11): newest first, each opens its PDF.
import { FileDown } from "lucide-react";

import {
  Button,
  Card,
  EmptyState,
  ErrorText,
  LoadingBlock,
  MoneyText,
  formatDate,
  messageKeyOf,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

import { useMyBills, useMyFlat, useMyPayments, useOpenPdf } from "../api/money";

export function MyBillsList() {
  const { t } = useTranslation("resident");
  const { t: tc } = useTranslation();
  const { flat } = useMyFlat();
  const bills = useMyBills(flat?.can_pay ? flat.flat_id : undefined);
  const open = useOpenPdf();

  if (flat && !flat.can_pay) return <p className="text-body">{t("money.ownerPays")}</p>;
  if (bills.isPending) return <LoadingBlock />;
  if (bills.isError) return <ErrorText>{tc(messageKeyOf(bills.error))}</ErrorText>;
  if (bills.data.length === 0) return <EmptyState message={t("money.noBills")} />;
  return (
    <ul className="flex flex-col gap-3">
      {bills.data.map((b) => (
        <li key={b.id}>
          <Card className="flex flex-col gap-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-body font-bold">{b.bill_number}</p>
                <p className="text-small text-muted">{t(`money.billStatus.${b.status}`)}</p>
              </div>
              <MoneyText paise={b.total_due_paise} className="text-section font-bold" />
            </div>
            <Button
              variant="secondary"
              icon={<FileDown size={20} />}
              onClick={() => open.mutate(`/my/flats/${b.flat_id}/bills/${b.id}/pdf`)}
            >
              {t("money.openBill")}
            </Button>
          </Card>
        </li>
      ))}
      {open.isError ? <ErrorText>{tc(messageKeyOf(open.error))}</ErrorText> : null}
    </ul>
  );
}

export function MyReceiptsList() {
  const { t } = useTranslation("resident");
  const { t: tc } = useTranslation();
  const { language } = useSettings();
  const { flat } = useMyFlat();
  const payments = useMyPayments(flat?.can_pay ? flat.flat_id : undefined);
  const open = useOpenPdf();

  if (flat && !flat.can_pay) return <p className="text-body">{t("money.ownerPays")}</p>;
  if (payments.isPending) return <LoadingBlock />;
  if (payments.isError) return <ErrorText>{tc(messageKeyOf(payments.error))}</ErrorText>;
  if (payments.data.length === 0) return <EmptyState message={t("money.noPayments")} />;
  return (
    <ul className="flex flex-col gap-3">
      {payments.data.map((p) => (
        <li key={p.id}>
          <Card className="flex flex-col gap-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-body font-bold">{formatDate(p.received_on, language)}</p>
                <p className="text-small text-muted">
                  {p.status === "confirmed" && p.receipt_number
                    ? p.receipt_number
                    : t(`money.paymentStatus.${p.status}`)}
                </p>
              </div>
              <MoneyText paise={p.amount_paise} className="text-section font-bold" />
            </div>
            {p.status === "confirmed" && p.receipt_number ? (
              <Button
                variant="secondary"
                icon={<FileDown size={20} />}
                onClick={() => open.mutate(`/my/flats/${p.flat_id}/payments/${p.id}/receipt`)}
              >
                {t("money.openReceipt")}
              </Button>
            ) : null}
          </Card>
        </li>
      ))}
      {open.isError ? <ErrorText>{tc(messageKeyOf(open.error))}</ErrorText> : null}
    </ul>
  );
}
