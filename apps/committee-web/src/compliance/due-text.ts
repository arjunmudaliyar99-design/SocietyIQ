import { formatDate } from "@societyiq/shared";

import type { Item } from "../api/compliance";

/** "Due in 12 days (5 Nov 2026)", "5 days overdue", "Done on ..." */
export function dueText(item: Item, t: (key: string, o?: Record<string, unknown>) => string, language: string): string {
  if (item.status === "done") return t("compliance.doneOn", { date: formatDate(item.last_done_on ?? item.next_due_on, language) });
  if (item.days_left < 0) return t("compliance.overdueBy", { count: -item.days_left });
  if (item.days_left === 0) return t("compliance.dueToday");
  return t("compliance.dueIn", { count: item.days_left, date: formatDate(item.next_due_on, language) });
}
