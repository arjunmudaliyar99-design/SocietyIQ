import { Copy } from "lucide-react";
import { useState } from "react";

import { Button, Card, useTranslation, type InviteResult } from "@societyiq/shared";

/** Invite links are shown once. Email sending comes in M9; until then the admin shares them. */
export function InviteLinks({ invites }: { invites: InviteResult[] }) {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const [copied, setCopied] = useState<string | null>(null);

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-section font-bold">{t("invites.linkTitle")}</h2>
      <p className="text-body">{t("invites.linkBody")}</p>
      {invites.map((inv) => {
        const who =
          inv.membership.invited_name ?? inv.membership.invited_email ?? inv.membership.invited_phone_e164 ?? "";
        return (
          <Card key={inv.membership.id} className="flex flex-col gap-2">
            <p className="text-body font-semibold">
              {who} · {tc(`roles.${inv.membership.role}`)}
            </p>
            <p className="text-small break-all text-muted">{inv.invite_link}</p>
            <div>
              <Button
                variant="secondary"
                icon={<Copy size={20} />}
                onClick={() => {
                  void navigator.clipboard?.writeText(inv.invite_link).then(() => setCopied(inv.membership.id));
                }}
              >
                {copied === inv.membership.id ? t("invites.copied") : t("invites.copy")}
              </Button>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
