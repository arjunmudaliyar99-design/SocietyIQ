// Complaints list for the committee (docs/02 §8): filter by status, raise on behalf of a flat.
import { Plus } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Button,
  COMPLAINT_STATUSES,
  ComplaintRow,
  EmptyState,
  ErrorText,
  LoadingBlock,
  messageKeyOf,
  useComplaints,
  useTranslation,
  type ComplaintStatus,
} from "@societyiq/shared";

export function ComplaintsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [status, setStatus] = useState<ComplaintStatus | undefined>("open");
  const complaints = useComplaints(status);
  const filters: { value: ComplaintStatus | undefined; label: string }[] = [
    ...COMPLAINT_STATUSES.map((s) => ({ value: s, label: t(`complaints.status.${s}`) })),
    { value: undefined, label: t("complaints.all") },
  ];

  return (
    <>
      <h1 className="mb-6 text-title font-bold">{t("complaints.title")}</h1>
      <div className="mb-6">
        <Button icon={<Plus size={22} />} onClick={() => navigate("/complaints/new")}>
          {t("complaints.raiseForFlat")}
        </Button>
      </div>
      <div role="group" aria-label={t("complaints.changeStatus")} className="mb-6 flex flex-wrap gap-2">
        {filters.map((f) => (
          <button
            key={f.label}
            type="button"
            aria-pressed={status === f.value}
            onClick={() => setStatus(f.value)}
            className={`min-h-[48px] rounded-full border-2 px-4 text-body font-semibold focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink ${
              status === f.value ? "border-teal bg-teal text-white" : "border-line bg-surface text-ink"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {complaints.isPending ? <LoadingBlock /> : null}
      {complaints.isError ? <ErrorText>{t(messageKeyOf(complaints.error))}</ErrorText> : null}
      {complaints.data?.length === 0 ? (
        <EmptyState message={status ? t("complaints.emptyFiltered") : t("complaints.empty")} />
      ) : null}
      {complaints.data?.length ? (
        <ul className="flex max-w-3xl flex-col gap-3">
          {complaints.data.map((c) => (
            <ComplaintRow key={c.id} complaint={c} onOpen={() => navigate(`/complaints/${c.id}`)} />
          ))}
        </ul>
      ) : null}
    </>
  );
}
