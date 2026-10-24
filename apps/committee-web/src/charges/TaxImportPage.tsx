// Property tax from Excel (docs/02 §5): copy each flat's amount from the municipal bill.
import { CircleAlert, CircleCheck, Download, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { BigButton, Button, Card, ErrorText, MoneyText, StepHeader, messageKeyOf, useTranslation } from "@societyiq/shared";

import { useConfirmTax, useTaxTemplate, useUploadTax, type TaxImport } from "../api/charges";

export function TaxImportPage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const template = useTaxTemplate();
  const upload = useUploadTax();
  const confirm = useConfirmTax();
  const input = useRef<HTMLInputElement>(null);
  const [job, setJob] = useState<TaxImport | null>(null);
  const shown = confirm.data ?? job;

  function issueText(issue: { key: string; params: Record<string, string | number | null> }) {
    const params = { ...issue.params };
    if (typeof params.field === "string") params.field = t(`import.fields.${params.field}`);
    return t(`import.issues.${issue.key}`, params);
  }

  return (
    <>
      <h1 className="mb-2 text-title font-bold">{t("taxImport.title")}</h1>
      <p className="mb-6 max-w-3xl text-body">{t("taxImport.body")}</p>
      {!shown ? (
        <div className="flex max-w-2xl flex-col gap-6">
          <Card>
            <StepHeader current={1} total={3} title={t("import.step1")} />
            <Button variant="secondary" icon={<Download size={22} />} onClick={() => template.mutate()}>
              {t("import.download")}
            </Button>
          </Card>
          <Card>
            <StepHeader current={2} total={3} title={t("import.step2")} />
            <BigButton icon={<Upload size={24} />} onClick={() => input.current?.click()} disabled={upload.isPending}>
              {upload.isPending ? t("import.checking") : t("import.choose")}
            </BigButton>
            {upload.isError ? <ErrorText>{tc(messageKeyOf(upload.error))}</ErrorText> : null}
          </Card>
        </div>
      ) : (
        <section className="flex flex-col gap-4">
          {confirm.data ? (
            <Card className="border-2 border-green">
              <p className="text-section font-bold">{t("taxImport.done", { count: confirm.data.ok_count })}</p>
              <div className="mt-4">
                <BigButton onClick={() => navigate("/charges/preview")}>{t("charges.preview")}</BigButton>
              </div>
            </Card>
          ) : (
            <StepHeader current={3} total={3} title={t("import.step3")} />
          )}
          <Card>
            <ul>
              {shown.rows.map((r) => (
                <li key={r.row} className="flex gap-3 border-b border-line py-3 last:border-b-0">
                  <span aria-hidden="true">
                    {r.status === "ok" ? <CircleCheck size={22} className="text-green" /> : <CircleAlert size={22} className="text-red" />}
                  </span>
                  <div className="flex-1">
                    <p className="text-body font-semibold">
                      {t("import.rowTitle", { row: r.row, status: t(`import.status.${r.status}`) })} · {r.flat_label} · {r.financial_year}
                    </p>
                    {r.issues.map((i, n) => (
                      <p key={n} className="text-body">
                        {issueText(i)}
                      </p>
                    ))}
                  </div>
                  <span className="shrink-0 text-body">
                    {r.is_exempt ? t("taxImport.exempt") : <MoneyText paise={r.annual_amount_paise} />}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
          {!confirm.data ? (
            <div className="flex flex-wrap gap-3">
              {shown.ok_count > 0 ? (
                <BigButton onClick={() => confirm.mutate(shown.id)} disabled={confirm.isPending}>
                  {t("taxImport.confirm", { count: shown.ok_count })}
                </BigButton>
              ) : null}
              <Button
                variant="secondary"
                icon={<Upload size={22} />}
                onClick={() => {
                  setJob(null);
                  upload.reset();
                  input.current?.click();
                }}
              >
                {t("import.reupload")}
              </Button>
            </div>
          ) : null}
          {confirm.isError ? <ErrorText>{tc(messageKeyOf(confirm.error))}</ErrorText> : null}
        </section>
      )}
      <input
        ref={input}
        type="file"
        aria-label={t("import.choose")}
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
