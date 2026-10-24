// Notice pieces used by both apps (docs/02 §9, §11): list row with unread in bold, status pill.
import { Archive, CircleCheck, Megaphone, PencilLine } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { useSettings } from "../settings-context";
import { formatDate } from "../utils/date";
import type { Notice, NoticeStatus } from "./api";

// Word + icon + colour, never colour alone (docs/03 §3).
const STATUS_STYLE: Record<NoticeStatus, { className: string; icon: ReactNode }> = {
  draft: { className: "text-ink border-muted", icon: <PencilLine size={18} /> },
  published: { className: "text-green border-green", icon: <CircleCheck size={18} /> },
  archived: { className: "text-muted border-line", icon: <Archive size={18} /> },
};

export function NoticeStatusPill({ status }: { status: NoticeStatus }) {
  const { t } = useTranslation();
  const style = STATUS_STYLE[status];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border-2 bg-surface px-3 py-1 text-small font-semibold ${style.className}`}
    >
      <span aria-hidden="true">{style.icon}</span>
      {t(`notices.status.${status}`)}
    </span>
  );
}

export interface NoticeRowProps {
  notice: Notice;
  onOpen: () => void;
  /** Residents see unread notices in bold; the committee sees the status instead. */
  showStatus?: boolean;
}

export function NoticeRow({ notice, onOpen, showStatus = false }: NoticeRowProps) {
  const { t } = useTranslation();
  const { language } = useSettings();
  const unread = !showStatus && !notice.is_read;
  const when = (notice.published_at ?? notice.updated_at).slice(0, 10);
  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full items-center gap-3 rounded-card border border-line bg-surface p-4 text-left shadow-card transition hover:border-teal hover:shadow-raised focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
      >
        <span aria-hidden="true" className="text-teal">
          <Megaphone size={26} />
        </span>
        <span className="flex flex-1 flex-col">
          <span className={`text-body ${unread ? "font-bold" : "font-normal"}`}>
            {notice.title}
            {unread ? <span className="sr-only"> ({t("notices.unread")})</span> : null}
          </span>
          <span className="text-small text-muted">{formatDate(when, language)}</span>
        </span>
        {showStatus ? <NoticeStatusPill status={notice.status} /> : null}
        {unread ? <span aria-hidden="true" className="h-3 w-3 rounded-full bg-teal" /> : null}
      </button>
    </li>
  );
}
