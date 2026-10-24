// TanStack Query hooks for billing runs and bills (docs/02 §5).
import { useAuth, useMutation, useQuery, useQueryClient, type Schemas } from "@societyiq/shared";

import { useSocietyId } from "./flats";

export type Run = Schemas["RunOut"];
export type RunDetail = Schemas["RunDetailOut"];
export type BillSummary = Schemas["BillSummaryOut"];
export type Bill = Schemas["BillOut"];

function useBase() {
  const { api } = useAuth();
  const societyId = useSocietyId();
  return { api, societyId, base: `/societies/${societyId}` };
}

function useInvalidate() {
  const client = useQueryClient();
  const societyId = useSocietyId();
  return () => client.invalidateQueries({ queryKey: ["societies", societyId] });
}

export function useRuns() {
  const { api, societyId, base } = useBase();
  return useQuery({ queryKey: ["societies", societyId, "runs"], queryFn: () => api.get<Run[]>(`${base}/billing-runs`) });
}

export function useRun(runId: string) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "runs", runId],
    queryFn: () => api.get<RunDetail>(`${base}/billing-runs/${runId}`),
  });
}

export function useCreateRun() {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (periodStart: string) => api.post<Run>(`${base}/billing-runs`, { period_start: periodStart }),
    onSuccess: invalidate,
  });
}

export function useRunAction(runId: string) {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ action, reason }: { action: "approve" | "cancel"; reason?: string }) =>
      api.post<Run>(`${base}/billing-runs/${runId}/${action}`, action === "cancel" ? { reason } : {}),
    onSuccess: invalidate,
  });
}

export function useBill(billId: string) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "bills", billId],
    queryFn: () => api.get<Bill>(`${base}/bills/${billId}`),
  });
}

export function useFlatBills(flatId: string) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "bills", "flat", flatId],
    queryFn: () => api.get<BillSummary[]>(`${base}/bills?flat_id=${flatId}`),
  });
}

export function useBillAction(billId: string) {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ action, reason }: { action: "cancel" | "reissue"; reason?: string }) =>
      api.post<BillSummary>(`${base}/bills/${billId}/${action}`, action === "cancel" ? { reason } : {}),
    onSuccess: invalidate,
  });
}

/** Opens a PDF from the API in a new tab (the browser shows, prints or saves it). */
export function useOpenPdf() {
  const { api, base } = useBase();
  return useMutation({
    mutationFn: async (path: string) => {
      const blob = await api.download(`${base}${path}`);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener");
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    },
  });
}
