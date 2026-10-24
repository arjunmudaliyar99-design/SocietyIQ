// The notice fields (docs/02 §9): title, message, language, audience. Used for new notices and
// for editing a draft.
import { useId } from "react";

import { Field, LANGUAGES, SelectField, useTranslation, type NoticeAudience, type NoticeLanguage } from "@societyiq/shared";

import { useWings } from "../api/flats";
import { AUDIENCES, type NoticeValues } from "./model";


export function NoticeForm({ values, onChange }: { values: NoticeValues; onChange: (v: NoticeValues) => void }) {
  const { t } = useTranslation();
  const wings = useWings();
  const bodyId = useId();
  const set = (patch: Partial<NoticeValues>) => onChange({ ...values, ...patch });

  return (
    <div className="flex flex-col gap-4">
      <Field label={t("notices.form.title")} value={values.title} maxLength={200} onChange={(e) => set({ title: e.target.value })} />
      <div className="flex flex-col gap-1">
        <label htmlFor={bodyId} className="text-body font-semibold">
          {t("notices.form.body")}
        </label>
        <textarea
          id={bodyId}
          rows={8}
          maxLength={10000}
          value={values.body}
          onChange={(e) => set({ body: e.target.value })}
          className="rounded-lg border-2 border-line bg-surface p-3 text-body focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
        />
      </div>
      <SelectField
        label={t("notices.form.language")}
        value={values.language}
        onChange={(e) => set({ language: e.target.value as NoticeLanguage })}
        options={LANGUAGES.map((l) => ({ value: l.code, label: l.nativeName }))}
      />
      <SelectField
        label={t("notices.form.audience")}
        value={values.audience}
        onChange={(e) => set({ audience: e.target.value as NoticeAudience })}
        options={AUDIENCES.map((a) => ({ value: a, label: t(`notices.audience.${a}`) }))}
      />
      {values.audience === "wing" ? (
        <SelectField
          label={t("notices.form.wing")}
          value={values.wingId}
          onChange={(e) => set({ wingId: e.target.value })}
          options={[
            { value: "", label: t("notices.form.chooseWing") },
            ...(wings.data ?? []).map((w) => ({ value: w.id, label: w.name })),
          ]}
        />
      ) : null}
    </div>
  );
}
