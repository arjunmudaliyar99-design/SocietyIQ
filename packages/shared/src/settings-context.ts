// Settings types, defaults and hook, kept apart from the provider component for fast refresh.
import { createContext, useContext } from "react";

import type { LanguageCode } from "./i18n";

export type TextSize = "normal" | "large" | "xlarge";

export const TEXT_SIZES: readonly TextSize[] = ["normal", "large", "xlarge"];

// Body text size for each setting (docs/03 §2). Every other size is in rem, so it follows.
export const ROOT_SIZE: Record<TextSize, string> = { normal: "18px", large: "21px", xlarge: "24px" };

export interface Settings {
  language: LanguageCode;
  textSize: TextSize;
  simpleMode: boolean;
}

export const DEFAULTS: Settings = { language: "en", textSize: "normal", simpleMode: true };

export interface SettingsContextValue extends Settings {
  setLanguage: (language: LanguageCode) => void;
  setTextSize: (size: TextSize) => void;
  setSimpleMode: (on: boolean) => void;
}

export const SettingsContext = createContext<SettingsContextValue | null>(null);

export function useSettings(): SettingsContextValue {
  const value = useContext(SettingsContext);
  if (!value) throw new Error("useSettings must be used inside SettingsProvider");
  return value;
}
