// One flat: details, balance and the people linked to it (docs/02 §4).
import { ArrowLeft, Pencil, UserPlus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  BigButton,
  Button,
  Card,
  ConfirmDialog,
  ErrorText,
  Field,
  MoneyText,
  SelectField,
  formatDate,
  messageKeyOf,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

import {
  useCanManageFlats,
  useFlat,
  useSaveMember,
  useUpdateFlat,
  useWings,
  type FlatDetail,
  type Member,
  type MemberInput,
} from "../api/flats";
import { FlatBills } from "./FlatBills";
import { FlatExtras } from "./FlatExtras";
import { FlatForm } from "./FlatForm";
import { MEMBER_TYPES, flatLabel } from "./labels";

export function FlatPage() {
  const { flatId = "" } = useParams();
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const flat = useFlat(flatId);
  const wings = useWings();
  const canManage = useCanManageFlats();
  const update = useUpdateFlat(flatId);
  const [editing, setEditing] = useState(false);

  if (flat.isPending || wings.isPending) return <p role="status">{tc("loading")}</p>;
  if (flat.isError) return <ErrorText>{tc(messageKeyOf(flat.error))}</ErrorText>;
  if (wings.isError) return <ErrorText>{tc(messageKeyOf(wings.error))}</ErrorText>;
  const data = flat.data;
  const label = flatLabel(data, wings.data.length);

  return (
    <>
      <div className="mb-4">
        <Button variant="secondary" icon={<ArrowLeft size={22} />} onClick={() => navigate("/flats")}>
          {t("flats.title")}
        </Button>
      </div>
      <h1 className="mb-2 text-title font-bold">{t("flats.flatTitle", { label })}</h1>
      <p className="mb-6">
        <Link to={`/flats/${data.id}/ledger`} className="text-body font-semibold text-teal underline">
          {t("ledger.open", { flat: label })}
        </Link>
      </p>

      {editing ? (
        <FlatForm
          wings={wings.data}
          flat={data}
          busy={update.isPending}
          error={update.error}
          onCancel={() => setEditing(false)}
          onSave={(body) => update.mutate(body, { onSuccess: () => setEditing(false) })}
        />
      ) : (
        <FlatFacts flat={data} canManage={canManage} onEdit={() => setEditing(true)} />
      )}

      <h2 className="mt-10 mb-4 text-section font-bold">{t("members.title")}</h2>
      <Members flat={data} canManage={canManage} />
      <FlatBills flatId={data.id} />
      <FlatExtras flatId={data.id} canManage={canManage} />
    </>
  );
}

function FlatFacts({ flat, canManage, onEdit }: { flat: FlatDetail; canManage: boolean; onEdit: () => void }) {
  const { t } = useTranslation("committee");
  const rows: [string, string][] = [
    [t("flats.fields.occupancy"), t(`flats.occupancy.${flat.occupancy}`)],
    [t("flats.fields.carpetArea"), flat.carpet_area_sqft ? t("flats.sqft", { value: flat.carpet_area_sqft }) : t("flats.notGiven")],
    [t("flats.fields.flatType"), flat.flat_type ?? t("flats.notGiven")],
    [t("flats.fields.usage"), t(`flats.usage.${flat.usage}`)],
    [t("flats.fields.waterPoints"), flat.water_points ?? t("flats.notGiven")],
    [t("flats.fields.municipalAccount"), flat.municipal_property_account ?? t("flats.notGiven")],
  ];
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_auto]">
      <Card>
        <dl className="grid gap-3 sm:grid-cols-2">
          {rows.map(([k, v]) => (
            <div key={k}>
              <dt className="text-small text-muted">{k}</dt>
              <dd className="text-body font-semibold">{v}</dd>
            </div>
          ))}
          <div>
            <dt className="text-small text-muted">{t("flats.fields.cost")}</dt>
            <dd className="text-body font-semibold">
              {flat.certified_construction_cost_paise !== null ? (
                <MoneyText paise={flat.certified_construction_cost_paise} />
              ) : (
                t("flats.notGiven")
              )}
            </dd>
          </div>
        </dl>
        {canManage ? (
          <div className="mt-5">
            <Button variant="secondary" icon={<Pencil size={20} />} onClick={onEdit}>
              {t("flats.edit")}
            </Button>
          </div>
        ) : null}
      </Card>
      <Card className="min-w-56">
        <p className="text-body text-muted">{flat.balance_paise < 0 ? t("flats.advance") : t("flats.balance")}</p>
        <MoneyText paise={Math.abs(flat.balance_paise)} className="block text-stat font-bold" />
      </Card>
    </div>
  );
}

