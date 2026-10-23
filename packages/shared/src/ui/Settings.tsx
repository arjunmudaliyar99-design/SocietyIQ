import { CircleQuestionMark, Globe } from "lucide-react";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { LANGUAGES, isLanguageCode } from "../i18n";
import { TEXT_SIZES, useSettings } from "../settings-context";
import { Button } from "./Button";
import { Dialog } from "./Dialog";

/** Language names in their own scripts, always reachable from the top bar (docs/03 §2, §5). */
export function LanguageSwitcher({ className = "" }: { className?: string }) {
  const { t } = useTranslation();
  const { language, setLanguage } = useSettings();
  const id = useId();
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <Globe size={22} aria-hidden="true" />
      <label htmlFor={id} className="sr-only">
        {t("language")}
      </label>
      <select
        id={id}
        value={language}
        onChange={(e) => {
          if (isLanguageCode(e.target.value)) setLanguage(e.target.value);
        }}
        className="min-h-[48px] rounded-lg border-2 border-line bg-surface px-3 text-body focus-visible:outline-3 focus-visible:outline-ink"
      >
        {LANGUAGES.map((l) => (
          <option key={l.code} value={l.code} lang={l.code}>
            {l.nativeName}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Normal / Large / Extra large (docs/03 §2). */
export function TextSizeSwitcher() {
  const { t } = useTranslation();
  const { textSize, setTextSize } = useSettings();
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-2 text-body font-semibold">{t("textSize.label")}</legend>
      <div className="flex flex-wrap gap-2">
        {TEXT_SIZES.map((size) => (
          <Button
            key={size}
            variant={size === textSize ? "primary" : "secondary"}
            aria-pressed={size === textSize}
            onClick={() => setTextSize(size)}
          >
            {t(`textSize.${size}`)}
          </Button>
        ))}
      </div>
    </fieldset>
  );
}

/** Simple view is the default; Detailed view shows more (docs/03 §2). */
export function ViewModeSwitcher() {
  const { t } = useTranslation();
  const { simpleMode, setSimpleMode } = useSettings();
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-2 text-body font-semibold">{t("view.label")}</legend>
      <div className="flex flex-wrap gap-2">
        <Button variant={simpleMode ? "primary" : "secondary"} aria-pressed={simpleMode} onClick={() => setSimpleMode(true)}>
          {t("view.simple")}
        </Button>
        <Button variant={simpleMode ? "secondary" : "primary"} aria-pressed={!simpleMode} onClick={() => setSimpleMode(false)}>
          {t("view.detailed")}
        </Button>
      </div>
    </fieldset>
  );
}

export interface Contact {
  name?: string;
  phone?: string;
  email?: string;
  hours?: string;
}

/**
 * Shows the society champion's contact (society data, from M2) and SocietyIQ support.
 * Support details come only from configuration, never hard-coded (CLAUDE.md §4a).
 */
export function HelpButton({ society, support }: { society?: Contact; support: Contact }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="secondary" icon={<CircleQuestionMark size={22} />} onClick={() => setOpen(true)}>
        {t("help.button")}
      </Button>
      <Dialog open={open} title={t("help.title")} onClose={() => setOpen(false)}>
        <section className="mb-5">
          <h3 className="mb-1 text-body font-bold">{t("help.society")}</h3>
          {society && (society.phone || society.email) ? (
            <ContactLines contact={society} />
          ) : (
            <p className="text-body text-muted">{t("help.societyMissing")}</p>
          )}
        </section>
        <section>
          <h3 className="mb-1 text-body font-bold">{t("help.support")}</h3>
          <ContactLines contact={support} />
        </section>
      </Dialog>
    </>
  );
}

function ContactLines({ contact }: { contact: Contact }) {
  const { t } = useTranslation();
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-body">
      {contact.name ? <dd className="col-span-2 font-semibold">{contact.name}</dd> : null}
      {contact.phone ? (
        <>
          <dt className="text-muted">{t("help.phone")}</dt>
          <dd>
            <a className="text-teal underline" href={`tel:${contact.phone.replace(/\s/g, "")}`}>
              {contact.phone}
            </a>
          </dd>
        </>
      ) : null}
      {contact.email ? (
        <>
          <dt className="text-muted">{t("help.email")}</dt>
          <dd>
            <a className="break-all text-teal underline" href={`mailto:${contact.email}`}>
              {contact.email}
            </a>
          </dd>
        </>
      ) : null}
      {contact.hours ? (
        <>
          <dt className="text-muted">{t("help.hours")}</dt>
          <dd>{contact.hours}</dd>
        </>
      ) : null}
    </dl>
  );
}
