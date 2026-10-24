// TanStack Query hooks for the audit log and the data export (docs/07 M11).
import { useAuth, useCurrentSociety, useInfiniteQuery, useMutation, type Schemas } from "@societyiq/shared";

import { useSocietyId } from "./flats";

export type AuditEntry = Schemas["AuditEntryOut"];
export type AuditPage = Schemas["AuditPageOut"];

// docs/02 §2: admin, treasurer and auditor see the audit log and may export.
const RECORD_ROLES = ["admin", "treasurer", "auditor"];

export function useCanSeeRecords(): boolean {
  const current = useCurrentSociety();
  return Boolean(current?.society.roles.some((r) => RECORD_ROLES.includes(r)));
}

export function useAuditLog(entityType: string, enabled: boolean) {
  const { api } = useAuth();
  const societyId = useSocietyId();
  return useInfiniteQuery({
    queryKey: ["societies", societyId, "audit", entityType],
    initialPageParam: null as number | null,
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams();
      if (entityType) params.set("entity_type", entityType);
      if (pageParam) params.set("before_id", String(pageParam));
      const query = params.toString();
      return api.get<AuditPage>(`/societies/${societyId}/audit-log${query ? `?${query}` : ""}`);
    },
    getNextPageParam: (last) => last.next_before_id,
    enabled,
  });
}

/** Downloads all society data; the browser saves the file. */
export function useExport() {
  const { api } = useAuth();
  const societyId = useSocietyId();
  return useMutation({
    mutationFn: async (format: "xlsx" | "pdf") => {
      const blob = await api.download(`/societies/${societyId}/export?format=${format}`);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `societyiq-export.${format}`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    },
  });
}
