// Society settings → people and invites (docs/02 §2-3). Admin only; the backend enforces it.
import { UserPlus } from "lucide-react";
import { useState } from "react";

import {
  BigButton,
  Button,
  Card,
  EmptyState,
  ErrorText,
  Field,
  SelectField,
  messageKeyOf,
  useCurrentSociety,
  useInvite,
  useMemberships,
  useTranslation,
  type InviteResult,
} from "@societyiq/shared";

import { InviteLinks } from "./InviteLinks";
import { COMMITTEE_ROLES, phoneToE164, validateInvite, type InviteDraft } from "./invite-form";

const EMPTY: InviteDraft = { name: "", email: "", phone: "", role: "committee" };

export function PeoplePage() {
  const current = useCurrentSociety();
  if (!current) return null;
  return <People societyId={current.society.id} isAdmin={current.society.roles.includes("admin")} />;
}

function People({ societyId, isAdmin }: { societyId: string; isAdmin: boolean }) {
  const { t } = useTranslation("committee");

  if (!isAdmin) {
    return (
      <>
        <h1 className="mb-6 text-title font-bold">{t("invites.title")}</h1>
        <EmptyState message={t("invites.adminOnly")} />
      </>
    );
  }
  return (
    <>
      <h1 className="mb-6 text-title font-bold">{t("invites.title")}</h1>
      <MemberList societyId={societyId} />
      <InviteForm societyId={societyId} key={societyId} />
    </>
  );
}

function MemberList({ societyId }: { societyId: string }) {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const members = useMemberships(societyId);

  if (members.isPending) return <p role="status">{tc("loading")}</p>;
  if (members.isError) return <ErrorText>{tc(messageKeyOf(members.error))}</ErrorText>;
  return (
    <ul className="mb-8 flex flex-col gap-3">
      {members.data.map((m) => (
        <li key={m.id}>
          <Card className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-body font-semibold">
                {m.invited_name ?? m.invited_email ?? m.invited_phone_e164}
                {m.is_you ? ` ${t("invites.you")}` : ""}
              </p>
              <p className="text-small text-muted">{m.invited_email ?? m.invited_phone_e164}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-body">{tc(`roles.${m.role}`)}</span>
              <span className="rounded-full border-2 border-line px-3 py-1 text-small font-semibold">
                {t(`invites.status.${m.status}`)}
              </span>
            </div>
          </Card>
        </li>
      ))}
    </ul>
  );
}

function InviteForm({ societyId }: { societyId: string }) {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const invite = useInvite(societyId);
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<InviteDraft>(EMPTY);
  const [problem, setProblem] = useState<string | null>(null);
  const [created, setCreated] = useState<InviteResult[]>([]);

  if (!open) {
    return (
      <div className="flex flex-col gap-4">
        {created.length ? <InviteLinks invites={created} /> : null}
        <BigButton icon={<UserPlus size={24} />} onClick={() => setOpen(true)}>
          {t("invites.invite")}
        </BigButton>
      </div>
    );
  }

  function send() {
    const key = validateInvite(draft);
    setProblem(key ? t(key) : null);
    if (key) return;
    invite.mutate(
      {
        name: draft.name.trim() || null,
        email: draft.email.trim() || null,
        phone_e164: draft.phone.trim() ? phoneToE164(draft.phone) : null,
        role: draft.role,
      },
      {
        onSuccess: (result) => {
          setCreated((all) => [result, ...all]);
          setDraft(EMPTY);
          setOpen(false);
        },
      },
    );
  }

  return (
    <Card className="flex flex-col gap-4">
      <h2 className="text-section font-bold">{t("invites.invite")}</h2>
      <Field label={t("invites.name")} value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
      <Field
        label={t("invites.email")}
        type="email"
        value={draft.email}
        onChange={(e) => setDraft({ ...draft, email: e.target.value })}
      />
      <Field
        label={t("invites.phone")}
        help={t("invites.phoneHelp")}
        inputMode="numeric"
        value={draft.phone}
        onChange={(e) => setDraft({ ...draft, phone: e.target.value })}
      />
      <SelectField
        label={t("invites.role")}
        options={COMMITTEE_ROLES.map((r) => ({ value: r, label: tc(`roles.${r}`) }))}
        value={draft.role}
        onChange={(e) => setDraft({ ...draft, role: e.target.value as InviteDraft["role"] })}
      />
      {problem ? <ErrorText>{problem}</ErrorText> : null}
      {invite.isError ? <ErrorText>{tc(messageKeyOf(invite.error))}</ErrorText> : null}
      <BigButton onClick={send} disabled={invite.isPending}>
        {t("invites.send")}
      </BigButton>
      <Button variant="secondary" onClick={() => setOpen(false)}>
        {tc("back")}
      </Button>
    </Card>
  );
}
