import { useNavigate } from "react-router-dom";

import { ErrorText, messageKeyOf, useTranslation } from "@societyiq/shared";

import { useCreateFlat, useWings } from "../api/flats";
import { FlatForm } from "./FlatForm";

export function NewFlatPage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const wings = useWings();
  const create = useCreateFlat();

  if (wings.isPending) return <p role="status">{tc("loading")}</p>;
  if (wings.isError) return <ErrorText>{tc(messageKeyOf(wings.error))}</ErrorText>;
  return (
    <>
      <h1 className="mb-6 text-title font-bold">{t("flats.add")}</h1>
      <FlatForm
        wings={wings.data}
        busy={create.isPending}
        error={create.error}
        onCancel={() => navigate("/flats")}
        onSave={(body) => create.mutate(body, { onSuccess: (flat) => navigate(`/flats/${flat.id}`) })}
      />
    </>
  );
}
