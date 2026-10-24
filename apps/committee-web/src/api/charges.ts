// TanStack Query hooks for charge setup, per-flat extras and the preview (docs/02 §5).
import { useAuth, useMutation, useQuery, useQueryClient, type Schemas } from "@societyiq/shared";

import { useSocietyId } from "./flats";

export type StandardHead = Schemas["StandardHeadOut"];
export type ChargeHead = Schemas["ChargeHeadOut"];
export type ChargeHeadInput = Schemas["ChargeHeadIn"];
export type ChargeHeadUpdate = Schemas["ChargeHeadUpdate"];
export type ChargeHeadSaved = Schemas["ChargeHeadSaved"];
export type LegalProblem = Schemas["LegalProblemOut"];
export type ChargesPreview = Schemas["PreviewOut"];
export type SocietySettings = Schemas["SettingsOut"];
export type SettingsUpdate = Schemas["SettingsUpdate"];
export type Override = Schemas["OverrideOut"];
export type OverrideInput = Schemas["OverrideIn"];
export type Parking = Schemas["ParkingOut"];
export type ParkingInput = Schemas["ParkingIn"];
export type PropertyTax = Schemas["PropertyTaxOut"];
export type PropertyTaxInput = Schemas["PropertyTaxIn"];
export type TaxImport = Schemas["TaxImportOut"];

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

export function useStandardHeads() {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "standard-heads"],
    queryFn: () => api.get<StandardHead[]>(`${base}/charges/standard-heads`),
    staleTime: Infinity,
  });
}

export function useChargeHeads() {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "charge-heads"],
    queryFn: () => api.get<ChargeHead[]>(`${base}/charges/heads`),
  });
}

export function useSaveHead() {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, body }: { id?: string; body: ChargeHeadInput | ChargeHeadUpdate }) =>
      id
        ? api.patch<ChargeHeadSaved>(`${base}/charges/heads/${id}`, body)
        : api.post<ChargeHeadSaved>(`${base}/charges/heads`, body),
    onSuccess: invalidate,
  });
}

export function useChargesPreview(periodStart: string) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "charges-preview", periodStart],
    queryFn: () => api.get<ChargesPreview>(`${base}/charges/preview?period_start=${periodStart}`),
  });
}

export function useSocietySettings() {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "settings"],
    queryFn: () => api.get<SocietySettings>(`${base}/settings`),
  });
}

export function useSaveSettings() {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: SettingsUpdate) => api.patch<SocietySettings>(`${base}/settings`, body),
    onSuccess: invalidate,
  });
}

function useFlatList<T>(flatId: string, kind: string) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "flats", flatId, kind],
    queryFn: () => api.get<T[]>(`${base}/flats/${flatId}/${kind}`),
  });
}

function useFlatSave<In, Out>(flatId: string, kind: string) {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, body }: { id?: string; body: In | { end_date: string } }) =>
      id
        ? api.patch<Out>(`${base}/flats/${flatId}/${kind}/${id}`, body)
        : api.post<Out>(`${base}/flats/${flatId}/${kind}`, body),
    onSuccess: invalidate,
  });
}

export const useOverrides = (flatId: string) => useFlatList<Override>(flatId, "overrides");
export const useSaveOverride = (flatId: string) => useFlatSave<OverrideInput, Override>(flatId, "overrides");
export const useParking = (flatId: string) => useFlatList<Parking>(flatId, "parking");
export const useSaveParking = (flatId: string) => useFlatSave<ParkingInput, Parking>(flatId, "parking");
export const usePropertyTax = (flatId: string) => useFlatList<PropertyTax>(flatId, "property-tax");
export const useAddPropertyTax = (flatId: string) => useFlatSave<PropertyTaxInput, PropertyTax>(flatId, "property-tax");

export function useTaxTemplate() {
  const { api, base } = useBase();
  return useMutation({
    mutationFn: async () => {
      const blob = await api.download(`${base}/property-tax/template`);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "societyiq-property-tax.xlsx";
      link.click();
      URL.revokeObjectURL(url);
    },
  });
}

export function useUploadTax() {
  const { api, base } = useBase();
  return useMutation({
    mutationFn: (file: File) => api.upload<TaxImport>(`${base}/property-tax/imports`, file, file.name),
  });
}

export function useConfirmTax() {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (jobId: string) => api.post<TaxImport>(`${base}/property-tax/imports/${jobId}/confirm`),
    onSuccess: invalidate,
  });
}
