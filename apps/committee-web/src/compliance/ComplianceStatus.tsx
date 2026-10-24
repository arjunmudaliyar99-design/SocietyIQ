import { CircleAlert, CircleCheck, Clock } from "lucide-react";
import type { ReactNode } from "react";

import { useTranslation } from "@societyiq/shared";

import type { Item } from "../api/compliance";

// Word + icon + colour, never colour alone (docs/03 §3).
const STYLE: Record<Item["status"], { className: string; icon: ReactNode }> = {
  overdue: { className: "text-red border-red", icon: <CircleAlert size={18} /> },
  due_soon: { className: "text-ink border-terracotta", icon: <Clock size={18} /> },
  ok: { className: "text-green border-green", icon: <CircleCheck size={18} /> },
  done: { className: "text-muted border-muted", icon: <CircleCheck size={18} /> },
};

export function ComplianceStatus({ status }: { status: Item["status"] }) {
  const { t } = useTranslation("committee");
  const style = STYLE[status];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border-2 bg-surface px-3 py-1 text-small font-semibold ${style.className}`}
    >
      <span aria-hidden="true">{style.icon}</span>
      {t(`compliance.status.${status}`)}
    </span>
  );
}
