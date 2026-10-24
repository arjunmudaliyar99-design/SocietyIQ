// Compliance and AMC tracker (docs/02 §13): overdue first, then due soon, then the rest.
import { Plus, Truck } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import {
  BigButton,
  Button,
  EmptyState,
  ErrorText,
  LoadingBlock,
  messageKeyOf,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

import { useCanManageCompliance, useComplianceItems } from "../api/compliance";
import { ComplianceStatus } from "./ComplianceStatus";
import { dueText } from "./due-text";

export function CompliancePage() {
  const { t } = useTranslation("committee");
  const { t: tc } = useTranslation();
  const { language } = useSettings();
  const navigate = useNavigate();
  const items = useComplianceItems();
  const canManage = useCanManageCompliance();

  return (
    <>
      <h1 className="mb-2 text-title font-bold">{t("compliance.title")}</h1>
      <p className="mb-6 max-w-3xl text-body">{t("compliance.body")}</p>
      <div className="mb-6 flex flex-wrap gap-3">
        {canManage ? (
          <BigButton icon={<Plus size={24} />} onClick={() => navigate("/compliance/new")}>
            {t("compliance.add")}
          </BigButton>
        ) : null}
        <Button variant="secondary" icon={<Truck size={22} />} onClick={() => navigate("/compliance/vendors")}>
          {t("compliance.vendors.title")}
        </Button>
      </div>

      {items.isPending ? <LoadingBlock /> : null}
      {items.isError ? <ErrorText>{tc(messageKeyOf(items.error))}</ErrorText> : null}
      {items.data && items.data.length === 0 ? <EmptyState message={t("compliance.empty")} /> : null}
      <ul className="flex max-w-3xl flex-col gap-3">
        {items.data?.map((item) => (
          <li key={item.id}>
            <Link
              to={`/compliance/${item.id}`}
              className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-line bg-surface p-4 shadow-card hover:border-teal focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
            >
              <span>
                <span className="block text-body font-bold">{item.title}</span>
                <span className="block text-small text-muted">
                  {dueText(item, t, language)}
                  {item.vendor_name ? ` · ${item.vendor_name}` : ""}
                </span>
              </span>
              <ComplianceStatus status={item.status} />
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
