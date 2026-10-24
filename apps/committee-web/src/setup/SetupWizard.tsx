// Create a society in 3 steps (docs/02 §3): details, billing settings, invite the committee.
import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import {
  BigButton,
  Button,
  Card,
  CenteredPage,
  ErrorText,
  Field,
  SelectField,
  StepHeader,
  messageKeyOf,
  queryKeys,
  useCreateSociety,
  useQueryClient,
  useSettings,
  useTranslation,
  type InviteInput,
  type SocietyCreated,
} from "@societyiq/shared";

import { InviteLinks } from "./InviteLinks";
import { COMMITTEE_ROLES, phoneToE164, validateInvite, type InviteDraft } from "./invite-form";

interface Draft {
  name: string;
  registrationNumber: string;
  addressLine: string;
  city: string;
  state: string;
  pincode: string;
  fyStartMonth: string;
  billingFrequency: "monthly" | "quarterly";
  billDay: string;
  dueDays: string;
  upiId: string;
  upiPayeeName: string;
  bankName: string;
  bankLast4: string;
}

const EMPTY: Draft = {
  name: "",
  registrationNumber: "",
  addressLine: "",
  city: "",
  state: "Maharashtra",
  pincode: "",
  fyStartMonth: "4",
  billingFrequency: "monthly",
  billDay: "",
  dueDays: "15",
  upiId: "",
  upiPayeeName: "",
  bankName: "",
  bankLast4: "",
};

type Errors = Partial<Record<keyof Draft, string>>;

const optional = (v: string) => (v.trim() ? v.trim() : null);

