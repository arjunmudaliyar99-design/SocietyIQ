import { CircleAlert, CircleCheck, CircleDot, Clock } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

export type Status = "paid" | "pending" | "overdue" | "open" | "resolved";

// Word + icon + colour, never colour alone (docs/03 §3).
const STYLE: Record<Status, { className: string; icon: ReactNode }> = {
  paid: { className: "text-green border-green", icon: <CircleCheck size={18} /> },
  resolved: { className: "text-green border-green", icon: <CircleCheck size={18} /> },
  pending: { className: "text-ink border-muted", icon: <Clock size={18} /> },
  open: { className: "text-teal border-teal", icon: <CircleDot size={18} /> },
  overdue: { className: "text-red border-red", icon: <CircleAlert size={18} /> },
};

export function StatusPill({ status }: { status: Status }) {
  const { t } = useTranslation();
  const style = STYLE[status];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border-2 bg-surface px-3 py-1 text-small font-semibold ${style.className}`}
    >
      <span aria-hidden="true">{style.icon}</span>
      {t(`status.${status}`)}
    </span>
  );
}
