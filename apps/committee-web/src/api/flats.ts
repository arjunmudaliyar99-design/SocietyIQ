// TanStack Query hooks for wings, flats, members and the Excel import (docs/02 §4).
import { useAuth, useCurrentSociety, useMutation, useQuery, useQueryClient, type Schemas } from "@societyiq/shared";

export type Wing = Schemas["WingOut"];
export type FlatSummary = Schemas["FlatSummaryOut"];
export type FlatDetail = Schemas["FlatDetailOut"];
export type FlatInput = Schemas["FlatIn"];
export type FlatUpdate = Schemas["FlatUpdate"];
export type Member = Schemas["MemberOut"];
export type MemberInput = Schemas["MemberIn"];
export type MemberUpdate = Schemas["MemberUpdate"];
export type ImportJob = Schemas["ImportJobOut"];
export type ImportRow = Schemas["ImportRowOut"];

/** docs/02 §2: admin, treasurer and consultant manage; committee and auditor view. */
export const MANAGE_ROLES = ["admin", "treasurer", "consultant"];

export function useSocietyId(): string {
  const current = useCurrentSociety();
  if (!current) throw new Error("Society pages need a selected society");
  return current.society.id;
}

export function useCanManageFlats(): boolean {
  const current = useCurrentSociety();
  return Boolean(current?.society.roles.some((r) => MANAGE_ROLES.includes(r)));
}

const keys = {
  wings: (s: string) => ["societies", s, "wings"] as const,
  flats: (s: string) => ["societies", s, "flats"] as const,
  flat: (s: string, f: string) => ["societies", s, "flats", f] as const,
};

export function useWings() {
  const { api } = useAuth();
  const societyId = useSocietyId();
  return useQuery({
    queryKey: keys.wings(societyId),
    queryFn: () => api.get<Wing[]>(`/societies/${societyId}/wings`),
  });
}

function useInvalidateFlats() {
  const client = useQueryClient();
  const societyId = useSocietyId();
  return () => client.invalidateQueries({ queryKey: ["societies", societyId] });
}

export function useSaveWing() {
  const { api } = useAuth();
  const societyId = useSocietyId();
  const invalidate = useInvalidateFlats();
  return useMutation({
    mutationFn: ({ id, ...body }: { id?: string; name?: string; has_lift?: boolean }) =>
      id
        ? api.patch<Wing>(`/societies/${societyId}/wings/${id}`, body)
        : api.post<Wing>(`/societies/${societyId}/wings`, body),
    onSuccess: invalidate,
  });
}

export function useFlats() {
  const { api } = useAuth();
  const societyId = useSocietyId();
  return useQuery({
    queryKey: keys.flats(societyId),
    queryFn: () => api.get<FlatSummary[]>(`/societies/${societyId}/flats`),
  });
}

export function useFlat(flatId: string) {
  const { api } = useAuth();
  const societyId = useSocietyId();
  return useQuery({
    queryKey: keys.flat(societyId, flatId),
    queryFn: () => api.get<FlatDetail>(`/societies/${societyId}/flats/${flatId}`),
  });
}

export function useCreateFlat() {
  const { api } = useAuth();
  const societyId = useSocietyId();
  const invalidate = useInvalidateFlats();
  return useMutation({
    mutationFn: (body: FlatInput) => api.post<Schemas["FlatOut"]>(`/societies/${societyId}/flats`, body),
    onSuccess: invalidate,
  });
}

export function useUpdateFlat(flatId: string) {
  const { api } = useAuth();
  const societyId = useSocietyId();
  const invalidate = useInvalidateFlats();
  return useMutation({
    mutationFn: (body: FlatUpdate) => api.patch<Schemas["FlatOut"]>(`/societies/${societyId}/flats/${flatId}`, body),
    onSuccess: invalidate,
  });
}

export function useSaveMember(flatId: string) {
  const { api } = useAuth();
  const societyId = useSocietyId();
  const invalidate = useInvalidateFlats();
  return useMutation({
    mutationFn: ({ id, body }: { id?: string; body: MemberInput | MemberUpdate }) =>
      id
        ? api.patch<Member>(`/societies/${societyId}/flats/${flatId}/members/${id}`, body)
        : api.post<Member>(`/societies/${societyId}/flats/${flatId}/members`, body),
    onSuccess: invalidate,
  });
}

export function useDownloadTemplate() {
  const { api } = useAuth();
  const societyId = useSocietyId();
  return useMutation({
    mutationFn: async () => {
      const blob = await api.download(`/societies/${societyId}/imports/template`);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "societyiq-flats-template.xlsx";
      link.click();
      URL.revokeObjectURL(url);
    },
  });
}

export function useUploadImport() {
  const { api } = useAuth();
  const societyId = useSocietyId();
  return useMutation({
    mutationFn: (file: File) => api.upload<ImportJob>(`/societies/${societyId}/imports`, file, file.name),
  });
}

export function useConfirmImport() {
  const { api } = useAuth();
  const societyId = useSocietyId();
  const invalidate = useInvalidateFlats();
  return useMutation({
    mutationFn: (jobId: string) => api.post<ImportJob>(`/societies/${societyId}/imports/${jobId}/confirm`),
    onSuccess: invalidate,
  });
}
