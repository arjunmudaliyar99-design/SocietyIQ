// TanStack Query hooks for the M2 endpoints, shared by both apps (CLAUDE.md §7).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../auth/auth-context";
import type { Schemas } from "./client";

export type Me = Schemas["MeOut"];
export type MySociety = Schemas["MySocietyOut"];
export type Society = Schemas["SocietyOut"];
export type Membership = Schemas["MembershipOut"];
export type InviteResult = Schemas["InviteOut"];
export type SocietyCreateInput = Schemas["SocietyCreateIn"];
export type SocietyCreated = Schemas["SocietyCreatedOut"];
export type InviteInput = Schemas["InviteIn"];
export type PreferencesInput = Schemas["PreferencesIn"];

export const queryKeys = {
  me: ["me"] as const,
  mySocieties: ["me", "societies"] as const,
  society: (id: string) => ["societies", id] as const,
  memberships: (id: string) => ["societies", id, "memberships"] as const,
};

export function useMe() {
  const { api, status } = useAuth();
  return useQuery({ queryKey: queryKeys.me, queryFn: () => api.get<Me>("/me"), enabled: status === "signedIn" });
}

export function useUpdatePreferences() {
  const { api } = useAuth();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (changes: PreferencesInput) => api.patch<Me>("/me/preferences", changes),
    onSuccess: (me) => client.setQueryData(queryKeys.me, me),
  });
}

export function useGiveConsent() {
  const { api } = useAuth();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { analytics: boolean; notifications: boolean }) =>
      api.post("/me/consents", { accept_terms_and_privacy: true, ...input }),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.me }),
  });
}

export function useMySocieties() {
  const { api, status } = useAuth();
  return useQuery({
    queryKey: queryKeys.mySocieties,
    queryFn: () => api.get<MySociety[]>("/me/societies"),
    enabled: status === "signedIn",
  });
}

/** Does not refresh the society list by itself: the wizard first shows the invite links,
 * which are visible only once, then refreshes when the person moves on. */
export function useCreateSociety() {
  const { api } = useAuth();
  return useMutation({
    mutationFn: (input: SocietyCreateInput) => api.post<SocietyCreated>("/societies", input),
  });
}

export function useSociety(id: string) {
  const { api } = useAuth();
  return useQuery({ queryKey: queryKeys.society(id), queryFn: () => api.get<Society>(`/societies/${id}`) });
}

export function useMemberships(societyId: string) {
  const { api } = useAuth();
  return useQuery({
    queryKey: queryKeys.memberships(societyId),
    queryFn: () => api.get<Membership[]>(`/societies/${societyId}/memberships`),
  });
}

export function useInvite(societyId: string) {
  const { api } = useAuth();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: InviteInput) => api.post<InviteResult>(`/societies/${societyId}/invites`, input),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.memberships(societyId) }),
  });
}

export function useAcceptInvite() {
  const { api } = useAuth();
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ societyId, token }: { societyId: string; token: string }) =>
      api.post<Membership>(`/societies/${societyId}/invites/accept`, { token }),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.mySocieties }),
  });
}
