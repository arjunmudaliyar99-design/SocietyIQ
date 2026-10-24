// The resident's own flats: dues, how to pay, bills and receipts (docs/02 §11, docs/07 M7).
import { useAuth, useCurrentSociety, useMutation, useQuery, useQueryClient, type Schemas } from "@societyiq/shared";

export type MyFlat = Schemas["ResidentFlatOut"];
export type MyBill = Schemas["BillSummaryOut"];
export type MyPayment = Schemas["PaymentOut"];
export type PaymentReport = Schemas["ResidentPaymentIn"];

const FLAT_KEY = "societyiq.flat";

function useBase() {
  const { api } = useAuth();
  const societyId = useCurrentSociety()?.society.id ?? "";
  return { api, societyId, base: `/societies/${societyId}` };
}

export function useMyFlats() {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "my-flats"],
    queryFn: () => api.get<MyFlat[]>(`${base}/my/flats`),
    enabled: Boolean(societyId),
  });
}

export function readChosenFlat(): string | null {
  try {
    return window.localStorage.getItem(FLAT_KEY);
  } catch {
    return null;
  }
}

export function chooseFlat(flatId: string): void {
  try {
    window.localStorage.setItem(FLAT_KEY, flatId);
  } catch {
    // Without storage the first flat is shown; nothing breaks.
  }
}

/** The flat the resident is looking at: their choice, else the first they can pay for. */
export function useMyFlat(): { flat: MyFlat | undefined; flats: MyFlat[]; isPending: boolean; isError: boolean; error: unknown } {
  const flats = useMyFlats();
  const list = flats.data ?? [];
  const chosen = readChosenFlat();
  const flat = list.find((f) => f.flat_id === chosen) ?? list.find((f) => f.can_pay) ?? list[0];
  return { flat, flats: list, isPending: flats.isPending, isError: flats.isError, error: flats.error };
}

export function useMyBills(flatId: string | undefined) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "my-flats", flatId, "bills"],
    queryFn: () => api.get<MyBill[]>(`${base}/my/flats/${flatId}/bills`),
    enabled: Boolean(societyId && flatId),
  });
}

export function useMyPayments(flatId: string | undefined) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "my-flats", flatId, "payments"],
    queryFn: () => api.get<MyPayment[]>(`${base}/my/flats/${flatId}/payments`),
    enabled: Boolean(societyId && flatId),
  });
}

export function useReportPayment(flatId: string | undefined) {
  const { api, societyId, base } = useBase();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: PaymentReport) => api.post<MyPayment>(`${base}/flats/${flatId}/payment-reports`, body),
    onSuccess: () => client.invalidateQueries({ queryKey: ["societies", societyId, "my-flats"] }),
  });
}

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
