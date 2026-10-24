// Sign-in state for both apps (docs/02 §3, docs/04 §5). Supabase keeps its own session in
// storage; the token is read from it for every API call.
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { useEffect, useMemo, useState, type ReactNode } from "react";

import { createApiClient } from "../api/client";
import { AuthContext, SignInError, type AuthContextValue, type AuthMode, type AuthStatus } from "./auth-context";

const DEV_TOKEN_KEY = "societyiq.devToken";

/** Holds the current access token outside React state: the API client reads it on every
 * call, and changing it must not re-render the app. */
class TokenStore {
  private token: string | null;
  constructor(token: string | null) {
    this.token = token;
  }
  get(): string | null {
    return this.token;
  }
  set(token: string | null): void {
    this.token = token;
  }
}

export interface AuthConfig {
  apiBaseUrl: string;
  supabaseUrl?: string;
  supabaseAnonKey?: string;
  /** Local preview only; ignored when Supabase is configured. */
  devSignIn?: boolean;
}

function readDevToken(): { token: string; email: string } | null {
  try {
    const raw = window.localStorage.getItem(DEV_TOKEN_KEY);
    return raw ? (JSON.parse(raw) as { token: string; email: string }) : null;
  } catch {
    return null;
  }
}

function writeDevToken(value: { token: string; email: string } | null): void {
  try {
    if (value) window.localStorage.setItem(DEV_TOKEN_KEY, JSON.stringify(value));
    else window.localStorage.removeItem(DEV_TOKEN_KEY);
  } catch {
    // Blocked storage: the dev sign-in lasts for this page only.
  }
}

export function AuthProvider({ config, children }: { config: AuthConfig; children: ReactNode }) {
  const mode: AuthMode =
    config.supabaseUrl && config.supabaseAnonKey ? "supabase" : config.devSignIn ? "dev" : "none";

  const supabase = useMemo<SupabaseClient | null>(
    () =>
      mode === "supabase" && config.supabaseUrl && config.supabaseAnonKey
        ? createClient(config.supabaseUrl, config.supabaseAnonKey)
        : null,
    [mode, config.supabaseUrl, config.supabaseAnonKey],
  );

  const initialDev = mode === "dev" ? readDevToken() : null;
  const [tokens] = useState(() => new TokenStore(initialDev?.token ?? null));
  const [status, setStatus] = useState<AuthStatus>(
    mode === "supabase" ? "loading" : initialDev ? "signedIn" : "signedOut",
  );
  const [email, setEmail] = useState<string | null>(initialDev?.email ?? null);

  useEffect(() => {
    if (!supabase) return;
    void supabase.auth.getSession().then(({ data }) => {
      tokens.set(data.session?.access_token ?? null);
      setEmail(data.session?.user.email ?? null);
      setStatus(data.session ? "signedIn" : "signedOut");
    });
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      tokens.set(session?.access_token ?? null);
      setEmail(session?.user.email ?? null);
      setStatus(session ? "signedIn" : "signedOut");
    });
    return () => data.subscription.unsubscribe();
  }, [supabase, tokens]);

  const value = useMemo<AuthContextValue>(() => {
    const api = createApiClient(config.apiBaseUrl, () => tokens.get());

    function requireSupabase(): SupabaseClient {
      if (!supabase) throw new SignInError("auth.notConfigured");
      return supabase;
    }

    return {
      mode,
      status,
      email,
      api,
      async signInWithPassword(address, password) {
        const { error } = await requireSupabase().auth.signInWithPassword({ email: address, password });
        if (error) throw new SignInError("auth.wrongPassword");
      },
      async sendEmailCode(address) {
        const { error } = await requireSupabase().auth.signInWithOtp({
          email: address,
          options: { shouldCreateUser: true },
        });
        if (error) throw new SignInError("auth.codeNotSent");
      },
      async verifyEmailCode(address, code) {
        const { error } = await requireSupabase().auth.verifyOtp({ email: address, token: code, type: "email" });
        if (error) throw new SignInError("auth.wrongCode");
      },
      async devSignIn(address) {
        if (mode !== "dev") throw new SignInError("auth.notConfigured");
        const { access_token } = await api.post<{ access_token: string }>("/dev/token", { email: address });
        tokens.set(access_token);
        writeDevToken({ token: access_token, email: address });
        setEmail(address);
        setStatus("signedIn");
      },
      async signOut() {
        if (supabase) await supabase.auth.signOut();
        writeDevToken(null);
        tokens.set(null);
        setEmail(null);
        setStatus("signedOut");
      },
    };
  }, [config.apiBaseUrl, mode, status, email, supabase, tokens]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
