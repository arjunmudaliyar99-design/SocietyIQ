// TanStack Query hooks for complaints (docs/02 §8). Shared: the committee manages, residents
// raise and follow; the backend decides what each person may see.
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Schemas } from "../api/client";
import { useAuth } from "../auth/auth-context";
import { useCurrentSociety } from "../auth/society-context";

export type Complaint = Schemas["ComplaintOut"];
export type ComplaintDetail = Schemas["ComplaintDetailOut"];
export type ComplaintStatus = Complaint["status"];
export type ComplaintCategory = Complaint["category"];
export type ComplaintLocation = Complaint["location"];
export type NewComplaint = Schemas["ComplaintIn"];

function useBase() {
  const { api } = useAuth();
  const current = useCurrentSociety();
  if (!current) throw new Error("Complaint pages need a selected society");
  const societyId = current.society.id;
  return { api, societyId, base: `/societies/${societyId}/complaints` };
}

function useInvalidate() {
  const client = useQueryClient();
  const { societyId } = useBase();
  return () => client.invalidateQueries({ queryKey: ["societies", societyId, "complaints"] });
}

export function useComplaints(status?: ComplaintStatus) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "complaints", "list", status ?? "all"],
    queryFn: () => api.get<Complaint[]>(status ? `${base}?status=${status}` : base),
  });
}

export function useComplaint(id: string) {
  const { api, societyId, base } = useBase();
  return useQuery({
    queryKey: ["societies", societyId, "complaints", id],
    queryFn: () => api.get<ComplaintDetail>(`${base}/${id}`),
  });
}

/** Creates the complaint, then attaches the photo if one was chosen. */
export function useRaiseComplaint() {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async ({ complaint, photo }: { complaint: NewComplaint; photo?: File | null }) => {
      const created = await api.post<ComplaintDetail>(base, complaint);
      if (!photo) return created;
      return api.upload<ComplaintDetail>(`${base}/${created.id}/photos`, photo, photo.name || "photo.jpg");
    },
    onSuccess: invalidate,
  });
}

export function useAddComplaintUpdate(id: string) {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: Schemas["ComplaintUpdateIn"]) => api.post<ComplaintDetail>(`${base}/${id}/updates`, body),
    onSuccess: invalidate,
  });
}

export function useAssignComplaint(id: string) {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (assignedTo: string) =>
      api.patch<ComplaintDetail>(`${base}/${id}/assignee`, { assigned_to_text: assignedTo }),
    onSuccess: invalidate,
  });
}

export function useComplaintFeedback(id: string) {
  const { api, base } = useBase();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (feedback: "fixed" | "not_fixed") =>
      api.post<ComplaintDetail>(`${base}/${id}/feedback`, { feedback }),
    onSuccess: invalidate,
  });
}

/** Photos need the sign-in header, so they are fetched as blobs and shown via object URLs. */
export function useComplaintPhoto(complaintId: string, photoId: string): string | null {
  const { api, societyId, base } = useBase();
  const blob = useQuery({
    queryKey: ["societies", societyId, "complaints", complaintId, "photo", photoId],
    queryFn: () => api.download(`${base}/${complaintId}/photos/${photoId}`),
    staleTime: Infinity,
  });
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!blob.data) return;
    const next = URL.createObjectURL(blob.data);
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [blob.data]);
  return url;
}
