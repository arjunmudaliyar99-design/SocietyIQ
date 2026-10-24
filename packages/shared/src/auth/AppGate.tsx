// Order after opening the app: sign in → consent → accept invite (if the link had one) →
// pick a society → the app (docs/02 §3).
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { useMe, useMySocieties, useUpdatePreferences, type Me, type MySociety } from "../api/hooks";
import { isLanguageCode } from "../i18n";
import { TEXT_SIZES, useSettings, type TextSize } from "../settings-context";
import { useAuth } from "./auth-context";
import { AcceptInviteScreen, ConsentScreen, LoadingPage, SignInScreen, SocietyPicker } from "./screens";
import { CurrentSocietyContext, type CurrentSocietyValue } from "./society-context";

const SOCIETY_KEY = "societyiq.society";

function readStored(): string | null {
  try {
    return window.localStorage.getItem(SOCIETY_KEY);
  } catch {
    return null;
  }
}

function store(id: string | null): void {
  try {
    if (id) window.localStorage.setItem(SOCIETY_KEY, id);
    else window.localStorage.removeItem(SOCIETY_KEY);
  } catch {
    // Without storage the picker shows again next visit; nothing breaks.
  }
}

/** Server preferences win on sign-in; later changes on this device are saved back, so the
 * person's language and text size follow them across devices. */
function usePreferenceSync(me: Me | undefined) {
  const settings = useSettings();
  const update = useUpdatePreferences();
  const applied = useRef(false);

  useEffect(() => {
    if (!me || applied.current) return;
    applied.current = true;
    if (isLanguageCode(me.preferred_language)) settings.setLanguage(me.preferred_language);
    if (TEXT_SIZES.includes(me.text_size as TextSize)) settings.setTextSize(me.text_size as TextSize);
    settings.setSimpleMode(me.simple_mode);
  }, [me, settings]);

  const { language, textSize, simpleMode } = settings;
  const { mutate } = update;
  useEffect(() => {
    if (!me || !applied.current) return;
    if (me.preferred_language === language && me.text_size === textSize && me.simple_mode === simpleMode) return;
    mutate({ preferred_language: language, text_size: textSize, simple_mode: simpleMode });
  }, [me, language, textSize, simpleMode, mutate]);
}

export interface PendingInvite {
  societyId: string;
  token: string;
}

export function AppGate({
  allowPassword,
  invite,
  onInviteHandled,
  noSociety,
  children,
}: {
  allowPassword: boolean;
  invite: PendingInvite | null;
  onInviteHandled: () => void;
  /** What to show a signed-in person who belongs to no society yet. */
  noSociety: ReactNode;
  children: ReactNode;
}) {
  const auth = useAuth();
  const me = useMe();
  const societies = useMySocieties();
  const [chosen, setChosen] = useState<string | null>(readStored);
  usePreferenceSync(me.data);

  const list = useMemo<MySociety[]>(() => societies.data ?? [], [societies.data]);
  const current = list.find((s) => s.id === chosen) ?? (list.length === 1 ? list[0] : undefined);

  const value = useMemo<CurrentSocietyValue | null>(
    () =>
      current
        ? {
            society: current,
            canSwitch: list.length > 1,
            switchSociety: () => {
              store(null);
              setChosen(null);
            },
          }
        : null,
    [current, list.length],
  );

  if (auth.status === "loading") return <LoadingPage />;
  if (auth.status === "signedOut") return <SignInScreen allowPassword={allowPassword} />;
  if (me.isPending || societies.isPending) return <LoadingPage />;
  if (me.data?.needs_consent) return <ConsentScreen />;
  if (invite) {
    return (
      <AcceptInviteScreen
        societyId={invite.societyId}
        token={invite.token}
        onDone={(id) => {
          if (id) {
            store(id);
            setChosen(id);
          }
          onInviteHandled();
        }}
      />
    );
  }
  if (list.length === 0) return <>{noSociety}</>;
  if (!value) {
    return (
      <SocietyPicker
        societies={list}
        onPick={(s) => {
          store(s.id);
          setChosen(s.id);
        }}
      />
    );
  }
  return <CurrentSocietyContext.Provider value={value}>{children}</CurrentSocietyContext.Provider>;
}
