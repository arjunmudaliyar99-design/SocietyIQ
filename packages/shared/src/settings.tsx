// Per-person display settings (docs/03 §2). Kept in localStorage for now; M2 saves them
// to the user's profile so they follow the person across devices.
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { I18nextProvider } from "react-i18next";

import { createI18n, isLanguageCode } from "./i18n";
import {
  DEFAULTS,
  ROOT_SIZE,
  SettingsContext,
  TEXT_SIZES,
  type Settings,
  type SettingsContextValue,
  type TextSize,
} from "./settings-context";

function load(storageKey: string): Settings {
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) return DEFAULTS;
    const parsed = JSON.parse(raw) as Partial<Settings>;
    return {
      language: isLanguageCode(parsed.language) ? parsed.language : DEFAULTS.language,
      textSize: TEXT_SIZES.includes(parsed.textSize as TextSize)
        ? (parsed.textSize as TextSize)
        : DEFAULTS.textSize,
      simpleMode: typeof parsed.simpleMode === "boolean" ? parsed.simpleMode : DEFAULTS.simpleMode,
    };
  } catch {
    // Unreadable storage must never stop the app from opening.
    return DEFAULTS;
  }
}

export function SettingsProvider({
  children,
  storageKey = "societyiq.settings",
}: {
  children: ReactNode;
  storageKey?: string;
}) {
  const [settings, setSettings] = useState<Settings>(() => load(storageKey));
  const [i18n] = useState(() => createI18n(settings.language));

  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty("--siq-root-size", ROOT_SIZE[settings.textSize]);
    root.lang = settings.language;
    if (i18n.language !== settings.language) void i18n.changeLanguage(settings.language);
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(settings));
    } catch {
      // Private browsing can block storage; settings then last for this visit only.
    }
  }, [settings, i18n, storageKey]);

  const value = useMemo<SettingsContextValue>(
    () => ({
      ...settings,
      setLanguage: (language) => setSettings((s) => ({ ...s, language })),
      setTextSize: (textSize) => setSettings((s) => ({ ...s, textSize })),
      setSimpleMode: (simpleMode) => setSettings((s) => ({ ...s, simpleMode })),
    }),
    [settings],
  );

  return (
    <SettingsContext.Provider value={value}>
      <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
    </SettingsContext.Provider>
  );
}
