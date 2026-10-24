// Excel import (docs/02 §4): download template → upload → check every row → confirm.
// Never import silently: nothing is saved until the person confirms.
import { CircleAlert, CircleCheck, Download, TriangleAlert, Upload } from "lucide-react";
import { useId, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  BigButton,
  Button,
  Card,
  ConfirmDialog,
  ErrorText,
  MoneyText,
  StatCard,
  StepHeader,
  messageKeyOf,
  useTranslation,
} from "@societyiq/shared";

import { useConfirmImport, useDownloadTemplate, useUploadImport, type ImportJob, type ImportRow } from "../api/flats";

const STATUS_ORDER = { error: 0, warning: 1, ok: 2 } as const;

function useIssueText() {
  const { t } = useTranslation("committee");
  return (issue: ImportRow["issues"][number]) => {
    const params = { ...issue.params } as Record<string, string | number | null>;
    if (typeof params.field === "string") params.field = t(`import.fields.${params.field}`);
    return t(`import.issues.${issue.key}`, params);
  };
}

function RowLine({ row }: { row: ImportRow }) {
  const { t } = useTranslation("committee");
  const issueText = useIssueText();
  const icon =
    row.status === "error" ? (
      <CircleAlert size={22} className="text-red" />
    ) : row.status === "warning" ? (
      <TriangleAlert size={22} className="text-terracotta" />
    ) : (
      <CircleCheck size={22} className="text-green" />
    );
  const flat = [row.wing, row.flat_number].filter(Boolean).join("-");
  return (
    <li className="flex gap-3 border-b border-line py-3 last:border-b-0">
      <span aria-hidden="true" className="pt-1">
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-body font-semibold">
          {t("import.rowTitle", { row: row.row, status: t(`import.status.${row.status}`) })}
          {flat ? ` · ${flat}` : ""}
          {row.owner_name ? ` · ${row.owner_name}` : ""}
        </p>
        {row.issues.length ? (
          <ul className="text-body">
            {row.issues.map((issue, i) => (
              <li key={i}>{issueText(issue)}</li>
            ))}
          </ul>
        ) : null}
      </div>
      {row.opening_balance_paise ? (
        <MoneyText paise={row.opening_balance_paise} className="shrink-0 text-body" />
      ) : null}
    </li>
  );
}

function Preview({ job, onReupload }: { job: ImportJob; onReupload: () => void }) {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const confirm = useConfirmImport();
  const [asking, setAsking] = useState(false);
  const result = confirm.data;
  const shown = result ?? job;
  const rows = [...shown.rows].sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status] || a.row - b.row);
  const count = (s: ImportRow["status"]) => shown.rows.filter((r) => r.status === s).length;

  return (
    <section className="flex flex-col gap-4">
      {result ? (
        <Card className="border-2 border-green">
          <p className="text-section font-bold">{t("import.done", { count: result.ok_count })}</p>
          {result.error_count ? <p className="text-body">{t("import.skipped", { count: result.error_count })}</p> : null}
          <div className="mt-4">
            <BigButton onClick={() => navigate("/flats")}>{t("import.seeFlats")}</BigButton>
          </div>
        </Card>
      ) : (
        <StepHeader current={3} total={3} title={t("import.step3")} />
      )}
      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label={t("import.status.ok")} value={count("ok")} />
        <StatCard label={t("import.status.warning")} value={count("warning")} note={t("import.warningNote")} />
        <StatCard label={t("import.status.error")} value={count("error")} note={t("import.errorNote")} />
      </div>
      <Card>
        <ul>
          {rows.map((r) => (
            <RowLine key={r.row} row={r} />
          ))}
        </ul>
      </Card>
      {!result ? (
        <div className="flex flex-wrap gap-3">
          {job.ok_count > 0 ? (
            <BigButton onClick={() => setAsking(true)} disabled={confirm.isPending}>
              {t("import.confirm", { count: job.ok_count })}
            </BigButton>
          ) : null}
          <Button variant="secondary" icon={<Upload size={22} />} onClick={onReupload}>
            {t("import.reupload")}
          </Button>
        </div>
      ) : null}
      {confirm.isError ? <ErrorText>{tc(messageKeyOf(confirm.error))}</ErrorText> : null}
      <ConfirmDialog
        open={asking}
        question={t("import.confirmQuestion", { count: job.ok_count, skipped: job.error_count })}
        confirmLabel={t("import.confirmYes")}
        onCancel={() => setAsking(false)}
        onConfirm={() => {
          setAsking(false);
          confirm.mutate(job.id);
        }}
      />
    </section>
  );
}

export function ImportPage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const download = useDownloadTemplate();
  const upload = useUploadImport();
  const inputId = useId();
  const input = useRef<HTMLInputElement>(null);
  const [job, setJob] = useState<ImportJob | null>(null);

  function reupload() {
    setJob(null);
    upload.reset();
    input.current?.click();
  }

  return (
    <>
      <h1 className="mb-2 text-title font-bold">{t("import.title")}</h1>
      <p className="mb-6 text-body">{t("import.body")}</p>
      {job ? (
        <Preview job={job} onReupload={reupload} />
      ) : (
        <div className="flex max-w-2xl flex-col gap-6">
          <Card>
            <StepHeader current={1} total={3} title={t("import.step1")} />
            <p className="mb-4 text-body">{t("import.step1Body")}</p>
            <Button variant="secondary" icon={<Download size={22} />} onClick={() => download.mutate()} disabled={download.isPending}>
              {t("import.download")}
            </Button>
            {download.isError ? <ErrorText>{tc(messageKeyOf(download.error))}</ErrorText> : null}
          </Card>
          <Card>
            <StepHeader current={2} total={3} title={t("import.step2")} />
            <p className="mb-4 text-body">{t("import.step2Body")}</p>
            <BigButton icon={<Upload size={24} />} onClick={() => input.current?.click()} disabled={upload.isPending}>
              {upload.isPending ? t("import.checking") : t("import.choose")}
            </BigButton>
            {upload.isError ? (
              <div className="mt-3">
                <ErrorText>{tc(messageKeyOf(upload.error))}</ErrorText>
              </div>
            ) : null}
          </Card>
        </div>
      )}
      <input
        id={inputId}
        aria-label={t("import.choose")}
        ref={input}
        type="file"
        accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          e.target.value = "";
          if (file) upload.mutate(file, { onSuccess: setJob });
        }}
      />
    </>
  );
}
