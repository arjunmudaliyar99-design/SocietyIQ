// One notice for the committee (docs/02 §9). A draft can be edited, translated and published;
// publishing emails every member with an email address. A published notice shows how many
// residents opened it and how many emails went out.
import { Archive, ArrowLeft, Languages, Mail, MessageCircle, Save, Send, Sparkles } from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  Button,
  Card,
  ConfirmDialog,
  ErrorText,
  Field,
  LANGUAGES,
  LoadingBlock,
  NoticeStatusPill,
  StatCard,
  formatDate,
  messageKeyOf,
  useAiTranslate,
  useNotice,
  useNoticeAction,
  useNoticeOptions,
  useSettings,
  useTranslation,
  useUpdateNotice,
  type NoticeDetail,
  type NoticeLanguage,
} from "@societyiq/shared";

import { NoticeForm } from "./NoticeForm";
import { isComplete, type NoticeValues } from "./model";

function EditDraft({ notice }: { notice: NoticeDetail }) {
  const { t } = useTranslation();
  const update = useUpdateNotice(notice.id);
  const [values, setValues] = useState<NoticeValues>({
    title: notice.title,
    body: notice.body,
    language: notice.language,
    audience: notice.audience,
    wingId: notice.audience_wing_id ?? "",
  });
  return (
    <Card className="flex flex-col gap-4">
      <NoticeForm values={values} onChange={setValues} />
      <div>
        <Button
          variant="secondary"
          icon={<Save size={22} />}
          disabled={!isComplete(values) || update.isPending}
          onClick={() =>
            update.mutate({
              title: values.title.trim(),
              body: values.body.trim(),
              language: values.language,
              audience: values.audience,
              audience_wing_id: values.audience === "wing" ? values.wingId : null,
            })
          }
        >
          {t("notices.saveChanges")}
        </Button>
      </div>
      {update.isSuccess ? <p role="status" className="text-body">{t("notices.saved")}</p> : null}
      {update.isError ? <ErrorText>{t(messageKeyOf(update.error))}</ErrorText> : null}
    </Card>
  );
}

function TranslationEditor({ notice, lang, editable }: { notice: NoticeDetail; lang: NoticeLanguage; editable: boolean }) {
  const { t } = useTranslation();
  const update = useUpdateNotice(notice.id);
  const current = notice.translations?.[lang];
  const [open, setOpen] = useState(Boolean(current));
  const [title, setTitle] = useState(current?.title ?? "");
  const [body, setBody] = useState(current?.body ?? "");
  const name = LANGUAGES.find((l) => l.code === lang)?.nativeName ?? lang;

  if (!editable) {
    if (!current) return null;
    return (
      <div className="border-l-4 border-teal pl-3">
        <p className="text-small font-semibold text-muted">{name}</p>
        <p className="text-body font-semibold">{current.title}</p>
        <p className="whitespace-pre-line text-body">{current.body}</p>
      </div>
    );
  }
  if (!open) {
    return (
      <div>
        <Button variant="secondary" onClick={() => setOpen(true)}>
          {t("notices.translations.add", { language: name })}
        </Button>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-3 border-l-4 border-teal pl-3">
      <p className="text-body font-semibold">
        {name}
        {current && !current.reviewed ? ` · ${t("notices.translations.needsCheck")}` : ""}
        {current?.reviewed ? ` · ${t("notices.translations.checked")}` : ""}
      </p>
      <Field label={t("notices.form.title")} value={title} onChange={(e) => setTitle(e.target.value)} />
      <label className="flex flex-col gap-1 text-body font-semibold">
        {t("notices.form.body")}
        <textarea
          rows={5}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          className="rounded-lg border-2 border-line bg-surface p-3 font-normal focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
        />
      </label>
      <div className="flex flex-wrap gap-3">
        <Button
          variant="secondary"
          disabled={!title.trim() || !body.trim() || update.isPending}
          onClick={() =>
            update.mutate({ translations: { [lang]: { title: title.trim(), body: body.trim(), reviewed: true } } })
          }
        >
          {t("notices.translations.saveChecked")}
        </Button>
        {current ? (
          <Button variant="secondary" disabled={update.isPending} onClick={() => update.mutate({ translations: { [lang]: null } })}>
            {t("notices.translations.remove")}
          </Button>
        ) : null}
      </div>
      {update.isError ? <ErrorText>{t(messageKeyOf(update.error))}</ErrorText> : null}
    </div>
  );
}

function Translations({ notice, aiAvailable }: { notice: NoticeDetail; aiAvailable: boolean }) {
  const { t } = useTranslation();
  const translate = useAiTranslate(notice.id);
  const editable = notice.can_edit;
  const others = LANGUAGES.map((l) => l.code).filter((c) => c !== notice.language) as NoticeLanguage[];
  const missing = others.filter((c) => !notice.translations?.[c]);
  if (!editable && Object.keys(notice.translations ?? {}).length === 0) return null;
  return (
    <Card className="flex flex-col gap-4">
      <h2 className="flex items-center gap-2 text-section font-bold">
        <Languages size={24} aria-hidden="true" />
        {t("notices.translations.title")}
      </h2>
      {editable ? <p className="text-body">{t("notices.translations.explain")}</p> : null}
      {editable && aiAvailable && missing.length ? (
        <div>
          <Button variant="secondary" icon={<Sparkles size={22} />} disabled={translate.isPending} onClick={() => translate.mutate(missing)}>
            {translate.isPending ? t("notices.ai.working") : t("notices.translations.ai")}
          </Button>
        </div>
      ) : null}
      {translate.isError ? <ErrorText>{t(messageKeyOf(translate.error))}</ErrorText> : null}
      {others.map((lang) => (
        // Re-mount when the stored translation changes so the fields show it.
        <TranslationEditor
          key={`${lang}-${notice.translations?.[lang]?.title ?? ""}-${String(notice.translations?.[lang]?.reviewed)}`}
          notice={notice}
          lang={lang}
          editable={editable}
        />
      ))}
    </Card>
  );
}

function Channels() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-wrap gap-3 text-body">
      <span className="inline-flex items-center gap-2 rounded-full border-2 border-green px-3 py-1 font-semibold text-green">
        <Mail size={18} aria-hidden="true" /> {t("notices.channels.email")}
      </span>
      <span className="inline-flex items-center gap-2 rounded-full border-2 border-line px-3 py-1 font-semibold text-muted">
        <MessageCircle size={18} aria-hidden="true" /> {t("notices.channels.whatsapp")} · {t("comingSoon")}
      </span>
    </div>
  );
}

