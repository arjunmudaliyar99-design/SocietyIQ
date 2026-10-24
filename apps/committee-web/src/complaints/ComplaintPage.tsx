// One complaint for the committee (docs/02 §8): assign, post updates, move through
// Open → In progress → Resolved → Closed. Residents see updates unless marked committee-only.
import { ArrowLeft, Send, UserCheck } from "lucide-react";
import { useId, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  Button,
  Card,
  ComplaintHistory,
  ComplaintPhotos,
  ComplaintStatusPill,
  ErrorText,
  LoadingBlock,
  Field,
  SelectField,
  categoryIcon,
  messageKeyOf,
  useAddComplaintUpdate,
  useAssignComplaint,
  useComplaint,
  useTranslation,
  type ComplaintDetail,
  type ComplaintStatus,
} from "@societyiq/shared";

// Mirrors the backend's allowed moves so the list offers only what will be accepted.
const NEXT: Record<ComplaintStatus, ComplaintStatus[]> = {
  open: ["in_progress", "resolved", "closed"],
  in_progress: ["open", "resolved", "closed"],
  resolved: ["in_progress", "closed"],
  closed: ["in_progress"],
};

function AssignForm({ complaint }: { complaint: ComplaintDetail }) {
  const { t } = useTranslation();
  const assign = useAssignComplaint(complaint.id);
  const [name, setName] = useState(complaint.assigned_to_text ?? "");
  return (
    <Card className="flex flex-col gap-3">
      <Field label={t("complaints.assign")} value={name} maxLength={120} onChange={(e) => setName(e.target.value)} />
      <div>
        <Button
          variant="secondary"
          icon={<UserCheck size={22} />}
          disabled={assign.isPending || name.trim() === (complaint.assigned_to_text ?? "")}
          onClick={() => assign.mutate(name.trim())}
        >
          {t("complaints.assignSave")}
        </Button>
      </div>
      {assign.isError ? <ErrorText>{t(messageKeyOf(assign.error))}</ErrorText> : null}
    </Card>
  );
}

function UpdateForm({ complaint }: { complaint: ComplaintDetail }) {
  const { t } = useTranslation();
  const add = useAddComplaintUpdate(complaint.id);
  const messageId = useId();
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState("");
  const [internal, setInternal] = useState(false);

  function post() {
    add.mutate(
      {
        message: message.trim(),
        new_status: (status || null) as ComplaintStatus | null,
        visible_to_resident: !internal,
      },
      {
        onSuccess: () => {
          setMessage("");
          setStatus("");
          setInternal(false);
        },
      },
    );
  }

  return (
    <Card className="flex flex-col gap-4">
      <h2 className="text-section font-bold">{t("complaints.addUpdate")}</h2>
      <div className="flex flex-col gap-1">
        <label htmlFor={messageId} className="text-body font-semibold">
          {t("complaints.updateMessage")}
        </label>
        <textarea
          id={messageId}
          rows={3}
          maxLength={2000}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          className="rounded-lg border-2 border-line bg-surface p-3 text-body focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
        />
      </div>
      <SelectField
        label={t("complaints.changeStatus")}
        value={status}
        onChange={(e) => setStatus(e.target.value)}
        options={[
          { value: "", label: t("complaints.keepStatus") },
          ...NEXT[complaint.status].map((s) => ({ value: s, label: t(`complaints.status.${s}`) })),
        ]}
      />
      <label className="flex min-h-[48px] items-center gap-3 text-body">
        <input type="checkbox" className="h-6 w-6" checked={internal} onChange={(e) => setInternal(e.target.checked)} />
        {t("complaints.committeeOnlyToggle")}
      </label>
      <div>
        <Button icon={<Send size={22} />} disabled={!message.trim() || add.isPending} onClick={post}>
          {t("complaints.postUpdate")}
        </Button>
      </div>
      {add.isError ? <ErrorText>{t(messageKeyOf(add.error))}</ErrorText> : null}
    </Card>
  );
}

export function ComplaintPage() {
  const { complaintId = "" } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const complaint = useComplaint(complaintId);

  if (complaint.isPending) return <LoadingBlock />;
  if (complaint.isError) return <ErrorText>{t(messageKeyOf(complaint.error))}</ErrorText>;
  const c = complaint.data;

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <div>
        <Button variant="secondary" icon={<ArrowLeft size={22} />} onClick={() => navigate("/complaints")}>
          {t("complaints.back")}
        </Button>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <span aria-hidden="true" className="text-teal">
          {categoryIcon(c.category)}
        </span>
        <h1 className="text-title font-bold">{t(`complaints.category.${c.category}`)}</h1>
        <ComplaintStatusPill status={c.status} />
      </div>
      <p className="text-body">
        {c.flat_id && c.flat_label ? (
          <Link to={`/flats/${c.flat_id}`} className="font-semibold underline">
            {c.flat_label}
          </Link>
        ) : null}
        {c.flat_label ? " · " : ""}
        {t(`complaints.location.${c.location}`)}
        {" · "}
        {c.assigned_to_text ? t("complaints.assignedTo", { name: c.assigned_to_text }) : t("complaints.notAssigned")}
      </p>
      {c.resident_feedback ? (
        <p className="text-body font-semibold">{t(`complaints.feedback.${c.resident_feedback}`)}</p>
      ) : null}
      {c.description ? (
        <Card>
          <h2 className="mb-2 text-section font-bold">{t("complaints.description")}</h2>
          <p className="whitespace-pre-line text-body">{c.description}</p>
        </Card>
      ) : null}
      <ComplaintPhotos complaint={c} />
      {c.can_manage ? (
        <>
          <UpdateForm key={c.status} complaint={c} />
          <AssignForm key={c.assigned_to_text ?? ""} complaint={c} />
        </>
      ) : null}
      <ComplaintHistory complaint={c} />
    </div>
  );
}
