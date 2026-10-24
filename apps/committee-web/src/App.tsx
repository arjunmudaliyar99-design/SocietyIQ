
import { Route, Routes } from "react-router-dom";

import { EmptyState, useTranslation } from "@societyiq/shared";

import { ChargesPage } from "./charges/ChargesPage";
import { HeadPage } from "./charges/HeadPage";
import { PreviewPage } from "./charges/PreviewPage";
import { SettingsPage } from "./charges/SettingsPage";
import { TaxImportPage } from "./charges/TaxImportPage";
import { FlatPage } from "./flats/FlatPage";
import { FlatsPage } from "./flats/FlatsPage";
import { ImportPage } from "./flats/ImportPage";
import { NewFlatPage } from "./flats/NewFlatPage";
import { WingsPage } from "./flats/WingsPage";
import { Preview } from "./Preview";
import { DETAILED_NAV, SIMPLE_NAV } from "./nav";
import { PeoplePage } from "./setup/PeoplePage";
import { Shell } from "./Shell";

function Home() {
  const { t } = useTranslation("committee");
  return (
    <>
      <h1 className="mb-6 text-title font-bold">{t("home.title")}</h1>
      <EmptyState message={t("home.body")} />
    </>
  );
}

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
const BUILT = new Set(["/", "/settings", "/flats", "/charges"]);

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Home />} />
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
        <Route path="/charges" element={<ChargesPage />} />
        <Route path="/charges/new" element={<HeadPage />} />
        <Route path="/charges/preview" element={<PreviewPage />} />
        <Route path="/charges/settings" element={<SettingsPage />} />
        <Route path="/charges/property-tax" element={<TaxImportPage />} />
        <Route path="/charges/:headId" element={<HeadPage />} />
        <Route path="/preview" element={<Preview />} />
        <Route path="*" element={<Home />} />
      </Routes>
    </Shell>
  );
}
