import { useTranslation } from "react-i18next";

import { formatPaise } from "../utils/money";

export interface MoneyTextProps {
  paise: number;
  /** Residents see a negative balance as "₹500 advance", never "-₹500" (docs/03 §5). */
  forResident?: boolean;
  className?: string;
}

export function MoneyText({ paise, forResident = false, className = "" }: MoneyTextProps) {
  const { t } = useTranslation();
  const text =
    forResident && paise < 0 ? t("moneyAdvance", { amount: formatPaise(-paise) }) : formatPaise(paise);
  return <span className={`tabular ph-no-capture ${className}`}>{text}</span>;
}
