// Screens shared by both apps before a society is open: sign-in, consent, picker, invite.
// One main action per screen and plain words (docs/03 §1).
import { CircleAlert } from "lucide-react";
import { useId, useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../api/client";
import { useAcceptInvite, useGiveConsent, type MySociety } from "../api/hooks";
import { BigButton, Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Field } from "../ui/Field";
import { Skeleton } from "../ui/Skeleton";
import { useAuth } from "./auth-context";
import { messageKeyOf } from "./errors";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function ErrorText({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="flex items-center gap-2 text-body font-semibold text-red">
      <CircleAlert size={22} aria-hidden="true" />
      {children}
    </p>
  );
}

export function CenteredPage({ title, children }: { title: string; children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Soft brand band behind the card: gives the first screens some warmth without noise. */}
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-56 bg-gradient-to-b from-mint/40 to-transparent" />
      <div className="relative mx-auto flex min-h-screen max-w-lg flex-col justify-center gap-6 p-4">
        <img src="/logo-light.svg" alt={t("appName")} className="h-12 w-auto self-start" />
        <Card className="flex animate-enter flex-col gap-5 shadow-raised">
          <h1 className="text-title font-bold">{title}</h1>
          {children}
        </Card>
      </div>
    </div>
  );
}

export function LoadingPage() {
  const { t } = useTranslation();
  return (
    <div role="status" className="mx-auto flex min-h-screen max-w-lg flex-col justify-center gap-4 p-4">
      <img src="/logo-light.svg" alt={t("appName")} className="h-12 w-auto animate-pulse self-start" />
      <span className="sr-only">{t("loading")}</span>
      <div className="rounded-card border border-line bg-surface p-5 shadow-card">
        <Skeleton className="mb-4 h-7 w-1/2" />
        <Skeleton className="mb-2 h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    </div>
  );
}

/** Committee: email code or password. Residents: email code only (docs/02 §3). */
export function SignInScreen({ allowPassword }: { allowPassword: boolean }) {
  const { t } = useTranslation();
  const auth = useAuth();
  const [method, setMethod] = useState<"code" | "password">("code");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (auth.mode === "none") {
    return (
      <CenteredPage title={t("auth.title")}>
        <p className="text-body">{t("auth.notConfiguredBody")}</p>
      </CenteredPage>
    );
  }

  async function run(action: () => Promise<void>) {
    setError(null);
    setBusy(true);
    try {
      await action();
    } catch (e) {
      setError(messageKeyOf(e));
    } finally {
      setBusy(false);
    }
  }

  function emailOk(): boolean {
    const ok = EMAIL.test(email.trim());
    setFieldError(ok ? null : t("auth.emailInvalid"));
    return ok;
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const address = email.trim().toLowerCase();
    if (auth.mode === "dev") {
      if (emailOk()) void run(() => auth.devSignIn(address));
    } else if (method === "password") {
      if (emailOk()) void run(() => auth.signInWithPassword(address, password));
    } else if (!codeSent) {
      if (emailOk()) void run(async () => {
        await auth.sendEmailCode(address);
        setCodeSent(true);
      });
    } else {
      void run(() => auth.verifyEmailCode(address, code.trim()));
    }
  }

  const showCode = auth.mode === "supabase" && method === "code" && codeSent;
  const submitLabel =
    auth.mode === "supabase" && method === "code" && !codeSent ? t("auth.sendCode") : t("auth.signIn");

  return (
    <CenteredPage title={t("auth.title")}>
      <form className="flex flex-col gap-5" onSubmit={onSubmit} noValidate>
        {auth.mode === "dev" ? <p className="text-small text-muted">{t("auth.devNote")}</p> : null}
        {showCode ? (
          <>
            <p className="text-body">{t("auth.codeSent", { email: email.trim() })}</p>
            <Field
              label={t("auth.codeLabel")}
              inputMode="numeric"
              autoComplete="one-time-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
          </>
        ) : (
          <Field
            label={t("auth.emailLabel")}
            type="email"
            autoComplete="email"
            value={email}
            error={fieldError ?? undefined}
            onChange={(e) => setEmail(e.target.value)}
          />
        )}
        {auth.mode === "supabase" && method === "password" ? (
          <Field
            label={t("auth.passwordLabel")}
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        ) : null}
        {error ? <ErrorText>{t(error)}</ErrorText> : null}
        <BigButton type="submit" disabled={busy}>
          {submitLabel}
        </BigButton>
      </form>
      {showCode ? (
        <Button variant="secondary" onClick={() => setCodeSent(false)}>
          {t("auth.useAnotherEmail")}
        </Button>
      ) : null}
      {auth.mode === "supabase" && allowPassword && !showCode ? (
        <Button variant="secondary" onClick={() => setMethod(method === "code" ? "password" : "code")}>
          {method === "code" ? t("auth.usePassword") : t("auth.useCode")}
        </Button>
      ) : null}
    </CenteredPage>
  );
}

