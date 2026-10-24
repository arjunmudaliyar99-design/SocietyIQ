// TanStack Query hooks for the committee home and the compliance tracker (docs/02 §10, §13).
import {
  useAuth,
  useCurrentSociety,
  useMutation,
  useQuery,
  useQueryClient,
  type Schemas,
} from "@societyiq/shared";

import { useSocietyId } from "./flats";

export type Home = Schemas["HomeOut"];
export type Item = Schemas["ItemOut"];
export type ItemDetail = Schemas["ItemDetailOut"];
export type ItemIn = Schemas["ItemIn"];
export type ItemUpdate = Schemas["ItemUpdate"];
export type Vendor = Schemas["VendorOut"];
export type VendorIn = Schemas["VendorIn"];
export type ItemType = Item["item_type"];

export const ITEM_TYPES: ItemType[] = [
  "fire_audit",
  "structural_audit",
  "lift_amc",
  "pump_amc",
  "generator_service",
  "tank_cleaning",
  "cctv_amc",
  "insurance",
  "pest_control",
  "other",
];

const MANAGE_ROLES = ["admin", "treasurer", "committee", "consultant"];

export function useCanManageCompliance(): boolean {
  const current = useCurrentSociety();
  return Boolean(current?.society.roles.some((r) => MANAGE_ROLES.includes(r)));
}

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

export function useHome() {
  const { api, societyId, base } = useBase();
  return useQuery({ queryKey: ["societies", societyId, "home"], queryFn: () => api.get<Home>(`${base}/home`) });
}

export function useComplianceItems() {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "compliance"],
    queryFn: () => api.get<Item[]>(`${base}/compliance/items`),
  });
}

export function useComplianceItem(itemId: string) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "compliance", itemId],
    queryFn: () => api.get<ItemDetail>(`${base}/compliance/items/${itemId}`),
    enabled: Boolean(itemId),
  });
}

export function useSaveItem() {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, ...body }: (ItemIn | ItemUpdate) & { id?: string }) =>
      id
        ? api.patch<ItemDetail>(`${base}/compliance/items/${id}`, body)
        : api.post<ItemDetail>(`${base}/compliance/items`, body),
    onSuccess: invalidate,
  });
}

export function useMarkDone(itemId: string) {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: { done_on: string; notes?: string | null }) =>
      api.post<ItemDetail>(`${base}/compliance/items/${itemId}/done`, body),
    onSuccess: invalidate,
  });
}

export function useVendors() {
  const { api, societyId, base } = useBase();
  return useQuery({ queryKey: ["societies", societyId, "vendors"], queryFn: () => api.get<Vendor[]>(`${base}/vendors`) });
}

export function useSaveVendor() {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<VendorIn> & { id?: string }) =>
      id ? api.patch<Vendor>(`${base}/vendors/${id}`, body) : api.post<Vendor>(`${base}/vendors`, body),
    onSuccess: invalidate,
  });
}
