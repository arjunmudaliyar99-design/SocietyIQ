
import { Route, Routes } from "react-router-dom";

import { EmptyState, useTranslation } from "@societyiq/shared";

import { BillPage } from "./billing/BillPage";
import { BillsPage } from "./billing/BillsPage";
import { RunPage } from "./billing/RunPage";
import { ComplaintPage } from "./complaints/ComplaintPage";
import { ComplaintsPage } from "./complaints/ComplaintsPage";
import { NewComplaintPage } from "./complaints/NewComplaintPage";
import { ChargesPage } from "./charges/ChargesPage";
import { HeadPage } from "./charges/HeadPage";
import { PreviewPage } from "./charges/PreviewPage";
import { SettingsPage } from "./charges/SettingsPage";
import { TaxImportPage } from "./charges/TaxImportPage";
import { CompliancePage } from "./compliance/CompliancePage";
import { ItemFormPage } from "./compliance/ItemFormPage";
import { ItemPage } from "./compliance/ItemPage";
import { VendorsPage } from "./compliance/VendorsPage";
import { FlatPage } from "./flats/FlatPage";
import { FlatsPage } from "./flats/FlatsPage";
import { ImportPage } from "./flats/ImportPage";
import { NewFlatPage } from "./flats/NewFlatPage";
import { WingsPage } from "./flats/WingsPage";
import { DuesPage } from "./payments/DuesPage";
import { LedgerPage } from "./payments/LedgerPage";
import { PaymentPage } from "./payments/PaymentPage";
import { PaymentsPage } from "./payments/PaymentsPage";
import { RecordPaymentPage } from "./payments/RecordPaymentPage";
import { HomePage } from "./home/HomePage";
import { Preview } from "./Preview";
import { DETAILED_NAV, SIMPLE_NAV } from "./nav";
import { PeoplePage } from "./setup/PeoplePage";
import { Shell } from "./Shell";

function ComingSoon({ navKey }: { navKey: string }) {
  const { t } = useTranslation();
  const { t: tc } = useTranslation("committee");
  return (
    <>
      <h1 className="mb-6 text-title font-bold">{tc(`nav.${navKey}`)}</h1>
      <EmptyState message={`${t("comingSoon")}. ${t("comingSoonBody")}`} />
    </>
  );
}

// Menu items with real pages; the rest show "Coming soon" until their milestone.
const BUILT = new Set(["/", "/settings", "/flats", "/charges", "/bills", "/complaints", "/payments", "/dues", "/compliance"]);

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<HomePage />} />
        {[...SIMPLE_NAV, ...DETAILED_NAV]
          .filter((item) => !BUILT.has(item.path))
          .map((item) => (
            <Route key={item.path} path={item.path} element={<ComingSoon navKey={item.key} />} />
          ))}
        <Route path="/settings" element={<PeoplePage />} />
        <Route path="/flats" element={<FlatsPage />} />
        <Route path="/flats/new" element={<NewFlatPage />} />
        <Route path="/flats/wings" element={<WingsPage />} />
        <Route path="/flats/import" element={<ImportPage />} />
        <Route path="/flats/:flatId" element={<FlatPage />} />
        <Route path="/flats/:flatId/ledger" element={<LedgerPage />} />
        <Route path="/payments" element={<PaymentsPage />} />
        <Route path="/payments/new" element={<RecordPaymentPage />} />
        <Route path="/payments/:paymentId" element={<PaymentPage />} />
        <Route path="/dues" element={<DuesPage />} />
        <Route path="/bills" element={<BillsPage />} />
        <Route path="/bills/runs/:runId" element={<RunPage />} />
        <Route path="/bills/:billId" element={<BillPage />} />
        <Route path="/charges" element={<ChargesPage />} />
        <Route path="/charges/new" element={<HeadPage />} />
        <Route path="/charges/preview" element={<PreviewPage />} />
        <Route path="/charges/settings" element={<SettingsPage />} />
        <Route path="/charges/property-tax" element={<TaxImportPage />} />
        <Route path="/charges/:headId" element={<HeadPage />} />
        <Route path="/complaints" element={<ComplaintsPage />} />
        <Route path="/complaints/new" element={<NewComplaintPage />} />
        <Route path="/complaints/:complaintId" element={<ComplaintPage />} />
        <Route path="/compliance" element={<CompliancePage />} />
        <Route path="/compliance/new" element={<ItemFormPage />} />
        <Route path="/compliance/vendors" element={<VendorsPage />} />
        <Route path="/compliance/:itemId" element={<ItemPage />} />
        <Route path="/compliance/:itemId/edit" element={<ItemFormPage />} />
        <Route path="/preview" element={<Preview />} />
        <Route path="*" element={<HomePage />} />
      </Routes>
    </Shell>
  );
}
