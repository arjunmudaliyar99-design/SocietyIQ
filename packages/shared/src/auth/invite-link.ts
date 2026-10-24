import type { PendingInvite } from "./AppGate";

/** Invite links look like /invite/<society id>?token=<token> (backend services/societies). */
export function readInvite(location: Pick<Location, "pathname" | "search">): PendingInvite | null {
  const match = /^\/invite\/([0-9a-f-]{36})\/?$/i.exec(location.pathname);
  const token = new URLSearchParams(location.search).get("token");
  return match?.[1] && token ? { societyId: match[1], token } : null;
}
