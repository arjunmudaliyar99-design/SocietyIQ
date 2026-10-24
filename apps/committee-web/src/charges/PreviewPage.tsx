// What each flat will be charged for a period (docs/07 M4 task 5), before any bill exists.
// Every amount comes from the backend's calculation; this screen does no arithmetic.
import { TriangleAlert } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Card, ErrorText, Field, MoneyText, StatCard, messageKeyOf, useTranslation } from "@societyiq/shared";

import { useChargesPreview } from "../api/charges";

function nextMonthStart(): string {
  const now = new Date();
  const next = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  return `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}`;
}

export function PreviewPage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const [month, setMonth] = useState(nextMonthStart);
  const [query, setQuery] = useState("");
  const preview = useChargesPreview(`${month}-01`);

  const flats = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return (preview.data?.flats ?? []).filter((f) => !needle || f.label.toLowerCase().includes(needle));
  }, [preview.data, query]);

  const missing = preview.data?.missing ?? {};
  const missingLines = Object.entries(missing).filter(([, count]) => count > 0);

  return (
    <>
      <h1 className="mb-2 text-title font-bold">{t("charges.preview")}</h1>
      <p className="mb-6 max-w-3xl text-body">{t("preview.body")}</p>
      <div className="mb-6 flex flex-wrap gap-4">
        <Field
          label={t("preview.month")}
          type="month"
          value={month}
          onChange={(e) => e.target.value && setMonth(e.target.value)}
          className="w-64"
        />
        <Field label={t("flats.search")} value={query} onChange={(e) => setQuery(e.target.value)} className="w-64" />
      </div>

      {preview.isPending ? <p role="status">{tc("loading")}</p> : null}
      {preview.isError ? <ErrorText>{tc(messageKeyOf(preview.error))}</ErrorText> : null}
      {preview.data ? (
        <div className="flex flex-col gap-6">
          <div className="grid gap-3 sm:grid-cols-3">
            <StatCard label={t("preview.total")} value={<MoneyText paise={preview.data.total_paise} />} />
            <StatCard label={t("preview.flatsBilled")} value={preview.data.flats.length} />
            <StatCard label={t("preview.flatsLeftOut")} value={preview.data.excluded.length} note={t("preview.leftOutNote")} />
          </div>

          {missingLines.length ? (
            <Card className="border-2 border-terracotta">
              <h2 className="mb-2 flex items-center gap-2 text-section font-bold">
                <TriangleAlert size={22} aria-hidden="true" className="text-terracotta" />
                {t("preview.missingTitle")}
              </h2>
              <ul className="list-disc pl-6 text-body">
                {missingLines.map(([key, count]) => (
                  <li key={key}>{t(`preview.missing.${key}`, { count })}</li>
                ))}
              </ul>
              <p className="mt-2 text-small text-muted">
                <Link to="/flats" className="underline">
                  {t("flats.title")}
                </Link>
              </p>
            </Card>
          ) : null}

          {preview.data.excluded.length ? (
            <Card>
              <h2 className="mb-2 text-section font-bold">{t("preview.leftOutTitle")}</h2>
              <ul className="text-body">
                {preview.data.excluded.map((f) => (
                  <li key={f.flat_id}>
                    <Link to={`/flats/${f.flat_id}`} className="font-semibold underline">
                      {f.label}
                    </Link>
                    : {f.reasons.map((r) => t(`preview.reasons.${r}`)).join(", ")}
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}

          {preview.data.heads.length === 0 ? (
            <p className="text-body">{t("charges.empty")}</p>
          ) : (
            <div className="overflow-x-auto rounded-card border border-line bg-surface">
              <table className="min-w-full text-body">
                <caption className="sr-only">{t("charges.preview")}</caption>
                <thead>
                  <tr className="border-b border-line text-left">
                    <th scope="col" className="p-3">
                      {t("preview.flat")}
                    </th>
                    {preview.data.heads.map((h) => (
                      <th key={h.id} scope="col" className="p-3 text-right">
                        {h.name}
                      </th>
                    ))}
                    <th scope="col" className="p-3 text-right">
                      {t("preview.rounding")}
                    </th>
                    <th scope="col" className="p-3 text-right">
                      {t("preview.flatTotal")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {flats.map((f) => (
                    <tr key={f.flat_id} className="border-b border-line last:border-b-0">
                      <th scope="row" className="p-3 text-left font-semibold">
                        <Link to={`/flats/${f.flat_id}`} className="underline">
                          {f.label}
                        </Link>
                        {f.overridden.length ? <span className="block text-small text-muted">{t("preview.hasOverride")}</span> : null}
                        {f.warnings.length ? (
                          <span className="block text-small text-terracotta">
                            {f.warnings.map((w) => t(`preview.reasons.${w}`)).join(", ")}
                          </span>
                        ) : null}
                      </th>
                      {preview.data.heads.map((h) => (
                        <td key={h.id} className="p-3 text-right">
                          <MoneyText paise={f.lines[h.id] ?? 0} />
                        </td>
                      ))}
                      <td className="p-3 text-right">
                        <MoneyText paise={f.rounding_paise} />
                      </td>
                      <td className="p-3 text-right font-bold">
                        <MoneyText paise={f.total_paise} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : null}
    </>
  );
}
