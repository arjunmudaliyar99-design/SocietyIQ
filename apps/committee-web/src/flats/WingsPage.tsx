// Wings and lifts (docs/02 §4): lift charges are shared only by flats in wings with a lift.
import { ArrowLeft, Plus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { BigButton, Button, Card, ErrorText, Field, messageKeyOf, useTranslation } from "@societyiq/shared";

import { useCanManageFlats, useSaveWing, useWings } from "../api/flats";

export function WingsPage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const wings = useWings();
  const save = useSaveWing();
  const canManage = useCanManageFlats();
  const [name, setName] = useState("");
  const [lift, setLift] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  function add(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return setProblem(t("setup.required"));
    setProblem(null);
    save.mutate(
      { name: name.trim(), has_lift: lift },
      {
        onSuccess: () => {
          setName("");
          setLift(false);
        },
      },
    );
  }

  return (
    <>
      <div className="mb-4">
        <Button variant="secondary" icon={<ArrowLeft size={22} />} onClick={() => navigate("/flats")}>
          {t("flats.title")}
        </Button>
      </div>
      <h1 className="mb-2 text-title font-bold">{t("wings.title")}</h1>
      <p className="mb-6 text-body">{t("wings.body")}</p>
      {wings.isPending ? <p role="status">{tc("loading")}</p> : null}
      {wings.isError ? <ErrorText>{tc(messageKeyOf(wings.error))}</ErrorText> : null}
      <ul className="mb-8 flex max-w-xl flex-col gap-3">
        {wings.data?.map((w) => (
          <li key={w.id}>
            <Card className="flex flex-wrap items-center justify-between gap-3">
              <span className="text-body font-bold">{t("flats.wing", { name: w.name })}</span>
              <span className="flex items-center gap-3">
                <span className="text-body">{w.has_lift ? t("wings.hasLift") : t("wings.noLift")}</span>
                {canManage ? (
                  <Button variant="secondary" onClick={() => save.mutate({ id: w.id, has_lift: !w.has_lift })}>
                    {w.has_lift ? t("wings.markNoLift") : t("wings.markLift")}
                  </Button>
                ) : null}
              </span>
            </Card>
          </li>
        ))}
      </ul>
      {canManage ? (
        <Card className="max-w-xl">
          <form className="flex flex-col gap-4" onSubmit={add} noValidate>
            <h2 className="text-section font-bold">{t("wings.add")}</h2>
            <Field label={t("wings.name")} help={t("wings.nameHelp")} value={name} onChange={(e) => setName(e.target.value)} />
            <label className="flex items-center gap-3 text-body">
              <input type="checkbox" checked={lift} onChange={(e) => setLift(e.target.checked)} className="h-7 w-7 accent-teal" />
              {t("wings.hasLift")}
            </label>
            {problem ? <ErrorText>{problem}</ErrorText> : null}
            {save.isError ? <ErrorText>{tc(messageKeyOf(save.error))}</ErrorText> : null}
            <BigButton type="submit" icon={<Plus size={22} />} disabled={save.isPending}>
              {t("wings.add")}
            </BigButton>
          </form>
        </Card>
      ) : null}
    </>
  );
}
