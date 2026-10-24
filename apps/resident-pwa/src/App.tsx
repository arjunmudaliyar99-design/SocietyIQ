import {
  ArrowLeft,
  FileText,
  House,
  Megaphone,
  Menu,
  MessageSquareWarning,
  Receipt,
  Settings,
  Wallet,
} from "lucide-react";
import type { ReactNode } from "react";

import { Link, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import {
  BigButton,
  Button,
  Card,
  EmptyState,
  HelpButton,
  LanguageSwitcher,
  TextSizeSwitcher,
  useAuth,
  useCurrentSociety,
  useTranslation,
} from "@societyiq/shared";

import { ComplaintPage, MyComplaintsPage, ReportPage } from "./complaints/ComplaintPages";
import { NoticePage, NoticesPage } from "./notices/NoticePages";
import { support } from "./config";
import { InstallBanner } from "./InstallBanner";
import { useMyFlats } from "./api/money";
import { DuesCard } from "./money/DuesCard";
import { MyBillsList, MyReceiptsList } from "./money/HistoryPages";
import { OfflineBanner } from "./money/OfflineBanner";
import { PayPage } from "./money/PayPage";

function TopBar() {
  const { t } = useTranslation();
  const current = useCurrentSociety();
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface/95 shadow-bar backdrop-blur">
      <div className="mx-auto flex max-w-xl items-center gap-2 px-3 py-2">
        <Link to="/" className="shrink-0 rounded-lg focus-visible:outline-3 focus-visible:outline-ink">
          <img src="/mark.svg" alt={t("appName")} className="h-10 w-10" />
        </Link>
        <p className="min-w-0 flex-1 truncate text-body font-bold">{current?.society.name ?? t("appName")}</p>
        <LanguageSwitcher className="[&>svg]:hidden" />
        <HelpButton support={support} compact />
      </div>
    </header>
  );
}

/** Phone-style tab bar: the four places a resident goes most, always one tap away. */
function BottomBar() {
  const { t } = useTranslation("resident");
  const { t: tc } = useTranslation();
  const items = [
    { to: "/", label: t("nav.home"), icon: <House size={24} /> },
    { to: "/bills", label: t("menu.myBills"), icon: <FileText size={24} /> },
    { to: "/notices", label: t("home.notices"), icon: <Megaphone size={24} /> },
    { to: "/menu", label: tc("menu"), icon: <Menu size={24} /> },
  ];
  return (
    <nav
      aria-label={t("nav.label")}
      className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 pb-[env(safe-area-inset-bottom)] shadow-bar backdrop-blur"
    >
      <ul className="mx-auto grid max-w-xl grid-cols-4">
        {items.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex min-h-[64px] flex-col items-center justify-center gap-1 text-small font-semibold transition-colors focus-visible:outline-3 focus-visible:outline-ink ${
                  isActive ? "text-teal" : "text-muted hover:text-ink"
                }`
              }
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** Simple-mode home: dues banner plus three big buttons (docs/02 §11). */
/** Pay is hidden only once we know none of the person's flats may pay (a tenant the owner
 * has not allowed, docs/07 M7). */
function useCanPay(): boolean {
  const flats = useMyFlats();
  if (!flats.data || flats.data.length === 0) return true;
  return flats.data.some((f) => f.can_pay);
}

function Home() {
  const { t } = useTranslation("resident");
  const navigate = useNavigate();
  const current = useCurrentSociety();
  return (
    <div className="flex flex-col gap-4">
      <DuesCard />
      {current ? <PayButton /> : (
        <BigButton icon={<Wallet size={26} />} onClick={() => navigate("/pay")} className="sm:w-full">
          {t("home.pay")}
        </BigButton>
      )}
      <div className="grid grid-cols-2 gap-3">
        <BigButton
          variant="secondary"
          icon={<Megaphone size={26} />}
          onClick={() => navigate("/notices")}
          className="h-full flex-col sm:w-full sm:min-w-0"
        >
          {t("home.notices")}
        </BigButton>
        <BigButton
          variant="secondary"
          icon={<MessageSquareWarning size={26} />}
          onClick={() => navigate("/report")}
          className="h-full flex-col sm:w-full sm:min-w-0"
        >
          {t("home.report")}
        </BigButton>
      </div>
    </div>
  );
}

function PayButton() {
  const { t } = useTranslation("resident");
  const navigate = useNavigate();
  if (!useCanPay()) return null;
  return (
    <BigButton icon={<Wallet size={26} />} onClick={() => navigate("/pay")} className="sm:w-full">
      {t("home.pay")}
    </BigButton>
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
      <SignOut />
    </Page>
  );
}

/** Outside the sign-in gate (component tests) there is no account to sign out of. */
function SignOut() {
  const current = useCurrentSociety();
  return current ? <SignOutButton /> : null;
}

function SignOutButton() {
  const { t } = useTranslation();
  const { signOut } = useAuth();
  return (
    <div>
      <Button variant="secondary" onClick={() => void signOut()}>
        {t("signOut")}
      </Button>
    </div>
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

/** Money pages need a signed-in society; outside it (previews, tests) they say Coming soon. */
function Signed({ title, children }: { title: string; children: ReactNode }) {
  const current = useCurrentSociety();
  if (!current) return <ComingSoon title={title} />;
  return <Page title={title}>{children}</Page>;
}

export default function App() {
  const { t } = useTranslation("resident");
  const location = useLocation();
  return (
    <div className="min-h-screen">
      <TopBar />
      {/* Bottom padding keeps the last item clear of the tab bar. */}
      <main key={location.pathname} className="mx-auto max-w-xl animate-enter p-4 pb-28">
        <OfflineBanner />
        <InstallBanner />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/pay" element={<Signed title={t("home.pay")}><PayPage /></Signed>} />
          <Route path="/notices" element={<NoticesPage />} />
          <Route path="/notices/:noticeId" element={<NoticePage />} />
          <Route path="/report" element={<ReportPage />} />
          <Route path="/menu" element={<MenuPage />} />
          <Route path="/bills" element={<Signed title={t("menu.myBills")}><MyBillsList /></Signed>} />
          <Route path="/receipts" element={<Signed title={t("menu.myReceipts")}><MyReceiptsList /></Signed>} />
          <Route path="/complaints" element={<MyComplaintsPage />} />
          <Route path="/complaints/:complaintId" element={<ComplaintPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </main>
      <BottomBar />
    </div>
  );
}
