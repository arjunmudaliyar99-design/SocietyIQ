// Add or change a compliance item (docs/02 §13 fields). The type sets a sensible title; the
// repeat interval is whatever the society's contract or rule says, so it is never filled in.
import { ArrowLeft, Save } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  BigButton,
  Button,
  Card,
  ErrorText,
  Field,
  LoadingBlock,
  SelectField,
  messageKeyOf,
  useTranslation,
} from "@societyiq/shared";

import {
  ITEM_TYPES,
  useComplianceItem,
  useSaveItem,
  useVendors,
  type ItemDetail,
  type ItemType,
} from "../api/compliance";
import { paiseToRupeesInput, rupeesToPaise } from "../flats/labels";

interface Draft {
  itemType: ItemType;
  title: string;
  vendorId: string;
  nextDue: string;
  repeat: string;
  contract: string;
  notes: string;
}

function draftOf(item: ItemDetail | undefined): Draft {
  return {
    itemType: item?.item_type ?? "fire_audit",
    title: item?.title ?? "",
    vendorId: item?.vendor_id ?? "",
    nextDue: item?.next_due_on ?? "",
    repeat: item?.repeat_months ? String(item.repeat_months) : "",
    contract: paiseToRupeesInput(item?.contract_value_paise),
    notes: item?.notes ?? "",
  };
}

function Form({ item }: { item?: ItemDetail }) {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const vendors = useVendors();
  const save = useSaveItem();
  const [d, setD] = useState<Draft>(() => draftOf(item));
  const [problem, setProblem] = useState<string | null>(null);
  const set = (patch: Partial<Draft>) => setD((old) => ({ ...old, ...patch }));

  function submit(event: FormEvent) {
    event.preventDefault();
    const title = d.title.trim() || t(`compliance.types.${d.itemType}`);
    const repeat = d.repeat.trim() ? Number(d.repeat) : null;
    const contract = d.contract.trim() ? rupeesToPaise(d.contract) : null;
    if (!d.nextDue) return setProblem(t("compliance.form.dueRequired"));
    if (repeat !== null && (!Number.isInteger(repeat) || repeat < 1 || repeat > 120))
      return setProblem(t("compliance.form.repeatInvalid"));
    if (d.contract.trim() && contract === null) return setProblem(t("compliance.form.amountInvalid"));
    setProblem(null);
    save.mutate(
      {
        id: item?.id,
        item_type: d.itemType,
        title,
        vendor_id: d.vendorId || null,
        next_due_on: d.nextDue,
        repeat_months: repeat,
        contract_value_paise: contract,
        notes: d.notes.trim() || null,
      },
      { onSuccess: (saved) => navigate(`/compliance/${saved.id}`) },
    );
  }

  return (
    <Card className="max-w-2xl">
      <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
        <SelectField
          label={t("compliance.form.type")}
          value={d.itemType}
          onChange={(e) => set({ itemType: e.target.value as ItemType })}
          options={ITEM_TYPES.map((v) => ({ value: v, label: t(`compliance.types.${v}`) }))}
        />
        <Field
          label={t("compliance.form.title")}
          help={t("compliance.form.titleHelp")}
          value={d.title}
          placeholder={t(`compliance.types.${d.itemType}`)}
          onChange={(e) => set({ title: e.target.value })}
        />
        <SelectField
          label={t("compliance.form.vendor")}
          value={d.vendorId}
          onChange={(e) => set({ vendorId: e.target.value })}
          options={[
            { value: "", label: t("compliance.form.noVendor") },
            ...(vendors.data ?? []).map((v) => ({ value: v.id, label: v.name })),
          ]}
        />
        <Field
          label={t("compliance.form.nextDue")}
          type="date"
          value={d.nextDue}
          onChange={(e) => set({ nextDue: e.target.value })}
        />
        <Field
          label={t("compliance.form.repeat")}
          help={t("compliance.form.repeatHelp")}
          inputMode="numeric"
          value={d.repeat}
          onChange={(e) => set({ repeat: e.target.value })}
        />
        <Field
          label={t("compliance.form.contract")}
          inputMode="decimal"
          value={d.contract}
          onChange={(e) => set({ contract: e.target.value })}
        />
        <Field label={t("compliance.form.notes")} value={d.notes} onChange={(e) => set({ notes: e.target.value })} />
        {problem ? <ErrorText>{problem}</ErrorText> : null}
        {save.isError ? <ErrorText>{tc(messageKeyOf(save.error))}</ErrorText> : null}
        <BigButton type="submit" icon={<Save size={22} />} disabled={save.isPending}>
          {t("compliance.form.save")}
        </BigButton>
      </form>
    </Card>
  );
}

export function ItemFormPage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const { itemId } = useParams();
  const existing = useComplianceItem(itemId ?? "");

  return (
    <>
      <div className="mb-4">
        <Button variant="secondary" icon={<ArrowLeft size={22} />} onClick={() => navigate(itemId ? `/compliance/${itemId}` : "/compliance")}>
          {itemId ? t("compliance.back") : t("compliance.title")}
        </Button>
      </div>
      <h1 className="mb-6 text-title font-bold">{itemId ? t("compliance.edit") : t("compliance.add")}</h1>
      {!itemId ? <Form /> : null}
      {itemId && existing.isPending ? <LoadingBlock /> : null}
      {itemId && existing.isError ? <ErrorText>{tc(messageKeyOf(existing.error))}</ErrorText> : null}
      {itemId && existing.data ? <Form item={existing.data} /> : null}
    </>
  );
}
