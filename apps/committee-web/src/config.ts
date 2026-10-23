import type { Contact } from "@societyiq/shared";

// Support contact comes only from configuration (CLAUDE.md §4a).
export const support: Contact = {
  email: import.meta.env.VITE_SUPPORT_EMAIL || "support@example.com",
  phone: import.meta.env.VITE_SUPPORT_PHONE || undefined,
  hours: import.meta.env.VITE_SUPPORT_HOURS || undefined,
};
