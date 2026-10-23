import { useEffect, useState } from "react";

import { Button, Card, useTranslation } from "@societyiq/shared";

// Chrome's install event is not in the TypeScript DOM types.
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
}

const SEEN_KEY = "societyiq.installBannerSeen";

function isStandalone(): boolean {
  return window.matchMedia?.("(display-mode: standalone)").matches ?? false;
}

function isIphone(): boolean {
  return /iPhone|iPad|iPod/.test(window.navigator.userAgent);
}

function alreadySeen(): boolean {
  try {
    return window.localStorage.getItem(SEEN_KEY) === "1";
  } catch {
    return false;
  }
}

/** "Add SocietyIQ to your home screen", shown once (docs/04 §16). */
export function InstallBanner() {
  const { t } = useTranslation("resident");
  const [promptEvent, setPromptEvent] = useState<BeforeInstallPromptEvent | null>(null);
  const [hidden, setHidden] = useState(() => alreadySeen() || isStandalone());

  useEffect(() => {
    const onPrompt = (event: Event) => {
      // Keep the event so the install dialog opens from our own big button.
      event.preventDefault();
      setPromptEvent(event as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  const dismiss = () => {
    setHidden(true);
    try {
      window.localStorage.setItem(SEEN_KEY, "1");
    } catch {
      // Storage blocked: banner may show again next visit, which is harmless.
    }
  };

  if (hidden || (!promptEvent && !isIphone())) return null;

  return (
    <Card role="region" aria-label={t("install.title")} className="mb-4 flex flex-col gap-3">
      <h2 className="text-section font-bold">{t("install.title")}</h2>
      <p className="text-body">{promptEvent ? t("install.body") : t("install.iphone")}</p>
      <div className="flex flex-wrap gap-2">
        {promptEvent ? (
          <Button
            onClick={() => {
              void promptEvent.prompt().finally(dismiss);
            }}
          >
            {t("install.add")}
          </Button>
        ) : null}
        <Button variant="secondary" onClick={dismiss}>
          {t("install.later")}
        </Button>
      </div>
    </Card>
  );
}
