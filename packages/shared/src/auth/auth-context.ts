// Auth types and hook, kept apart from the provider component for fast refresh.
import { createContext, useContext } from "react";

import type { ApiClient } from "../api/client";

/**
 * supabase: real sign-in (docs/04 §5).
 * dev: local preview without a Supabase project; the backend mints the token and only
 *      mounts that route when APP_ENV=local.
 * none: nothing configured; the sign-in screen says so.
 */
export type AuthMode = "supabase" | "dev" | "none";

export type AuthStatus = "loading" | "signedOut" | "signedIn";

export interface AuthContextValue {
  mode: AuthMode;
  status: AuthStatus;
  email: string | null;
  api: ApiClient;
  signInWithPassword: (email: string, password: string) => Promise<void>;
  sendEmailCode: (email: string) => Promise<void>;
  verifyEmailCode: (email: string, code: string) => Promise<void>;
  /** dev mode only */
  devSignIn: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

/** Thrown by sign-in calls; `messageKey` is an i18n key. */
export class SignInError extends Error {
  readonly messageKey: string;
  constructor(messageKey: string) {
    super(messageKey);
    this.messageKey = messageKey;
  }
}
