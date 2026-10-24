import { useCurrentSociety } from "@societyiq/shared";

// docs/02 §2: admin drafts and publishes; committee members and consultants draft only.
export function useCanDraftNotices(): boolean {
  const roles = useCurrentSociety()?.society.roles ?? [];
  return roles.some((r) => ["admin", "committee", "consultant"].includes(r));
}