export function SetupWizard({ onCancel }: { onCancel?: () => void }) {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const { language } = useSettings();
  const create = useCreateSociety();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(1);
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [errors, setErrors] = useState<Errors>({});
  const [invites, setInvites] = useState<InviteDraft[]>([]);
  const [inviteErrors, setInviteErrors] = useState<Record<number, string>>({});
  const [created, setCreated] = useState<SocietyCreated | null>(null);

  const set = (key: keyof Draft) => (e: { target: { value: string } }) =>
    setDraft((d) => ({ ...d, [key]: e.target.value }));

  // Month names from the browser in the chosen language, so they need no translation keys.
  const months = Array.from({ length: 12 }, (_, i) => ({
    value: String(i + 1),
    label: new Intl.DateTimeFormat(language, { month: "long" }).format(new Date(2026, i, 1)),
  }));

  function checkStep1(): boolean {
    const e: Errors = {};
    if (!draft.name.trim()) e.name = t("setup.required");
    if (draft.pincode.trim() && !/^[1-9][0-9]{5}$/.test(draft.pincode.trim())) e.pincode = t("setup.invalidPincode");
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function checkStep2(): boolean {
    const e: Errors = {};
    const day = Number(draft.billDay);
    if (!Number.isInteger(day) || day < 1 || day > 28) e.billDay = t("setup.invalidBillDay");
    const due = Number(draft.dueDays);
    if (draft.dueDays.trim() === "" || !Number.isInteger(due) || due < 0) e.dueDays = t("setup.invalidNumber");
    if (draft.bankLast4.trim() && !/^[0-9]{4}$/.test(draft.bankLast4.trim())) e.bankLast4 = t("setup.invalidLast4");
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function checkStep3(): boolean {
    const e: Record<number, string> = {};
    invites.forEach((inv, i) => {
      const problem = validateInvite(inv);
      if (problem) e[i] = t(problem);
    });
    setInviteErrors(e);
    return Object.keys(e).length === 0;
  }

  function submit() {
    if (!checkStep3()) return;
    const inviteBody: InviteInput[] = invites.map((inv) => ({
      name: optional(inv.name),
      email: optional(inv.email),
      phone_e164: inv.phone.trim() ? phoneToE164(inv.phone) : null,
      role: inv.role,
    }));
    create.mutate(
      {
        details: {
          name: draft.name.trim(),
          registration_number: optional(draft.registrationNumber),
          address_line: optional(draft.addressLine),
          city: optional(draft.city),
          state: draft.state.trim() || "Maharashtra",
          pincode: optional(draft.pincode),
          financial_year_start_month: Number(draft.fyStartMonth),
        },
        billing: {
          billing_frequency: draft.billingFrequency,
          bill_day: Number(draft.billDay),
          due_days: Number(draft.dueDays),
          upi_id: optional(draft.upiId),
          upi_payee_name: optional(draft.upiPayeeName),
          bank_name: optional(draft.bankName),
          bank_account_last4: optional(draft.bankLast4),
        },
        invites: inviteBody,
      },
      { onSuccess: setCreated },
    );
  }

  if (created) {
    return (
      <CenteredPage title={t("setup.created")}>
        <p className="text-body">{created.society.name}</p>
        {created.invites.length ? <InviteLinks invites={created.invites} /> : null}
        <BigButton onClick={() => void queryClient.invalidateQueries({ queryKey: queryKeys.mySocieties })}>
          {t("setup.goToSociety")}
        </BigButton>
      </CenteredPage>
    );
  }

  return (
    <CenteredPage title={t("setup.title")}>
      {step === 1 ? (
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            if (checkStep1()) setStep(2);
          }}
        >
          <StepHeader current={1} total={3} title={t("setup.step1")} />
          <Field label={t("setup.name")} value={draft.name} onChange={set("name")} error={errors.name} />
          <Field
            label={t("setup.registrationNumber")}
            help={t("setup.optional")}
            value={draft.registrationNumber}
            onChange={set("registrationNumber")}
          />
          <Field label={t("setup.address")} value={draft.addressLine} onChange={set("addressLine")} />
          <Field label={t("setup.city")} value={draft.city} onChange={set("city")} />
          <Field label={t("setup.state")} value={draft.state} onChange={set("state")} />
          <Field
            label={t("setup.pincode")}
            help={t("setup.pincodeHelp")}
            inputMode="numeric"
            value={draft.pincode}
            onChange={set("pincode")}
            error={errors.pincode}
          />
          <SelectField
            label={t("setup.fyStart")}
            options={months}
            value={draft.fyStartMonth}
            onChange={set("fyStartMonth")}
          />
          <BigButton type="submit">{t("setup.next")}</BigButton>
          {onCancel ? (
            <Button variant="secondary" onClick={onCancel}>
              {tc("back")}
            </Button>
          ) : null}
        </form>
      ) : null}

      {step === 2 ? (
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            if (checkStep2()) setStep(3);
          }}
        >
          <StepHeader current={2} total={3} title={t("setup.step2")} />
          <SelectField
            label={t("setup.billingFrequency")}
            options={[
              { value: "monthly", label: t("setup.monthly") },
              { value: "quarterly", label: t("setup.quarterly") },
            ]}
            value={draft.billingFrequency}
            onChange={(e) =>
              setDraft((d) => ({ ...d, billingFrequency: e.target.value === "quarterly" ? "quarterly" : "monthly" }))
            }
          />
          <Field
            label={t("setup.billDay")}
            help={t("setup.billDayHelp")}
            inputMode="numeric"
            value={draft.billDay}
            onChange={set("billDay")}
            error={errors.billDay}
          />
          <Field
            label={t("setup.dueDays")}
            inputMode="numeric"
            value={draft.dueDays}
            onChange={set("dueDays")}
            error={errors.dueDays}
          />
          <Field label={t("setup.upiId")} help={t("setup.upiHelp")} value={draft.upiId} onChange={set("upiId")} />
          <Field label={t("setup.upiPayee")} value={draft.upiPayeeName} onChange={set("upiPayeeName")} />
          <Field label={t("setup.bankName")} value={draft.bankName} onChange={set("bankName")} />
          <Field
            label={t("setup.bankLast4")}
            help={t("setup.bankLast4Help")}
            inputMode="numeric"
            value={draft.bankLast4}
            onChange={set("bankLast4")}
            error={errors.bankLast4}
          />
          <BigButton type="submit">{t("setup.next")}</BigButton>
          <Button variant="secondary" onClick={() => setStep(1)}>
            {tc("back")}
          </Button>
        </form>
      ) : null}

      {step === 3 ? (
        <div className="flex flex-col gap-4">
          <StepHeader current={3} total={3} title={t("setup.step3")} />
          <p className="text-body">{t("setup.inviteLater")}</p>
          {invites.map((inv, i) => (
            <Card key={i} className="flex flex-col gap-3">
              <Field
                label={t("invites.name")}
                value={inv.name}
                onChange={(e) => setInvites((all) => all.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))}
              />
              <Field
                label={t("invites.email")}
                type="email"
                value={inv.email}
                onChange={(e) =>
                  setInvites((all) => all.map((x, j) => (j === i ? { ...x, email: e.target.value } : x)))
                }
              />
              <Field
                label={t("invites.phone")}
                help={t("invites.phoneHelp")}
                inputMode="numeric"
                value={inv.phone}
                onChange={(e) =>
                  setInvites((all) => all.map((x, j) => (j === i ? { ...x, phone: e.target.value } : x)))
                }
              />
              <SelectField
                label={t("invites.role")}
                options={COMMITTEE_ROLES.map((r) => ({ value: r, label: tc(`roles.${r}`) }))}
                value={inv.role}
                onChange={(e) =>
                  setInvites((all) =>
                    all.map((x, j) => (j === i ? { ...x, role: e.target.value as InviteDraft["role"] } : x)),
                  )
                }
              />
              {inviteErrors[i] ? <ErrorText>{inviteErrors[i]}</ErrorText> : null}
              <Button
                variant="secondary"
                icon={<Trash2 size={20} />}
                onClick={() => setInvites((all) => all.filter((_, j) => j !== i))}
              >
                {t("invites.remove")}
              </Button>
            </Card>
          ))}
          <Button
            variant="secondary"
            icon={<Plus size={22} />}
            onClick={() => setInvites((all) => [...all, { name: "", email: "", phone: "", role: "committee" }])}
          >
            {t("invites.addPerson")}
          </Button>
          {create.isError ? <ErrorText>{tc(messageKeyOf(create.error))}</ErrorText> : null}
          <BigButton onClick={submit} disabled={create.isPending}>
            {t("setup.finish")}
          </BigButton>
          <Button variant="secondary" onClick={() => setStep(2)}>
            {tc("back")}
          </Button>
        </div>
      ) : null}
    </CenteredPage>
  );
}
