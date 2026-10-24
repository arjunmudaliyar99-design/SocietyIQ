// Resident complaint screens (docs/02 §8, §11): report a problem, my complaints, and one
// complaint with the committee's updates and the Fixed / Not fixed answer.
import { ArrowLeft, CircleCheck, CircleX, MessageSquareWarning } from "lucide-react";
import type { ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  BigButton,
  Button,
  Card,
  ComplaintForm,
  ComplaintHistory,
  ComplaintPhotos,
  ComplaintRow,
  ComplaintStatusPill,
  EmptyState,
  ErrorText,
  categoryIcon,
  messageKeyOf,
  useComplaint,
  useComplaintFeedback,
  useComplaints,
  useTranslation,
} from "@societyiq/shared";

function Screen({ title, back, children }: { title: ReactNode; back: string; children: ReactNode }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <div className="flex flex-col gap-4">
      <div>
        <Button variant="secondary" icon={<ArrowLeft size={22} />} onClick={() => navigate(back)}>
          {t("back")}
        </Button>
      </div>
      <h1 className="text-title font-bold">{title}</h1>
      {children}
    </div>
  );
}

export function ReportPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <Screen title={t("complaints.report")} back="/">
      <ComplaintForm onDone={(c) => navigate(`/complaints/${c.id}?sent=1`)} />
    </Screen>
  );
}

export function MyComplaintsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const complaints = useComplaints();
  return (
    <Screen title={t("complaints.myTitle")} back="/menu">
      <BigButton icon={<MessageSquareWarning size={26} />} onClick={() => navigate("/report")}>
        {t("complaints.report")}
      </BigButton>
      {complaints.isPending ? <p role="status">{t("loading")}</p> : null}
      {complaints.isError ? <ErrorText>{t(messageKeyOf(complaints.error))}</ErrorText> : null}
      {complaints.data?.length === 0 ? <EmptyState message={t("complaints.empty")} /> : null}
      {complaints.data?.length ? (
        <ul className="flex flex-col gap-3">
          {complaints.data.map((c) => (
            <ComplaintRow key={c.id} complaint={c} onOpen={() => navigate(`/complaints/${c.id}`)} />
          ))}
        </ul>
      ) : null}
    </Screen>
  );
}

export function ComplaintPage() {
  const { complaintId = "" } = useParams();
  const { t } = useTranslation();
  const complaint = useComplaint(complaintId);
  const feedback = useComplaintFeedback(complaintId);
  const justSent = new URLSearchParams(window.location.search).get("sent") === "1";

  if (complaint.isPending) return <p role="status">{t("loading")}</p>;
  if (complaint.isError) return <ErrorText>{t(messageKeyOf(complaint.error))}</ErrorText>;
  const c = complaint.data;

  return (
    <Screen
      back="/complaints"
      title={
        <span className="flex flex-wrap items-center gap-3">
          <span aria-hidden="true" className="text-teal">
            {categoryIcon(c.category)}
          </span>
          {t(`complaints.category.${c.category}`)}
        </span>
      }
    >
      {justSent ? (
        <Card role="status" className="border-2 border-green">
          <p className="text-body font-semibold">{t("complaints.sent")}</p>
        </Card>
      ) : null}
      <div>
        <ComplaintStatusPill status={c.status} />
      </div>
      <p className="text-body">
        {c.location === "common_area" ? t("complaints.location.common_area") : (c.flat_label ?? "")}
      </p>
      {c.description ? <p className="whitespace-pre-line text-body">{c.description}</p> : null}
      <ComplaintPhotos complaint={c} />

      {c.status === "resolved" ? (
        <Card className="flex flex-col gap-3 border-2 border-teal">
          <p className="text-section font-bold">{t("complaints.askFixed")}</p>
          <BigButton
            icon={<CircleCheck size={26} />}
            disabled={feedback.isPending}
            onClick={() => feedback.mutate("fixed")}
          >
            {t("complaints.fixedButton")}
          </BigButton>
          <BigButton
            variant="secondary"
            icon={<CircleX size={26} />}
            disabled={feedback.isPending}
            onClick={() => feedback.mutate("not_fixed")}
          >
            {t("complaints.notFixedButton")}
          </BigButton>
          {feedback.isError ? <ErrorText>{t(messageKeyOf(feedback.error))}</ErrorText> : null}
        </Card>
      ) : null}

      <ComplaintHistory complaint={c} />
    </Screen>
  );
}
