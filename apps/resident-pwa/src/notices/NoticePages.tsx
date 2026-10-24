// Resident notices (docs/02 §11): newest first, unread in bold; opening one marks it read and
// shows it in the reader's language when the committee has a checked translation.
import { ArrowLeft } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  Button,
  Card,
  EmptyState,
  ErrorText,
  LoadingBlock,
  NoticeRow,
  formatDate,
  messageKeyOf,
  noticeTextFor,
  useMarkNoticeRead,
  useNotice,
  useNotices,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

function Screen({ title, back, children }: { title: string; back: string; children: ReactNode }) {
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

export function NoticesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const notices = useNotices();
  return (
    <Screen title={t("notices.title")} back="/">
      {notices.isPending ? <LoadingBlock /> : null}
      {notices.isError ? <ErrorText>{t(messageKeyOf(notices.error))}</ErrorText> : null}
      {notices.data?.length === 0 ? <EmptyState message={t("notices.emptyResident")} /> : null}
      {notices.data?.length ? (
        <ul className="flex flex-col gap-3">
          {notices.data.map((n) => (
            <NoticeRow key={n.id} notice={n} onOpen={() => navigate(`/notices/${n.id}`)} />
          ))}
        </ul>
      ) : null}
    </Screen>
  );
}

export function NoticePage() {
  const { noticeId = "" } = useParams();
  const { t } = useTranslation();
  const { language } = useSettings();
  const notice = useNotice(noticeId);
  const markRead = useMarkNoticeRead(noticeId);
  const marked = useRef(false);
  const unread = notice.data ? !notice.data.is_read : false;

  useEffect(() => {
    if (unread && !marked.current) {
      marked.current = true;
      markRead.mutate();
    }
  }, [unread, markRead]);

  if (notice.isPending) return <LoadingBlock rows={1} />;
  if (notice.isError) return <ErrorText>{t(messageKeyOf(notice.error))}</ErrorText>;
  const n = notice.data;
  const text = noticeTextFor(n, language);

  return (
    <Screen title={text.title} back="/notices">
      {n.published_at ? <p className="text-small text-muted">{formatDate(n.published_at.slice(0, 10), language)}</p> : null}
      <Card>
        <p className="whitespace-pre-line text-body">{text.body}</p>
      </Card>
    </Screen>
  );
}
