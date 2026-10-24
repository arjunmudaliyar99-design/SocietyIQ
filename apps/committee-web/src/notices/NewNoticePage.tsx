// Write a notice (docs/02 §9). "Help me write" turns rough notes into a draft that the person
// edits; it is saved only as a draft and never sent until someone presses Publish.
import { ArrowLeft, Save, Sparkles } from "lucide-react";
import { useId, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Button,
  Card,
  ErrorText,
  messageKeyOf,
  useAiDraft,
  useCreateNotice,
  useNoticeOptions,
  useSettings,
  useTranslation,
  type NoticeLanguage,
} from "@societyiq/shared";

import { NoticeForm } from "./NoticeForm";
import { isComplete, type NoticeValues } from "./model";

function HelpMeWrite({ language, onDraft }: { language: NoticeLanguage; onDraft: (title: string, body: string) => void }) {
  const { t } = useTranslation();
  const draft = useAiDraft();
  const notesId = useId();
  const [notes, setNotes] = useState("");
  return (
    <Card className="flex flex-col gap-3">
      <h2 className="text-section font-bold">{t("notices.ai.title")}</h2>
      <p className="text-body">{t("notices.ai.explain")}</p>
      <label htmlFor={notesId} className="text-body font-semibold">
        {t("notices.ai.notes")}
      </label>
      <textarea
        id={notesId}
        rows={4}
        maxLength={4000}
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        className="rounded-lg border-2 border-line bg-surface p-3 text-body focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
      />
      <div>
        <Button
          variant="secondary"
          icon={<Sparkles size={22} />}
          disabled={notes.trim().length < 3 || draft.isPending}
          onClick={() => draft.mutate({ notes: notes.trim(), language }, { onSuccess: (d) => onDraft(d.title, d.body) })}
        >
          {draft.isPending ? t("notices.ai.working") : t("notices.ai.button")}
        </Button>
      </div>
      {draft.isError ? <ErrorText>{t(messageKeyOf(draft.error))}</ErrorText> : null}
    </Card>
  );
}

export function NewNoticePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { language } = useSettings();
  const options = useNoticeOptions();
  const create = useCreateNotice();
  const [values, setValues] = useState<NoticeValues>({
    title: "",
    body: "",
    language: language as NoticeLanguage,
    audience: "all",
    wingId: "",
  });
  const [aiAssisted, setAiAssisted] = useState(false);

  function save() {
    create.mutate(
      {
        title: values.title.trim(),
        body: values.body.trim(),
        language: values.language,
        audience: values.audience,
        audience_wing_id: values.audience === "wing" ? values.wingId : null,
        ai_assisted: aiAssisted,
      },
      { onSuccess: (n) => navigate(`/notices/${n.id}`) },
    );
  }

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <div>
        <Button variant="secondary" icon={<ArrowLeft size={22} />} onClick={() => navigate("/notices")}>
          {t("notices.back")}
        </Button>
      </div>
      <h1 className="text-title font-bold">{t("notices.write")}</h1>
      {options.data?.ai_available ? (
        <HelpMeWrite
          language={values.language}
          onDraft={(title, body) => {
            setValues({ ...values, title, body });
            setAiAssisted(true);
          }}
        />
      ) : null}
      {aiAssisted ? (
        <Card role="status" className="border-2 border-teal">
          <p className="text-body font-semibold">{t("notices.ai.checkDraft")}</p>
        </Card>
      ) : null}
      <NoticeForm values={values} onChange={setValues} />
      <div>
        <Button icon={<Save size={22} />} disabled={!isComplete(values) || create.isPending} onClick={save}>
          {t("notices.saveDraft")}
        </Button>
      </div>
      {create.isError ? <ErrorText>{t(messageKeyOf(create.error))}</ErrorText> : null}
    </div>
  );
}