export function NoticePage() {
  const { noticeId = "" } = useParams();
  const { t } = useTranslation();
  const { language } = useSettings();
  const navigate = useNavigate();
  const notice = useNotice(noticeId);
  const options = useNoticeOptions();
  const action = useNoticeAction(noticeId);
  const [confirming, setConfirming] = useState<"publish" | "archive" | null>(null);

  if (notice.isPending) return <LoadingBlock />;
  if (notice.isError) return <ErrorText>{t(messageKeyOf(notice.error))}</ErrorText>;
  const n = notice.data;
  const recipients = n.recipient_count ?? 0;

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <div>
        <Button variant="secondary" icon={<ArrowLeft size={22} />} onClick={() => navigate("/notices")}>
          {t("notices.back")}
        </Button>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-title font-bold">{n.title}</h1>
        <NoticeStatusPill status={n.status} />
      </div>
      <p className="text-body">
        {t(`notices.audience.${n.audience}`)}
        {n.published_at ? ` · ${formatDate(n.published_at.slice(0, 10), language)}` : ""}
        {n.ai_assisted ? ` · ${t("notices.ai.assisted")}` : ""}
      </p>

      {n.status !== "draft" ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <StatCard label={t("notices.readCount")} value={String(n.read_count ?? 0)} />
            <StatCard label={t("notices.emailsSent")} value={String(n.emails_sent ?? 0)} />
          </div>
          {n.emails_failed ? <ErrorText>{t("notices.emailsFailed", { count: n.emails_failed })}</ErrorText> : null}
          <Card>
            <p className="whitespace-pre-line text-body">{n.body}</p>
          </Card>
        </>
      ) : null}

      {n.can_edit ? <EditDraft key={n.updated_at} notice={n} /> : null}
      <Translations notice={n} aiAvailable={Boolean(options.data?.ai_available)} />
      <Channels />

      <div className="flex flex-wrap gap-3">
        {n.can_publish ? (
          <Button icon={<Send size={22} />} disabled={action.isPending} onClick={() => setConfirming("publish")}>
            {t("notices.publish")}
          </Button>
        ) : null}
        {n.status === "draft" && n.can_edit ? (
          <Button variant="secondary" icon={<Archive size={22} />} disabled={action.isPending} onClick={() => setConfirming("archive")}>
            {t("notices.discard")}
          </Button>
        ) : null}
      </div>
      {!n.can_publish && n.status === "draft" ? <p className="text-body">{t("notices.adminPublishes")}</p> : null}
      {action.isError ? <ErrorText>{t(messageKeyOf(action.error))}</ErrorText> : null}

      <ConfirmDialog
        open={confirming === "publish"}
        question={t("notices.publishQuestion", { count: recipients })}
        confirmLabel={t("notices.publishYes")}
        onConfirm={() => {
          setConfirming(null);
          action.mutate("publish");
        }}
        onCancel={() => setConfirming(null)}
      />
      <ConfirmDialog
        open={confirming === "archive"}
        question={t("notices.discardQuestion")}
        confirmLabel={t("notices.discard")}
        danger
        onConfirm={() => {
          setConfirming(null);
          action.mutate("archive", { onSuccess: () => navigate("/notices") });
        }}
        onCancel={() => setConfirming(null)}
      />
    </div>
  );
}
