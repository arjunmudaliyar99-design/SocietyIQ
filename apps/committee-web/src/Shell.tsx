import { Menu, User, X } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { NavLink, useLocation } from "react-router-dom";

import {
  Button,
  Dialog,
  HelpButton,
  LanguageSwitcher,
  TextSizeSwitcher,
  ViewModeSwitcher,
  useAuth,
  useCurrentSociety,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

import { support } from "./config";
import { DETAILED_NAV, SIMPLE_NAV, type NavItem } from "./nav";

function NavList({ items, onPick }: { items: NavItem[]; onPick?: () => void }) {
  const { t } = useTranslation("committee");
  return (
    <ul className="flex flex-col gap-1">
      {items.map((item) => (
        <li key={item.path}>
          <NavLink
            to={item.path}
            end={item.path === "/"}
            onClick={onPick}
            className={({ isActive }) =>
              `flex min-h-[52px] items-center gap-3 rounded-lg border-l-4 px-4 text-body font-semibold transition-colors duration-150 focus-visible:outline-3 focus-visible:outline-ink ${
                isActive ? "border-teal bg-teal/10 text-teal-dark" : "border-transparent text-ink hover:bg-paper"
              }`
            }
          >
            <span aria-hidden="true">{item.icon}</span>
            {t(`nav.${item.key}`)}
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

/** Phone menu: slides in from the left over a dimmed page. Escape, the X or a tap outside
 * closes it; focus moves in on open and back to the menu button on close. */
function Drawer({ items, onClose }: { items: NavItem[]; onClose: () => void }) {
  const { t } = useTranslation();
  const { t: tc } = useTranslation("committee");
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-40 md:hidden">
      <button type="button" aria-label={t("close")} className="absolute inset-0 animate-fade bg-ink/50" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={tc("nav.label")}
        className="absolute inset-y-0 left-0 flex w-[85%] max-w-xs animate-drawer flex-col gap-4 overflow-y-auto bg-surface p-4 shadow-raised"
      >
        <div className="flex items-center justify-between">
          <img src="/logo-light.svg" alt={t("appName")} className="h-9 w-auto" />
          <Button ref={closeRef} variant="secondary" icon={<X size={20} />} onClick={onClose}>
            {t("close")}
          </Button>
        </div>
        <nav aria-label={tc("nav.label")}>
          <NavList items={items} onPick={onClose} />
        </nav>
        <div className="mt-auto flex flex-col gap-3 border-t border-line pt-4">
          <LanguageSwitcher />
          <HelpButton support={support} />
        </div>
      </div>
    </div>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const { t } = useTranslation("committee");
  const { simpleMode } = useSettings();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const items = simpleMode ? SIMPLE_NAV : [...SIMPLE_NAV, ...DETAILED_NAV];
  const menuButton = useRef<HTMLButtonElement>(null) as React.RefObject<HTMLButtonElement>;

  function closeMenu() {
    setMenuOpen(false);
    menuButton.current?.focus();
  }

  return (
    <div className="min-h-screen">
      <TopBar menuButton={menuButton} onMenu={() => setMenuOpen(true)} menuOpen={menuOpen} />
      {menuOpen ? <Drawer items={items} onClose={closeMenu} /> : null}
      <div className="mx-auto flex max-w-7xl">
        <nav aria-label={t("nav.label")} className="hidden w-64 shrink-0 md:block">
          <div className="sticky top-[73px] p-3">
            <NavList items={items} />
          </div>
        </nav>
        <main key={location.pathname} className="min-w-0 flex-1 animate-enter p-4 pb-12 md:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}

function TopBar({
  menuButton,
  onMenu,
  menuOpen,
}: {
  menuButton: React.RefObject<HTMLButtonElement>;
  onMenu: () => void;
  menuOpen: boolean;
}) {
  const { t } = useTranslation();
  const { t: tc } = useTranslation("committee");
  const [accountOpen, setAccountOpen] = useState(false);
  const current = useCurrentSociety();

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface/95 shadow-bar backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-3 py-2">
        <button
          ref={menuButton}
          type="button"
          onClick={onMenu}
          aria-expanded={menuOpen}
          aria-label={t("menu")}
          className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-lg text-ink transition-colors hover:bg-paper focus-visible:outline-3 focus-visible:outline-ink md:hidden"
        >
          <Menu size={26} aria-hidden="true" />
        </button>
        <img src="/logo-light.svg" alt={t("appName")} className="hidden h-10 w-auto sm:block" />
        <p className="min-w-0 flex-1 truncate text-body font-bold sm:border-l sm:border-line sm:pl-3">
          {current?.society.name ?? tc("societyPlaceholder")}
        </p>
        <div className="hidden items-center gap-2 md:flex">
          <LanguageSwitcher />
          <HelpButton support={support} />
        </div>
        <Button variant="secondary" icon={<User size={22} />} onClick={() => setAccountOpen(true)}>
          <span className="sr-only sm:not-sr-only">{t("account")}</span>
        </Button>
      </div>
      <Dialog open={accountOpen} title={t("account")} onClose={() => setAccountOpen(false)}>
        <div className="flex flex-col gap-6">
          <TextSizeSwitcher />
          <ViewModeSwitcher />
          <AccountActions onDone={() => setAccountOpen(false)} />
        </div>
      </Dialog>
    </header>
  );
}

/** Outside the sign-in gate (component tests) there is no account to act on. */
function AccountActions({ onDone }: { onDone: () => void }) {
  const current = useCurrentSociety();
  return current ? <SignedInActions onDone={onDone} /> : null;
}

function SignedInActions({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const { signOut, email } = useAuth();
  const current = useCurrentSociety();
  return (
    <div className="flex flex-col gap-3">
      {email ? <p className="text-small text-muted">{email}</p> : null}
      {current?.canSwitch ? (
        <Button
          variant="secondary"
          onClick={() => {
            onDone();
            current.switchSociety();
          }}
        >
          {t("picker.switch")}
        </Button>
      ) : null}
      <Button variant="secondary" onClick={() => void signOut()}>
        {t("signOut")}
      </Button>
    </div>
  );
}
