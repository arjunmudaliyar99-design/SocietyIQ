import { WifiOff } from "lucide-react";
import { useEffect, useState } from "react";

import { useTranslation } from "@societyiq/shared";

/** docs/04 §16: offline, the app shows what was last loaded and says so plainly. */
export function OfflineBanner() {
  const { t } = useTranslation("resident");
  const [online, setOnline] = useState(() => navigator.onLine);
  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
    };
  }, []);
  if (online) return null;
  return (
    <p role="status" className="mb-4 flex items-center gap-2 rounded-card border-2 border-terracotta bg-surface p-3 text-body">
      <WifiOff size={22} aria-hidden="true" />
      {t("money.offline")}
    </p>
  );
}
