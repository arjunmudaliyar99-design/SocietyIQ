import {
  ArrowLeft,
  FileText,
  Megaphone,
  Menu,
  MessageSquareWarning,
  Receipt,
  Settings,
  Wallet,
} from "lucide-react";
import type { ReactNode } from "react";

import { Link, Route, Routes, useNavigate } from "react-router-dom";

import {
  BigButton,
  Button,
  Card,
  EmptyState,
  HelpButton,
  LanguageSwitcher,
  TextSizeSwitcher,
  useTranslation,
} from "@societyiq/shared";

import { support } from "./config";
import { InstallBanner } from "./InstallBanner";

function TopBar() {
  const { t } = useTranslation();
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-xl flex-wrap items-center justify-between gap-2 p-3">
        <Link to="/" className="rounded-lg focus-visible:outline-3 focus-visible:outline-ink">
          <img src="/logo-light.svg" alt={t("appName")} className="h-9 w-auto" />
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          <LanguageSwitcher />
          <HelpButton support={support} />
        </div>
      </div>
    </header>
  );
}

/** Simple-mode home: dues banner plus three big buttons (docs/02 §11). */
function Home() {
  const { t } = useTranslation("resident");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  return (
    <div className="flex flex-col gap-4">
      {/* Real dues (flat, amount, due date) come from the API in M6-M7. */}
      <Card role="region" aria-label={t("home.pay")} className="border-2 border-teal">
        <p className="text-body">{t("home.duesPlaceholder")}</p>
      </Card>
      <BigButton icon={<Wallet size={26} />} onClick={() => navigate("/pay")}>
        {t("home.pay")}
      </BigButton>
      <BigButton variant="secondary" icon={<Megaphone size={26} />} onClick={() => navigate("/notices")}>
        {t("home.notices")}
      </BigButton>
      <BigButton
        variant="secondary"
        icon={<MessageSquareWarning size={26} />}
        onClick={() => navigate("/report")}
      >
        {t("home.report")}
      </BigButton>
      <Button variant="secondary" icon={<Menu size={22} />} onClick={() => navigate("/menu")}>
        {tc("menu")}
      </Button>
    </div>
  );
}

function Page({ title, children }: { title: string; children: ReactNode }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <div className="flex flex-col gap-4">
      <div>
        <Button variant="secondary" icon={<ArrowLeft size={22} />} onClick={() => navigate("/")}>
          {t("back")}
        </Button>
      </div>
      <h1 className="text-title font-bold">{title}</h1>
      {children}
    </div>
  );
}

function ComingSoon({ title }: { title: string }) {
  const { t } = useTranslation();
  return (
    <Page title={title}>
      <EmptyState message={`${t("comingSoon")}. ${t("comingSoonBody")}`} />
    </Page>
  );
}

function MenuPage() {
  const { t } = useTranslation("resident");
  const { t: tc } = useTranslation();
  const navigate = useNavigate();
  const items = [
    { path: "/bills", label: t("menu.myBills"), icon: <FileText size={24} /> },
    { path: "/receipts", label: t("menu.myReceipts"), icon: <Receipt size={24} /> },
    { path: "/complaints", label: t("menu.myComplaints"), icon: <MessageSquareWarning size={24} /> },
    { path: "/settings", label: t("menu.settings"), icon: <Settings size={24} /> },
  ];
  return (
    <Page title={tc("menu")}>
      {items.map((item) => (
        <BigButton key={item.path} variant="secondary" icon={item.icon} onClick={() => navigate(item.path)}>
          {item.label}
        </BigButton>
      ))}
      <div>
        <Button variant="secondary" disabled>
          {tc("signOut")}
        </Button>
        <p className="mt-2 text-small text-muted">{tc("signOutSoon")}</p>
      </div>
    </Page>
  );
}

function SettingsPage() {
  const { t } = useTranslation("resident");
  const { t: tc } = useTranslation();
  return (
    <Page title={t("menu.settings")}>
      <Card className="flex flex-col gap-6">
        <div>
          <p className="mb-2 text-body font-semibold">{tc("language")}</p>
          <LanguageSwitcher />
        </div>
        <TextSizeSwitcher />
      </Card>
    </Page>
  );
}

export default function App() {
  const { t } = useTranslation("resident");
  return (
    <div className="min-h-screen">
      <TopBar />
      <main className="mx-auto max-w-xl p-4">
        <InstallBanner />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/pay" element={<ComingSoon title={t("home.pay")} />} />
          <Route path="/notices" element={<ComingSoon title={t("home.notices")} />} />
          <Route path="/report" element={<ComingSoon title={t("home.report")} />} />
          <Route path="/menu" element={<MenuPage />} />
          <Route path="/bills" element={<ComingSoon title={t("menu.myBills")} />} />
          <Route path="/receipts" element={<ComingSoon title={t("menu.myReceipts")} />} />
          <Route path="/complaints" element={<ComingSoon title={t("menu.myComplaints")} />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </main>
    </div>
  );
}
