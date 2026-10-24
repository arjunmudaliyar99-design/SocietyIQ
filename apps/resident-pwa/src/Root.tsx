// Providers and the sign-in gate around the resident app. Residents sign in with an email
// code only (docs/02 §3).
import { useState } from "react";

import {
  AppGate,
  AuthProvider,
  Button,
  CenteredPage,
  QueryClient,
  QueryClientProvider,
  readInvite,
  useAuth,
  useTranslation,
} from "@societyiq/shared";

import App from "./App";
import { authConfig } from "./config";

function NoSociety() {
  const { t } = useTranslation("resident");
  const { t: tc } = useTranslation();
  const { signOut } = useAuth();
  return (
    <CenteredPage title={t("noSociety.title")}>
      <p className="text-body">{t("noSociety.body")}</p>
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
          allowPassword={false}
          invite={invite}
          onInviteHandled={() => {
            window.history.replaceState(null, "", "/");
            setInvite(null);
          }}
          noSociety={<NoSociety />}
        >
          <App />
        </AppGate>
      </AuthProvider>
    </QueryClientProvider>
  );
}
