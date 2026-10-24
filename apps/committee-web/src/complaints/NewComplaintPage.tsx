// Raise a complaint on behalf of a resident without a phone (docs/02 §8).
import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button, ComplaintForm, useTranslation } from "@societyiq/shared";

import { useFlats } from "../api/flats";
import { flatLabel } from "../flats/labels";

export function NewComplaintPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const flats = useFlats();
  const all = flats.data ?? [];
  const wings = new Set(all.map((f) => f.wing_name)).size;
  const options = all.map((f) => ({ value: f.id, label: flatLabel(f, wings) }));

  return (
    <div className="max-w-2xl">
      <div className="mb-4">
        <Button variant="secondary" icon={<ArrowLeft size={22} />} onClick={() => navigate("/complaints")}>
          {t("complaints.back")}
        </Button>
      </div>
      <h1 className="mb-2 text-title font-bold">{t("complaints.newTitle")}</h1>
      <p className="mb-6 text-body">{t("complaints.onBehalfNote")}</p>
      {flats.isPending ? (
        <p role="status">{t("loading")}</p>
      ) : (
        <ComplaintForm flats={options} onDone={(c) => navigate(`/complaints/${c.id}`)} />
      )}
    </div>
  );
}
