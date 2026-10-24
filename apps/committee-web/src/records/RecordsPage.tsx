// Records (docs/07 M11): download all society data, and see who changed what (audit log).
import { ChevronDown, Download, FileSpreadsheet, FileText } from "lucide-react";
import { useState } from "react";

import {
  BigButton,
  Button,
  Card,
  EmptyState,
  ErrorText,
  LoadingBlock,
  SelectField,
  messageKeyOf,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

import { useAuditLog, useCanSeeRecords, useExport, type AuditEntry } from "../api/records";

const ENTITY_TYPES = [
  "society",
  "membership",
  "flat",
  "member",
  "charge_head",
  "billing_run",
  "bill",
  "payment",
  "complaint",
  "compliance_item",
  "vendor",
];

function when(value: string, language: string): string {
  return new Intl.DateTimeFormat(language, { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Kolkata" }).format(
    new Date(value),
  );
}

function Changes({ entry }: { entry: AuditEntry }) {
  const { t } = useTranslation("committee");
  const keys = [...new Set([...Object.keys(entry.before ?? {}), ...Object.keys(entry.after ?? {})])];
  const show = (v: unknown) => (v === null || v === undefined ? "—" : typeof v === "object" ? JSON.stringify(v) : String(v));
  return (
    // Personal data and money: never in usage analytics (docs/04 §10).
    <table className="ph-no-capture mt-3 w-full text-small">
      <thead>
        <tr className="text-left">
          <th className="py-1 pr-3">{t("admin.audit.field")}</th>
          <th className="py-1 pr-3">{t("admin.audit.before")}</th>
          <th className="py-1">{t("admin.audit.after")}</th>
        </tr>
      </thead>
      <tbody>
        {keys.map((k) => {
          const before = show(entry.before?.[k]);
          const after = show(entry.after?.[k]);
          return (
            <tr key={k} className={before !== after ? "font-semibold" : "text-muted"}>
              <td className="break-all py-1 pr-3">{k}</td>
              <td className="break-all py-1 pr-3">{before}</td>
              <td className="break-all py-1">{after}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Entry({ entry }: { entry: AuditEntry }) {
  const { t } = useTranslation("committee");
  const { language } = useSettings();
  const [open, setOpen] = useState(false);
  return (
    <li className="rounded-card border border-line bg-surface p-4 shadow-card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <span>
          <span className="block font-mono text-body font-bold">{entry.action}</span>
          <span className="ph-no-capture block text-small text-muted">
            {when(entry.created_at, language)} · {entry.actor_name ?? (entry.actor_user_id ? t("admin.audit.someone") : t("admin.audit.system"))}
          </span>
          {entry.reason ? <span className="block text-small">{t("admin.audit.reason", { reason: entry.reason })}</span> : null}
        </span>
        {entry.before || entry.after ? (
          <Button variant="secondary" icon={<ChevronDown size={20} />} aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? t("admin.audit.hide") : t("admin.audit.show")}
          </Button>
        ) : null}
      </div>
      {open ? <Changes entry={entry} /> : null}
    </li>
  );
}

export function RecordsPage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const allowed = useCanSeeRecords();
  const download = useExport();
  const [entityType, setEntityType] = useState("");
  const log = useAuditLog(entityType, allowed);

  if (!allowed) return <ErrorText>{tc("errors.notAllowed")}</ErrorText>;
  const entries = log.data?.pages.flatMap((p) => p.entries) ?? [];

  return (
    <>
      <h1 className="mb-2 text-title font-bold">{t("admin.title")}</h1>
      <p className="mb-6 max-w-3xl text-body">{t("admin.body")}</p>

      <Card className="mb-8 max-w-3xl">
        <h2 className="mb-2 text-section font-bold">{t("admin.export.title")}</h2>
        <p className="mb-4 text-body">{t("admin.export.body")}</p>
        <div className="flex flex-wrap gap-3">
          <BigButton icon={<FileSpreadsheet size={24} />} disabled={download.isPending} onClick={() => download.mutate("xlsx")}>
            {t("admin.export.excel")}
          </BigButton>
          <Button variant="secondary" icon={<FileText size={22} />} disabled={download.isPending} onClick={() => download.mutate("pdf")}>
            {t("admin.export.pdf")}
          </Button>
        </div>
        {download.isPending ? (
          <p role="status" className="mt-3 text-small">
            <Download size={16} className="mr-1 inline" aria-hidden="true" />
            {t("admin.export.preparing")}
          </p>
        ) : null}
        {download.isError ? <ErrorText>{tc(messageKeyOf(download.error))}</ErrorText> : null}
      </Card>

      <h2 className="mb-3 text-section font-bold">{t("admin.audit.title")}</h2>
      <SelectField
        label={t("admin.audit.filter")}
        className="mb-4 max-w-sm"
        value={entityType}
        onChange={(e) => setEntityType(e.target.value)}
        options={[
          { value: "", label: t("admin.audit.all") },
          ...ENTITY_TYPES.map((v) => ({ value: v, label: t(`admin.entities.${v}`) })),
        ]}
      />
      {log.isPending ? <LoadingBlock /> : null}
      {log.isError ? <ErrorText>{tc(messageKeyOf(log.error))}</ErrorText> : null}
      {log.data && entries.length === 0 ? <EmptyState message={t("admin.audit.empty")} /> : null}
      <ul className="flex max-w-3xl flex-col gap-3">
        {entries.map((e) => (
          <Entry key={e.id} entry={e} />
        ))}
      </ul>
      {log.hasNextPage ? (
        <div className="mt-4">
          <Button variant="secondary" disabled={log.isFetchingNextPage} onClick={() => void log.fetchNextPage()}>
            {t("admin.audit.more")}
          </Button>
        </div>
      ) : null}
    </>
  );
}