function Members({ flat, canManage }: { flat: FlatDetail; canManage: boolean }) {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const { language } = useSettings();
  const save = useSaveMember(flat.id);
  const [adding, setAdding] = useState(false);
  const [ending, setEnding] = useState<Member | null>(null);

  return (
    <div className="flex flex-col gap-3">
      {flat.members.length === 0 ? <p className="text-body">{t("flats.noMember")}</p> : null}
      <ul className="flex flex-col gap-3">
        {flat.members.map((m) => (
          <li key={m.id}>
            <Card className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-body font-bold">
                  {m.full_name}
                  {m.is_primary ? ` · ${t("members.primary")}` : ""}
                </p>
                <p className="text-small text-muted">
                  {t(`members.type.${m.member_type}`)}
                  {m.phone_e164 ? ` · ${m.phone_e164}` : ""}
                  {m.email ? ` · ${m.email}` : ""}
                </p>
                {m.to_date ? (
                  <p className="text-small text-muted">{t("members.left", { date: formatDate(m.to_date, language) })}</p>
                ) : null}
              </div>
              {canManage && !m.to_date ? (
                <Button variant="secondary" onClick={() => setEnding(m)}>
                  {t("members.end")}
                </Button>
              ) : null}
            </Card>
          </li>
        ))}
      </ul>
      {canManage && !adding ? (
        <div>
          <Button icon={<UserPlus size={22} />} onClick={() => setAdding(true)}>
            {t("members.add")}
          </Button>
        </div>
      ) : null}
      {adding ? (
        <MemberForm
          busy={save.isPending}
          error={save.error}
          onCancel={() => setAdding(false)}
          onSave={(body) => save.mutate({ body }, { onSuccess: () => setAdding(false) })}
        />
      ) : null}
      {save.isError && !adding ? <ErrorText>{tc(messageKeyOf(save.error))}</ErrorText> : null}
      <ConfirmDialog
        open={ending !== null}
        question={t("members.endQuestion", { name: ending?.full_name ?? "" })}
        confirmLabel={t("members.endConfirm")}
        onConfirm={() => {
          if (ending) save.mutate({ id: ending.id, body: { to_date: localToday() } }, { onSuccess: () => setEnding(null) });
        }}
        onCancel={() => setEnding(null)}
      />
    </div>
  );
}

/** Today on the person's own clock (India), as YYYY-MM-DD. */
function localToday(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function MemberForm({
  busy,
  error,
  onSave,
  onCancel,
}: {
  busy: boolean;
  error: unknown;
  onSave: (body: MemberInput) => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [type, setType] = useState<(typeof MEMBER_TYPES)[number]>("owner");
  const [problem, setProblem] = useState<string | null>(null);

  function submit(event: FormEvent) {
    event.preventDefault();
    const digits = phone.replace(/\D/g, "").replace(/^91(?=\d{10}$)/, "");
    if (!name.trim()) return setProblem(t("setup.required"));
    if (phone.trim() && digits.length !== 10) return setProblem(t("setup.invalidPhone"));
    if (email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) return setProblem(t("setup.invalidEmail"));
    setProblem(null);
    onSave({
      full_name: name.trim(),
      phone_e164: phone.trim() ? `+91${digits}` : null,
      email: email.trim() || null,
      member_type: type,
      is_primary: type === "owner",
      tenant_can_pay: false,
    });
  }

  return (
    <Card>
      <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
        <h3 className="text-section font-bold">{t("members.add")}</h3>
        <Field label={t("invites.name")} value={name} onChange={(e) => setName(e.target.value)} />
        <SelectField
          label={t("members.typeLabel")}
          options={MEMBER_TYPES.map((m) => ({ value: m, label: t(`members.type.${m}`) }))}
          value={type}
          onChange={(e) => setType(e.target.value as (typeof MEMBER_TYPES)[number])}
        />
        <Field
          label={t("invites.phone")}
          help={t("invites.phoneHelp")}
          inputMode="numeric"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <Field label={t("invites.email")} help={t("setup.optional")} type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        {problem ? <ErrorText>{problem}</ErrorText> : null}
        {error ? <ErrorText>{tc(messageKeyOf(error))}</ErrorText> : null}
        <BigButton type="submit" disabled={busy}>
          {t("members.save")}
        </BigButton>
        <Button variant="secondary" onClick={onCancel}>
          {tc("back")}
        </Button>
      </form>
    </Card>
  );
}
