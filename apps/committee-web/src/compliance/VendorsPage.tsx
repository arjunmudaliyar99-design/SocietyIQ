// Vendors the society deals with (docs/05 §6): name and how to reach them.
import { ArrowLeft, Plus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import {
  BigButton,
  Button,
  Card,
  EmptyState,
  ErrorText,
  Field,
  LoadingBlock,
  messageKeyOf,
  useTranslation,
} from "@societyiq/shared";

import { useCanManageCompliance, useSaveVendor, useVendors } from "../api/compliance";

export function VendorsPage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const vendors = useVendors();
  const save = useSaveVendor();
  const canManage = useCanManageCompliance();
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [phone, setPhone] = useState("");
  const [problem, setProblem] = useState<string | null>(null);

  function add(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return setProblem(t("setup.required"));
    const digits = phone.replace(/[\s-]/g, "");
    // Indian mobile numbers typed without +91 are the common case.
    const e164 = !digits ? null : digits.startsWith("+") ? digits : /^\d{10}$/.test(digits) ? `+91${digits}` : null;
    if (digits && !e164) return setProblem(t("compliance.vendors.phoneInvalid"));
    setProblem(null);
    save.mutate(
      { name: name.trim(), category: category.trim() || null, phone_e164: e164 },
      {
        onSuccess: () => {
          setName("");
          setCategory("");
          setPhone("");
        },
      },
    );
  }

  return (
    <>
      <div className="mb-4">
        <Button variant="secondary" icon={<ArrowLeft size={22} />} onClick={() => navigate("/compliance")}>
          {t("compliance.title")}
        </Button>
      </div>
      <h1 className="mb-6 text-title font-bold">{t("compliance.vendors.title")}</h1>
      {vendors.isPending ? <LoadingBlock /> : null}
      {vendors.isError ? <ErrorText>{tc(messageKeyOf(vendors.error))}</ErrorText> : null}
      {vendors.data && vendors.data.length === 0 ? <EmptyState message={t("compliance.vendors.empty")} /> : null}
      <ul className="mb-8 flex max-w-2xl flex-col gap-3">
        {vendors.data?.map((v) => (
          <li key={v.id}>
            <Card>
              <span className="block text-body font-bold">{v.name}</span>
              <span className="block text-small text-muted">
                {[v.category, v.phone_e164, v.email].filter(Boolean).join(" · ") || t("compliance.vendors.noDetails")}
              </span>
            </Card>
          </li>
        ))}
      </ul>
      {canManage ? (
        <Card className="max-w-2xl">
          <form className="flex flex-col gap-4" onSubmit={add} noValidate>
            <h2 className="text-section font-bold">{t("compliance.vendors.add")}</h2>
            <Field label={t("compliance.vendors.name")} value={name} onChange={(e) => setName(e.target.value)} />
            <Field label={t("compliance.vendors.category")} value={category} onChange={(e) => setCategory(e.target.value)} />
            <Field label={t("compliance.vendors.phone")} type="tel" inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} />
            {problem ? <ErrorText>{problem}</ErrorText> : null}
            {save.isError ? <ErrorText>{tc(messageKeyOf(save.error))}</ErrorText> : null}
            <BigButton type="submit" icon={<Plus size={22} />} disabled={save.isPending}>
              {t("compliance.vendors.add")}
            </BigButton>
          </form>
        </Card>
      ) : null}
    </>
  );
}
