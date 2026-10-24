import { Link } from "react-router-dom";

import { Card, MoneyText, useTranslation } from "@societyiq/shared";

import { useFlatBills } from "../api/billing";

/** The flat's bills, newest first (docs/02 §5). */
export function FlatBills({ flatId }: { flatId: string }) {
  const { t } = useTranslation("committee");
  const bills = useFlatBills(flatId);
  return (
    <section className="mt-10">
      <h2 className="mb-4 text-section font-bold">{t("billing.flatBills")}</h2>
      {bills.data?.length === 0 ? <p className="text-body">{t("billing.noBills")}</p> : null}
      <ul className="flex max-w-3xl flex-col gap-3">
        {bills.data?.map((b) => (
          <li key={b.id}>
            <Card className="flex flex-wrap items-center justify-between gap-3">
              <Link to={`/bills/${b.id}`} className="text-body font-bold underline">
                {b.bill_number}
              </Link>
              <span className="text-body">
                <MoneyText paise={b.total_due_paise} /> · {t(`billing.billStatus.${b.status}`)}
              </span>
            </Card>
          </li>
        ))}
      </ul>
    </section>
  );
}
