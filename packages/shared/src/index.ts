export { colors } from "./colors";
export { AnalyticsSetting, AnalyticsTracker } from "./analytics";
export { analyticsAllowed, type AnalyticsConfig } from "./analytics-gate";
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
export { SelectField, type SelectFieldProps } from "./ui/SelectField";
export { LoadingBlock, Skeleton } from "./ui/Skeleton";
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

export { ApiError, createApiClient, type ApiClient, type Schemas } from "./api/client";
export * from "./api/hooks";
export { AppGate, type PendingInvite } from "./auth/AppGate";
export { readInvite } from "./auth/invite-link";
export { AuthProvider, type AuthConfig } from "./auth/AuthProvider";
export { SignInError, useAuth, type AuthMode, type AuthStatus } from "./auth/auth-context";
export { messageKeyOf } from "./auth/errors";
export { CenteredPage, ErrorText, LoadingPage } from "./auth/screens";
export { useCurrentSociety, type CurrentSocietyValue } from "./auth/society-context";

// One TanStack Query instance for both apps and this package.
export {
  QueryClient,
  QueryClientProvider,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

// Apps must use this re-export so there is one react-i18next instance and one context.
export { useTranslation } from "react-i18next";
export * from "./complaints";
export * from "./notices";