function CheckBox({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  const id = useId();
  return (
    <div className="flex items-start gap-3">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 h-7 w-7 shrink-0 accent-teal"
      />
      <label htmlFor={id} className="text-body">
        {label}
      </label>
    </div>
  );
}

/** First sign-in consent, recorded in `consents` (docs/08 §8). */
export function ConsentScreen() {
  const { t } = useTranslation();
  const give = useGiveConsent();
  const [agree, setAgree] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const [notifications, setNotifications] = useState(false);
  const [missing, setMissing] = useState(false);

  function onContinue() {
    if (!agree) {
      setMissing(true);
      return;
    }
    give.mutate({ analytics, notifications });
  }

  return (
    <CenteredPage title={t("consent.title")}>
      <p className="text-body">{t("consent.body")}</p>
      <p className="text-body">{t("consent.noAadhaar")}</p>
      <CheckBox
        label={t("consent.agree")}
        checked={agree}
        onChange={(v) => {
          setAgree(v);
          setMissing(false);
        }}
      />
      <CheckBox label={t("consent.notifications")} checked={notifications} onChange={setNotifications} />
      <CheckBox label={t("consent.analytics")} checked={analytics} onChange={setAnalytics} />
      {missing ? <ErrorText>{t("consent.agreeRequired")}</ErrorText> : null}
      {give.isError ? <ErrorText>{t(messageKeyOf(give.error))}</ErrorText> : null}
      <BigButton onClick={onContinue} disabled={give.isPending}>
        {t("consent.continue")}
      </BigButton>
    </CenteredPage>
  );
}

export function SocietyPicker({ societies, onPick }: { societies: MySociety[]; onPick: (s: MySociety) => void }) {
  const { t } = useTranslation();
  return (
    <CenteredPage title={t("picker.title")}>
      <div className="flex flex-col gap-3">
        {societies.map((s) => (
          <BigButton key={s.id} variant="secondary" className="sm:w-full" onClick={() => onPick(s)}>
            {s.city ? `${s.name}, ${s.city}` : s.name}
          </BigButton>
        ))}
      </div>
    </CenteredPage>
  );
}

const INVITE_ERRORS: Record<string, string> = {
  INVITE_EXPIRED: "invite.expired",
  INVITE_OTHER_EMAIL: "invite.otherEmail",
  NOT_FOUND: "invite.notFound",
  ALREADY_MEMBER: "invite.alreadyMember",
};

export function AcceptInviteScreen({
  societyId,
  token,
  onDone,
}: {
  societyId: string;
  token: string;
  onDone: (societyId: string | null) => void;
}) {
  const { t } = useTranslation();
  const accept = useAcceptInvite();
  const errorKey =
    accept.error instanceof ApiError ? (INVITE_ERRORS[accept.error.code] ?? accept.error.messageKey) : null;

  return (
    <CenteredPage title={t("invite.title")}>
      <p className="text-body">{t("invite.body")}</p>
      {errorKey ? <ErrorText>{t(errorKey)}</ErrorText> : null}
      {accept.isError ? (
        <BigButton variant="secondary" onClick={() => onDone(null)}>
          {t("invite.skip")}
        </BigButton>
      ) : (
        <BigButton
          disabled={accept.isPending}
          onClick={() => accept.mutate({ societyId, token }, { onSuccess: () => onDone(societyId) })}
        >
          {t("invite.accept")}
        </BigButton>
      )}
    </CenteredPage>
  );
}
