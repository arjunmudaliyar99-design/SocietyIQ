import type { NoticeAudience, NoticeLanguage } from "@societyiq/shared";

export interface NoticeValues {
  title: string;
  body: string;
  language: NoticeLanguage;
  audience: NoticeAudience;
  wingId: string;
}

export const AUDIENCES: NoticeAudience[] = ["all", "owners", "tenants", "wing"];

export function isComplete(v: NoticeValues): boolean {
  return Boolean(v.title.trim() && v.body.trim() && (v.audience !== "wing" || v.wingId));
}
