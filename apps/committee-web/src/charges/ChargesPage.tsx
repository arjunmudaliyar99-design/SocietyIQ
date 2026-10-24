// Charge setup (docs/02 §5): the heads on every bill, how each is split, and links to the
// preview, billing settings and property tax import.
import { Calculator, FileSpreadsheet, Pencil, Plus, Settings2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button, Card, EmptyState, ErrorText, MoneyText, messageKeyOf, useCurrentSociety, useTranslation } from "@societyiq/shared";

import { useChargeHeads, type ChargeHead } from "../api/charges";
import { useCanManageFlats } from "../api/flats";

function Amount({ head }: { head: ChargeHead }) {
  const { t } = useTranslation("committee");
  if (head.period_total_paise !== null && head.period_total_paise !== undefined) {
    return (
      <>
        <MoneyText paise={head.period_total_paise} /> {t("charges.perPeriod")}
      </>
    );
  }
  if (head.percent !== null && head.percent !== undefined) {
    return <>{t("charges.percentValue", { value: Number(head.percent) })}</>;
  }
  if (head.fixed_amount_paise !== null && head.fixed_amount_paise !== undefined) {
    return <MoneyText paise={head.fixed_amount_paise} />;
  }
  return <>{t("charges.perFlatAmounts")}</>;
}

export function ChargesPage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const heads = useChargeHeads();
  const canManage = useCanManageFlats();
  const isAdmin = Boolean(useCurrentSociety()?.society.roles.includes("admin"));

  const active = heads.data?.filter((h) => h.is_active) ?? [];
  const inactive = heads.data?.filter((h) => !h.is_active) ?? [];

  return (
    <>
      <h1 className="mb-2 text-title font-bold">{t("charges.title")}</h1>
      <p className="mb-6 max-w-3xl text-body">{t("charges.body")}</p>
      <div className="mb-6 flex flex-wrap gap-3">
        {canManage ? (
          <Button icon={<Plus size={22} />} onClick={() => navigate("/charges/new")}>
            {t("charges.add")}
          </Button>
        ) : null}
        <Button variant="secondary" icon={<Calculator size={22} />} onClick={() => navigate("/charges/preview")}>
          {t("charges.preview")}
        </Button>
        {isAdmin ? (
          <Button variant="secondary" icon={<Settings2 size={22} />} onClick={() => navigate("/charges/settings")}>
            {t("billingSettings.title")}
          </Button>
        ) : null}
        {canManage ? (
          <Button variant="secondary" icon={<FileSpreadsheet size={22} />} onClick={() => navigate("/charges/property-tax")}>
            {t("taxImport.title")}
          </Button>
        ) : null}
      </div>

      {heads.isPending ? <p role="status">{tc("loading")}</p> : null}
      {heads.isError ? <ErrorText>{tc(messageKeyOf(heads.error))}</ErrorText> : null}
      {heads.data && active.length === 0 ? (
        <EmptyState
          message={t("charges.empty")}
          actionLabel={canManage ? t("charges.add") : undefined}
          onAction={canManage ? () => navigate("/charges/new") : undefined}
        />
      ) : null}

      <ul className="flex max-w-3xl flex-col gap-3">
        {[...active, ...inactive].map((h) => (
          <li key={h.id}>
            <Card className={`flex flex-wrap items-center justify-between gap-3 ${h.is_active ? "" : "opacity-70"}`}>
              <div className="min-w-0">
                <p className="text-body font-bold">
                  {h.name}
                  {h.is_active ? "" : ` · ${t("charges.stopped")}`}
                </p>
                <p className="text-small text-muted">{t(`charges.method.${h.calc_type}`)}</p>
                <p className="text-body">
                  <Amount head={h} />
                </p>
                {h.method_deviation_reason ? (
                  <p className="text-small text-terracotta">{t("charges.deviationNote", { reason: h.method_deviation_reason })}</p>
                ) : null}
              </div>
              {canManage ? (
                <Button variant="secondary" icon={<Pencil size={20} />} onClick={() => navigate(`/charges/${h.id}`)}>
                  {t("charges.change")}
                </Button>
              ) : null}
            </Card>
          </li>
        ))}
      </ul>
    </>
  );
}
