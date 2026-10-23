export { colors } from "./colors";
export { LANGUAGES, NAMESPACES, createI18n, isLanguageCode, resources, type LanguageCode } from "./i18n";
export { SettingsProvider } from "./settings";
export { TEXT_SIZES, useSettings, type Settings, type TextSize } from "./settings-context";
export { formatDate } from "./utils/date";
export { formatPaise } from "./utils/money";
export { contrastRatio } from "./utils/contrast";

export { BigButton, Button, type ButtonProps, type ButtonVariant } from "./ui/Button";
export { Card, StatCard, type StatCardProps } from "./ui/Card";
export { ConfirmDialog, Dialog, type ConfirmDialogProps } from "./ui/Dialog";
export { Field, type FieldProps } from "./ui/Field";
export { MoneyText, type MoneyTextProps } from "./ui/MoneyText";
export {
  HelpButton,
  LanguageSwitcher,
  TextSizeSwitcher,
  ViewModeSwitcher,
  type Contact,
} from "./ui/Settings";
export { EmptyState, StepHeader, type EmptyStateProps } from "./ui/Small";
export { StatusPill, type Status } from "./ui/StatusPill";
export { MIN_TOAST_MS, Toast, type ToastProps } from "./ui/Toast";

// Apps must use this re-export so there is one react-i18next instance and one context.
export { useTranslation } from "react-i18next";
