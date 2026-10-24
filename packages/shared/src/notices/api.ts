// TanStack Query hooks for notices (docs/02 §9). Shared: the committee drafts and publishes,
// residents read; the backend decides who sees which notice.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Schemas } from "../api/client";
import { useAuth } from "../auth/auth-context";
import { useCurrentSociety } from "../auth/society-context";

export type Notice = Schemas["NoticeOut"];
export type NoticeDetail = Schemas["NoticeDetailOut"];
export type NoticeStatus = Notice["status"];
export type NoticeAudience = Notice["audience"];
export type NoticeLanguage = Notice["language"];
export type NewNotice = Schemas["NoticeIn"];
export type NoticeChanges = Schemas["NoticeUpdate"];

function useBase() {
  const { api } = useAuth();
  const current = useCurrentSociety();
  if (!current) throw new Error("Notice pages need a selected society");
  const societyId = current.society.id;
  return { api, societyId, base: `/societies/${societyId}/notices` };
}

function useInvalidate() {
  const client = useQueryClient();
  const { societyId } = useBase();
  return () => client.invalidateQueries({ queryKey: ["societies", societyId, "notices"] });
}

export function useNotices(status?: NoticeStatus) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "notices", "list", status ?? "all"],
    queryFn: () => api.get<Notice[]>(status ? `${base}?status=${status}` : base),
  });
}

export function useNotice(id: string) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "notices", id],
    queryFn: () => api.get<NoticeDetail>(`${base}/${id}`),
  });
}

export function useNoticeOptions() {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "notices", "options"],
    queryFn: () => api.get<Schemas["NoticeOptionsOut"]>(`${base}/options`),
    staleTime: Infinity,
  });
}

export function useCreateNotice() {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (notice: NewNotice) => api.post<NoticeDetail>(base, notice),
    onSuccess: invalidate,
  });
}

export function useUpdateNotice(id: string) {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (changes: NoticeChanges) => api.patch<NoticeDetail>(`${base}/${id}`, changes),
    onSuccess: invalidate,
  });
}

export function useNoticeAction(id: string) {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (action: "publish" | "archive") => api.post<NoticeDetail>(`${base}/${id}/${action}`),
    onSuccess: invalidate,
  });
}

export function useAiTranslate(id: string) {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (languages: NoticeLanguage[]) =>
      api.post<NoticeDetail>(`${base}/${id}/ai-translate`, { languages }),
    onSuccess: invalidate,
  });
}

/** "Help me write": returns text for a person to edit; nothing is saved or sent. */
export function useAiDraft() {
  const { api, base } = useBase();
  return useMutation({
    mutationFn: (input: { notes: string; language: NoticeLanguage }) =>
      api.post<Schemas["AiTextOut"]>(`${base}/ai-draft`, input),
  });
}

export function useMarkNoticeRead(id: string) {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: () => api.post<{ read: boolean }>(`${base}/${id}/read`),
    onSuccess: invalidate,
  });
}

/** The reader's language when a reviewed translation exists, else the original. */
export function noticeTextFor(notice: NoticeDetail, language: string): { title: string; body: string } {
  const t = notice.translations?.[language as NoticeLanguage];
  if (language !== notice.language && t?.reviewed) return { title: t.title, body: t.body };
  return { title: notice.title, body: notice.body };
}
