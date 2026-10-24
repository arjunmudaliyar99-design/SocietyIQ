// One compliance item: when it is due, mark it done (docs/06 §9 sets the next due date), history.
import { ArrowLeft, CircleCheck, Pencil } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  BigButton,
  Button,
  Card,
  ConfirmDialog,
  ErrorText,
  Field,
  LoadingBlock,
  MoneyText,
  formatDate,
  messageKeyOf,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

import { useCanManageCompliance, useComplianceItem, useMarkDone } from "../api/compliance";
import { ComplianceStatus } from "./ComplianceStatus";
import { dueText } from "./due-text";

function localToday(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function MarkDone({ itemId, title }: { itemId: string; title: string }) {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const { language } = useSettings();
  const done = useMarkDone(itemId);
  const [doneOn, setDoneOn] = useState(localToday);
  const [notes, setNotes] = useState("");
  const [asking, setAsking] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!doneOn) return setProblem(t("compliance.form.dateRequired"));
    if (doneOn > localToday()) return setProblem(tc("errors.doneInFuture"));
    setProblem(null);
    setAsking(true);
  }

  return (
    <Card className="mb-6 max-w-2xl">
      <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
        <h2 className="text-section font-bold">{t("compliance.markDone")}</h2>
        <Field label={t("compliance.doneDate")} type="date" value={doneOn} max={localToday()} onChange={(e) => setDoneOn(e.target.value)} />
        <Field label={t("compliance.form.notes")} value={notes} onChange={(e) => setNotes(e.target.value)} />
        {problem ? <ErrorText>{problem}</ErrorText> : null}
        {done.isError ? <ErrorText>{tc(messageKeyOf(done.error))}</ErrorText> : null}
        <BigButton type="submit" icon={<CircleCheck size={22} />} disabled={done.isPending}>
          {t("compliance.markDone")}
        </BigButton>
      </form>
      <ConfirmDialog
        open={asking}
        question={t("compliance.markDoneQuestion", { title, date: formatDate(doneOn, language) })}
        confirmLabel={t("compliance.markDone")}
        onCancel={() => setAsking(false)}
        onConfirm={() => {
          setAsking(false);
          done.mutate({ done_on: doneOn, notes: notes.trim() || null }, { onSuccess: () => setNotes("") });
        }}
      />
    </Card>
  );
}

export function ItemPage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const { language } = useSettings();
  const navigate = useNavigate();
  const { itemId = "" } = useParams();
  const item = useComplianceItem(itemId);
  const canManage = useCanManageCompliance();
  const i = item.data;

  return (
    <>
      <div className="mb-4">
        <Button variant="secondary" icon={<ArrowLeft size={22} />} onClick={() => navigate("/compliance")}>
          {t("compliance.title")}
        </Button>
      </div>
      {item.isPending ? <LoadingBlock /> : null}
      {item.isError ? <ErrorText>{tc(messageKeyOf(item.error))}</ErrorText> : null}
      {i ? (
        <>
          <div className="mb-6 flex flex-wrap items-center gap-3">
            <h1 className="text-title font-bold">{i.title}</h1>
            <ComplianceStatus status={i.status} />
          </div>
          <Card className="mb-6 max-w-2xl">
            <dl className="grid gap-x-6 gap-y-3 text-body sm:grid-cols-[max-content_1fr]">
              <dt className="font-semibold">{t("compliance.form.type")}</dt>
              <dd>{t(`compliance.types.${i.item_type}`)}</dd>
              <dt className="font-semibold">{t("compliance.form.nextDue")}</dt>
              <dd>
                {formatDate(i.next_due_on, language)} · {dueText(i, t, language)}
              </dd>
              <dt className="font-semibold">{t("compliance.lastDone")}</dt>
              <dd>{i.last_done_on ? formatDate(i.last_done_on, language) : t("compliance.never")}</dd>
              <dt className="font-semibold">{t("compliance.form.repeat")}</dt>
              <dd>{i.repeat_months ? t("compliance.everyMonths", { count: i.repeat_months }) : t("compliance.noRepeat")}</dd>
              <dt className="font-semibold">{t("compliance.form.vendor")}</dt>
              <dd>{i.vendor_name ?? t("compliance.form.noVendor")}</dd>
              {i.contract_value_paise !== null ? (
                <>
                  <dt className="font-semibold">{t("compliance.form.contract")}</dt>
                  <dd>
                    <MoneyText paise={i.contract_value_paise} />
                  </dd>
                </>
              ) : null}
              {i.notes ? (
                <>
                  <dt className="font-semibold">{t("compliance.form.notes")}</dt>
                  <dd>{i.notes}</dd>
                </>
              ) : null}
            </dl>
          </Card>
          {canManage && i.is_active ? (
            <>
              <MarkDone itemId={i.id} title={i.title} />
              <div className="mb-8">
                <Button variant="secondary" icon={<Pencil size={22} />} onClick={() => navigate(`/compliance/${i.id}/edit`)}>
                  {t("compliance.edit")}
                </Button>
              </div>
            </>
          ) : null}
          <h2 className="mb-3 text-section font-bold">{t("compliance.history")}</h2>
          {i.events.length === 0 ? (
            <p className="text-body">{t("compliance.noHistory")}</p>
          ) : (
            <ul className="flex max-w-2xl flex-col gap-2">
              {i.events.map((e) => (
                <li key={e.id} className="rounded-card border border-line bg-surface p-4 text-body">
                  <span className="font-semibold">{formatDate(e.done_on, language)}</span>
                  {e.notes ? ` · ${e.notes}` : ""}
                </li>
              ))}
            </ul>
          )}
        </>
      ) : null}
    </>
  );
}
