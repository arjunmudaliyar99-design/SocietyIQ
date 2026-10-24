// Usage analytics with PostHog (docs/04 §10). Off unless all of these hold: a key is set, the
// environment is not "local", and the person turned on analytics consent (docs/08 §8). The
// library is loaded only then, so with analytics off nothing is downloaded or sent.
// People are identified by internal UUID only; text, inputs and attributes are masked, and
// session recordings and heatmaps run for society admins only.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

import { queryKeys, useMe } from "./api/hooks";
import { useAuth } from "./auth/auth-context";
import { analyticsAllowed, type AnalyticsConfig } from "./analytics-gate";
import { useCurrentSociety } from "./auth/society-context";

interface ConsentStatus {
  granted: { purpose: string }[];
}

type PostHog = (typeof import("posthog-js"))["default"];

const consentKey = ["me", "consents"] as const;

function useConsents() {
  const { api, status } = useAuth();
  return useQuery({
    queryKey: consentKey,
    queryFn: () => api.get<ConsentStatus>("/me/consents"),
    enabled: status === "signedIn",
  });
}

let loaded: Promise<PostHog> | null = null;

function load(config: AnalyticsConfig): Promise<PostHog> {
  loaded ??= import("posthog-js").then(({ default: posthog }) => {
    posthog.init(config.key ?? "", {
      // Region and host come from configuration only (VITE_POSTHOG_HOST).
      ...(config.host ? { api_host: config.host } : {}),
      person_profiles: "identified_only",
      autocapture: true,
      capture_pageview: "history_change",
      // Never send what is on screen or typed: names, flats, phone numbers, money.
      mask_all_text: true,
      mask_all_element_attributes: true,
      session_recording: { maskAllInputs: true, maskTextSelector: "*" },
      // Recording starts only for admins, below.
      disable_session_recording: true,
      enable_heatmaps: false,
      disable_surveys: true,
    });
    return posthog;
  });
  return loaded;
}

/** Mount once inside the signed-in app (both front ends). Renders nothing. */
export function AnalyticsTracker({ config }: { config: AnalyticsConfig }) {
  const me = useMe();
  const consents = useConsents();
  const society = useCurrentSociety();
  const consented = Boolean(consents.data?.granted.some((c) => c.purpose === "analytics"));
  const allowed = analyticsAllowed(config, consented);
  const userId = me.data?.id;
  const isAdmin = Boolean(society?.society.roles.includes("admin"));

  useEffect(() => {
    if (!allowed) {
      // Consent withdrawn after loading: stop and forget this browser's id.
      void loaded?.then((posthog) => {
        posthog.opt_out_capturing();
        posthog.reset();
      });
      return;
    }
    if (!userId) return;
    void load(config).then((posthog) => {
      posthog.opt_in_capturing();
      posthog.identify(userId);
      if (isAdmin) posthog.startSessionRecording();
      else posthog.stopSessionRecording();
    });
  }, [allowed, userId, isAdmin, config]);

  return null;
}

/** "Share usage data" on or off, for Settings (residents can opt out, docs/04 §10). */
export function AnalyticsSetting() {
  const { t } = useTranslation();
  const { api } = useAuth();
  const client = useQueryClient();
  const consents = useConsents();
  const granted = new Set(consents.data?.granted.map((c) => c.purpose));
  const save = useMutation({
    mutationFn: (analytics: boolean) =>
      api.post<ConsentStatus>("/me/consents", {
        accept_terms_and_privacy: true,
        analytics,
        // Keep the other choice exactly as it is.
        notifications: granted.has("notifications"),
      }),
    onSuccess: (status) => {
      client.setQueryData(consentKey, status);
      void client.invalidateQueries({ queryKey: queryKeys.me });
    },
  });
  if (!consents.data) return null;
  return (
    <label className="flex min-h-[48px] items-center gap-3 text-body">
      <input
        type="checkbox"
        className="h-7 w-7 accent-teal"
        checked={granted.has("analytics")}
        disabled={save.isPending}
        onChange={(e) => save.mutate(e.target.checked)}
      />
      {t("consent.analytics")}
    </label>
  );
}
