// Flats and members list (docs/02 §4): grouped by wing, with the main member and balance.
import { Building2, FileSpreadsheet, Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button, EmptyState, ErrorText, MoneyText, messageKeyOf, useTranslation } from "@societyiq/shared";

import { useCanManageFlats, useFlats, type FlatSummary } from "../api/flats";
import { flatLabel } from "./labels";

export function FlatsPage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const canManage = useCanManageFlats();
  const flats = useFlats();
  const [query, setQuery] = useState("");

  const groups = useMemo(() => {
    const all = flats.data ?? [];
    const wings = new Set(all.map((f) => f.wing_name)).size;
    const needle = query.trim().toLowerCase();
    const shown = all.filter(
      (f) =>
        !needle ||
        flatLabel(f, wings).toLowerCase().includes(needle) ||
        (f.primary_member ?? "").toLowerCase().includes(needle),
    );
    const byWing = new Map<string, FlatSummary[]>();
    for (const f of shown) byWing.set(f.wing_name, [...(byWing.get(f.wing_name) ?? []), f]);
    return { byWing: [...byWing.entries()], wings, total: all.length };
  }, [flats.data, query]);

  return (
    <>
      <h1 className="mb-6 text-title font-bold">{t("flats.title")}</h1>
      {canManage ? (
        <div className="mb-6 flex flex-wrap gap-3">
          <Button icon={<Plus size={22} />} onClick={() => navigate("/flats/new")}>
            {t("flats.add")}
          </Button>
          <Button variant="secondary" icon={<FileSpreadsheet size={22} />} onClick={() => navigate("/flats/import")}>
            {t("flats.import")}
          </Button>
          <Button variant="secondary" icon={<Building2 size={22} />} onClick={() => navigate("/flats/wings")}>
            {t("wings.title")}
          </Button>
        </div>
      ) : null}

      {flats.isPending ? <p role="status">{tc("loading")}</p> : null}
      {flats.isError ? <ErrorText>{tc(messageKeyOf(flats.error))}</ErrorText> : null}

      {flats.data && groups.total === 0 ? (
        <EmptyState
          message={t("flats.empty")}
          actionLabel={canManage ? t("flats.import") : undefined}
          onAction={canManage ? () => navigate("/flats/import") : undefined}
        />
      ) : null}

      {groups.total > 0 ? (
        <>
          <div className="mb-6 flex max-w-md flex-col gap-1">
            <label htmlFor="flat-search" className="text-body font-semibold">
              {t("flats.search")}
            </label>
            <div className="flex items-center gap-2 rounded-lg border-2 border-line bg-surface px-3">
              <Search size={20} aria-hidden="true" />
              <input
                id="flat-search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="min-h-[44px] flex-1 bg-transparent text-body focus-visible:outline-none"
              />
            </div>
            <p className="text-small text-muted">{t("flats.count", { count: groups.total })}</p>
          </div>
          {groups.byWing.map(([wing, list]) => (
            <section key={wing} className="mb-8">
              {groups.wings > 1 ? <h2 className="mb-3 text-section font-bold">{t("flats.wing", { name: wing })}</h2> : null}
              <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {list.map((f) => (
                  <li key={f.id}>
                    <Link
                      to={`/flats/${f.id}`}
                      className="flex min-h-[72px] items-center justify-between gap-3 rounded-card border border-line bg-surface p-4 hover:border-teal focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
                    >
                      <span className="min-w-0">
                        <span className="block text-body font-bold">{flatLabel(f, groups.wings)}</span>
                        <span className="block truncate text-small text-muted">
                          {f.primary_member ?? t("flats.noMember")}
                        </span>
                      </span>
                      <span className="shrink-0 text-right">
                        {f.balance_paise > 0 ? (
                          <>
                            <MoneyText paise={f.balance_paise} className="block text-body font-bold text-red" />
                            <span className="text-small text-muted">{t("flats.due")}</span>
                          </>
                        ) : f.balance_paise < 0 ? (
                          <>
                            <MoneyText paise={-f.balance_paise} className="block text-body font-bold" />
                            <span className="text-small text-muted">{t("flats.advance")}</span>
                          </>
                        ) : (
                          <span className="text-small text-muted">{t("flats.nothingDue")}</span>
                        )}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </>
      ) : null}
    </>
  );
}
