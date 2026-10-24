// Invite form rules shared by the setup wizard and the people page.

export const COMMITTEE_ROLES = ["admin", "treasurer", "committee", "consultant", "auditor"] as const;
export type CommitteeRole = (typeof COMMITTEE_ROLES)[number];

export interface InviteDraft {
  name: string;
  email: string;
  phone: string;
  role: CommitteeRole;
}

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** People type 10 digits (docs/03 §6); the API stores E.164. */
export function phoneToE164(phone: string): string {
  return `+91${phone.replace(/\D/g, "").slice(-10)}`;
}

/** Returns a committee i18n key describing the first problem, or null. */
export function validateInvite(inv: InviteDraft): string | null {
  const email = inv.email.trim();
  const digits = inv.phone.replace(/\D/g, "");
  if (!email && !digits) return "setup.needContact";
  if (email && !EMAIL.test(email)) return "setup.invalidEmail";
  if (digits && !(digits.length === 10 || (digits.length === 12 && digits.startsWith("91")))) {
    return "setup.invalidPhone";
  }
  return null;
}
