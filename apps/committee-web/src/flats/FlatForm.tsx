// Add or edit a flat (docs/02 §4). Money typed in rupees, sent as paise.
import { useState, type FormEvent } from "react";

import { BigButton, Button, ErrorText, Field, SelectField, messageKeyOf, useTranslation } from "@societyiq/shared";

import type { FlatDetail, FlatInput, Wing } from "../api/flats";
import { OCCUPANCIES, USAGES, paiseToRupeesInput, rupeesToPaise } from "./labels";

interface Draft {
  wingId: string;
  flatNumber: string;
  carpetArea: string;
  flatType: string;
  usage: (typeof USAGES)[number];
  cost: string;
  waterPoints: string;
  municipalAccount: string;
  occupancy: (typeof OCCUPANCIES)[number];
}

function initial(wings: Wing[], flat?: FlatDetail): Draft {
  return {
    wingId: flat?.wing_id ?? wings[0]?.id ?? "",
    flatNumber: flat?.flat_number ?? "",
    carpetArea: flat?.carpet_area_sqft ?? "",
    flatType: flat?.flat_type ?? "",
    usage: flat?.usage ?? "residential",
    cost: paiseToRupeesInput(flat?.certified_construction_cost_paise),
    waterPoints: flat?.water_points ?? "",
    municipalAccount: flat?.municipal_property_account ?? "",
    occupancy: flat?.occupancy ?? "owner_occupied",
  };
}

const NUMBER = /^\d+(\.\d{1,2})?$/;

export function FlatForm({
  wings,
  flat,
  busy,
  error,
  onSave,
  onCancel,
}: {
  wings: Wing[];
  flat?: FlatDetail;
  busy: boolean;
  error: unknown;
  onSave: (body: FlatInput) => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const [draft, setDraft] = useState<Draft>(() => initial(wings, flat));
  const [errors, setErrors] = useState<Partial<Record<keyof Draft, string>>>({});
  const set = (key: keyof Draft) => (e: { target: { value: string } }) => setDraft((d) => ({ ...d, [key]: e.target.value }));

  function submit(event: FormEvent) {
    event.preventDefault();
    const e: Partial<Record<keyof Draft, string>> = {};
    if (!draft.flatNumber.trim()) e.flatNumber = t("setup.required");
    if (draft.carpetArea.trim() && !(NUMBER.test(draft.carpetArea.trim()) && Number(draft.carpetArea) > 0)) {
      e.carpetArea = t("flats.invalidArea");
    }
    const cost = draft.cost.trim() ? rupeesToPaise(draft.cost) : null;
    if (draft.cost.trim() && cost === null) e.cost = t("flats.invalidAmount");
    if (draft.waterPoints.trim() && !NUMBER.test(draft.waterPoints.trim())) e.waterPoints = t("setup.invalidNumber");
    setErrors(e);
    if (Object.keys(e).length) return;
    onSave({
      wing_id: draft.wingId,
      flat_number: draft.flatNumber.trim(),
      carpet_area_sqft: draft.carpetArea.trim() || null,
      flat_type: draft.flatType.trim() || null,
      usage: draft.usage,
      certified_construction_cost_paise: cost,
      water_points: draft.waterPoints.trim() || null,
      municipal_property_account: draft.municipalAccount.trim() || null,
      occupancy: draft.occupancy,
    });
  }

  return (
    <form className="flex max-w-xl flex-col gap-4" onSubmit={submit} noValidate>
      {wings.length > 1 ? (
        <SelectField
          label={t("flats.fields.wing")}
          options={wings.map((w) => ({ value: w.id, label: w.name }))}
          value={draft.wingId}
          onChange={set("wingId")}
        />
      ) : null}
      <Field label={t("flats.fields.flatNumber")} value={draft.flatNumber} onChange={set("flatNumber")} error={errors.flatNumber} />
      <Field
        label={t("flats.fields.carpetArea")}
        help={t("flats.fields.carpetAreaHelp")}
        inputMode="decimal"
        value={draft.carpetArea}
        onChange={set("carpetArea")}
        error={errors.carpetArea}
      />
      <Field label={t("flats.fields.flatType")} help={t("flats.fields.flatTypeHelp")} value={draft.flatType} onChange={set("flatType")} />
      <SelectField
        label={t("flats.fields.occupancy")}
        options={OCCUPANCIES.map((o) => ({ value: o, label: t(`flats.occupancy.${o}`) }))}
        value={draft.occupancy}
        onChange={set("occupancy")}
      />
      <SelectField
        label={t("flats.fields.usage")}
        options={USAGES.map((u) => ({ value: u, label: t(`flats.usage.${u}`) }))}
        value={draft.usage}
        onChange={set("usage")}
      />
      <Field
        label={t("flats.fields.cost")}
        help={t("flats.fields.costHelp")}
        inputMode="decimal"
        value={draft.cost}
        onChange={set("cost")}
        error={errors.cost}
      />
      <Field
        label={t("flats.fields.waterPoints")}
        inputMode="decimal"
        value={draft.waterPoints}
        onChange={set("waterPoints")}
        error={errors.waterPoints}
      />
      <Field label={t("flats.fields.municipalAccount")} value={draft.municipalAccount} onChange={set("municipalAccount")} />
      {error ? <ErrorText>{tc(messageKeyOf(error))}</ErrorText> : null}
      <BigButton type="submit" disabled={busy}>
        {t("flats.save")}
      </BigButton>
      <Button variant="secondary" onClick={onCancel}>
        {tc("back")}
      </Button>
    </form>
  );
}
