// i18n setup (docs/03 §7). English is the default and the fallback. Other languages start
// as drafts marked "_status": "draft" and need a native speaker's review before a pilot.
import i18next, { type i18n } from "i18next";
import { initReactI18next } from "react-i18next";

import enCommon from "../i18n/en/common.json";
import enCommittee from "../i18n/en/committee.json";
import enResident from "../i18n/en/resident.json";
import guCommon from "../i18n/gu/common.json";
import guCommittee from "../i18n/gu/committee.json";
import guResident from "../i18n/gu/resident.json";
import hiCommon from "../i18n/hi/common.json";
import hiCommittee from "../i18n/hi/committee.json";
import hiResident from "../i18n/hi/resident.json";
import mrCommon from "../i18n/mr/common.json";
import mrCommittee from "../i18n/mr/committee.json";
import mrResident from "../i18n/mr/resident.json";
import taCommon from "../i18n/ta/common.json";
import taCommittee from "../i18n/ta/committee.json";
import taResident from "../i18n/ta/resident.json";

export const LANGUAGES = [
  { code: "en", nativeName: "English" },
  { code: "mr", nativeName: "मराठी" },
  { code: "hi", nativeName: "हिंदी" },
  { code: "gu", nativeName: "ગુજરાતી" },
  { code: "ta", nativeName: "தமிழ்" },
] as const;

export type LanguageCode = (typeof LANGUAGES)[number]["code"];

export const NAMESPACES = ["common", "committee", "resident"] as const;

export const resources = {
  en: { common: enCommon, committee: enCommittee, resident: enResident },
  mr: { common: mrCommon, committee: mrCommittee, resident: mrResident },
  hi: { common: hiCommon, committee: hiCommittee, resident: hiResident },
  gu: { common: guCommon, committee: guCommittee, resident: guResident },
  ta: { common: taCommon, committee: taCommittee, resident: taResident },
} as const;

export function isLanguageCode(value: unknown): value is LanguageCode {
  return LANGUAGES.some((l) => l.code === value);
}

export function createI18n(language: LanguageCode = "en"): i18n {
  const instance = i18next.createInstance();
  void instance.use(initReactI18next).init({
    resources,
    lng: language,
    fallbackLng: "en",
    ns: [...NAMESPACES],
    defaultNS: "common",
    interpolation: { escapeValue: false },
    initAsync: false,
  });
  return instance;
}
