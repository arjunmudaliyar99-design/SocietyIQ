import type { AnalyticsConfig, AuthConfig, Contact } from "@societyiq/shared";

// Support contact comes only from configuration (CLAUDE.md §4a).
export const support: Contact = {
  email: import.meta.env.VITE_SUPPORT_EMAIL || "support@example.com",
  phone: import.meta.env.VITE_SUPPORT_PHONE || undefined,
  hours: import.meta.env.VITE_SUPPORT_HOURS || undefined,
};

export const authConfig: AuthConfig = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  supabaseUrl: import.meta.env.VITE_SUPABASE_URL || undefined,
  supabaseAnonKey: import.meta.env.VITE_SUPABASE_ANON_KEY || undefined,
  // Local preview only; the backend refuses it outside APP_ENV=local.
  devSignIn: import.meta.env.DEV && import.meta.env.VITE_DEV_SIGN_IN === "true",
};

// Usage analytics are off without a key and always off in local (docs/04 §10).
export const analyticsConfig: AnalyticsConfig = {
  key: import.meta.env.VITE_POSTHOG_KEY || undefined,
  host: import.meta.env.VITE_POSTHOG_HOST || undefined,
  env: import.meta.env.VITE_APP_ENV || "local",
};
