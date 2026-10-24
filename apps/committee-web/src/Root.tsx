// Providers and the sign-in gate around the committee app.
import { useState } from "react";

import {
  AnalyticsTracker,
  AppGate,
  AuthProvider,
  BigButton,
  Button,
  CenteredPage,
  QueryClient,
  QueryClientProvider,
  readInvite,
  useAuth,
  useTranslation,
} from "@societyiq/shared";

import App from "./App";
import { analyticsConfig, authConfig } from "./config";
import { SetupWizard } from "./setup/SetupWizard";

function NoSociety() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const { signOut } = useAuth();
  const [setup, setSetup] = useState(false);
  if (setup) return <SetupWizard onCancel={() => setSetup(false)} />;
  return (
    <CenteredPage title={t("noSociety.title")}>
      <p className="text-body">{t("noSociety.body")}</p>
      <BigButton onClick={() => setSetup(true)}>{t("noSociety.setup")}</BigButton>
      <Button variant="secondary" onClick={() => void signOut()}>
        {tc("signOut")}
      </Button>
    </CenteredPage>
  );
}

export function Root({ queryClient }: { queryClient?: QueryClient }) {
  const [client] = useState(() => queryClient ?? new QueryClient({ defaultOptions: { queries: { retry: 1 } } }));
  const [invite, setInvite] = useState(() => readInvite(window.location));
  return (
    <QueryClientProvider client={client}>
      <AuthProvider config={authConfig}>
        <AppGate
          allowPassword
          invite={invite}
          onInviteHandled={() => {
            window.history.replaceState(null, "", "/");
            setInvite(null);
          }}
          noSociety={<NoSociety />}
        >
          <AnalyticsTracker config={analyticsConfig} />
          <App />
        </AppGate>
      </AuthProvider>
    </QueryClientProvider>
  );
}
