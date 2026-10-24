
import { Route, Routes } from "react-router-dom";

import { EmptyState, useTranslation } from "@societyiq/shared";

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

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Home />} />
        {[...SIMPLE_NAV, ...DETAILED_NAV]
          .filter((item) => item.path !== "/" && item.path !== "/settings")
          .map((item) => (
            <Route key={item.path} path={item.path} element={<ComingSoon navKey={item.key} />} />
          ))}
        <Route path="/settings" element={<PeoplePage />} />
        <Route path="/preview" element={<Preview />} />
        <Route path="*" element={<Home />} />
      </Routes>
    </Shell>
  );
}
