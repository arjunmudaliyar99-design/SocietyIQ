// Notices list for the committee (docs/02 §9): drafts and published notices, newest first.
import { Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";

import {
  Button,
  EmptyState,
  ErrorText,
  LoadingBlock,
  NoticeRow,
  messageKeyOf,
  useNotices,
  useTranslation,
} from "@societyiq/shared";

import { useCanDraftNotices } from "./roles";

export function NoticesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const notices = useNotices();
  const canDraft = useCanDraftNotices();

  return (
    <>
      <h1 className="mb-6 text-title font-bold">{t("notices.title")}</h1>
      {canDraft ? (
        <div className="mb-6">
          <Button icon={<Plus size={22} />} onClick={() => navigate("/notices/new")}>
            {t("notices.write")}
          </Button>
        </div>
      ) : null}
      {notices.isPending ? <LoadingBlock /> : null}
      {notices.isError ? <ErrorText>{t(messageKeyOf(notices.error))}</ErrorText> : null}
      {notices.data?.length === 0 ? (
        <EmptyState
          message={t("notices.empty")}
          actionLabel={canDraft ? t("notices.write") : undefined}
          onAction={canDraft ? () => navigate("/notices/new") : undefined}
        />
      ) : null}
      {notices.data?.length ? (
        <ul className="flex max-w-3xl flex-col gap-3">
          {notices.data.map((n) => (
            <NoticeRow key={n.id} notice={n} showStatus onOpen={() => navigate(`/notices/${n.id}`)} />
          ))}
        </ul>
      ) : null}
    </>
  );
}
