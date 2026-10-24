// TanStack Query hooks for payments, dues and the flat ledger (docs/02 §6-7).
import { useAuth, useMutation, useQuery, useQueryClient, type Schemas } from "@societyiq/shared";

import { useSocietyId } from "./flats";

export type Payment = Schemas["PaymentOut"];
export type PaymentDetail = Schemas["PaymentDetailOut"];
export type PaymentInput = Schemas["PaymentIn"];
export type Dues = Schemas["DuesOut"];
export type FlatLedger = Schemas["FlatLedgerOut"];

/** docs/02 §2: admin, treasurer and consultant record payments. */
export const MONEY_ROLES = ["admin", "treasurer", "consultant"];

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

export function usePayments(status?: string) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "payments", status ?? "all"],
    queryFn: () => api.get<Payment[]>(`${base}/payments${status ? `?status=${status}` : ""}`),
  });
}

export function usePayment(paymentId: string) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "payments", "one", paymentId],
    queryFn: () => api.get<PaymentDetail>(`${base}/payments/${paymentId}`),
  });
}

export function useRecordPayment() {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: PaymentInput) => api.post<PaymentDetail>(`${base}/payments`, body),
    onSuccess: invalidate,
  });
}

export function usePaymentAction(paymentId: string) {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ action, reason }: { action: "confirm" | "bounce" | "reverse"; reason?: string }) =>
      api.post<PaymentDetail>(`${base}/payments/${paymentId}/${action}`, action === "confirm" ? {} : { reason }),
    onSuccess: invalidate,
  });
}

export function useDues(bucket?: string) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "dues", bucket ?? "all"],
    queryFn: () => api.get<Dues>(`${base}/dues${bucket ? `?bucket=${bucket}` : ""}`),
  });
}

export function useFlatLedger(flatId: string) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "flats", flatId, "ledger"],
    queryFn: () => api.get<FlatLedger>(`${base}/flats/${flatId}/ledger`),
    enabled: Boolean(flatId),
  });
}

/** Downloads (Excel) or opens (PDF) a file from the API. */
export function useFile() {
  const { api, base } = useBase();
  return useMutation({
    mutationFn: async ({ path, filename }: { path: string; filename?: string }) => {
      const blob = await api.download(`${base}${path}`);
      const url = URL.createObjectURL(blob);
      if (filename) {
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        link.click();
      } else {
        window.open(url, "_blank", "noopener");
      }
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    },
  });
}
