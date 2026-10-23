import { Menu, User } from "lucide-react";
import { useState, type ReactNode } from "react";

import { NavLink, useLocation } from "react-router-dom";

import {
  Button,
  Dialog,
  HelpButton,
  LanguageSwitcher,
  TextSizeSwitcher,
  ViewModeSwitcher,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

import { support } from "./config";
import { DETAILED_NAV, SIMPLE_NAV } from "./nav";

export function Shell({ children }: { children: ReactNode }) {
  const { t } = useTranslation("committee");
  const { simpleMode } = useSettings();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const items = simpleMode ? SIMPLE_NAV : [...SIMPLE_NAV, ...DETAILED_NAV];

  return (
    <div className="min-h-screen">
      <TopBar onMenu={() => setMenuOpen((open) => !open)} menuOpen={menuOpen} />
      <div className="mx-auto flex max-w-7xl flex-col md:flex-row">
        <nav
          aria-label={t("nav.label")}
          className={`${menuOpen ? "block" : "hidden"} border-b border-line bg-surface p-3 md:block md:w-64 md:shrink-0 md:border-r md:border-b-0`}
        >
          <ul className="flex flex-col gap-2">
            {items.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  end
                  onClick={() => setMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex min-h-[56px] items-center gap-3 rounded-lg px-4 text-body font-semibold focus-visible:outline-3 focus-visible:outline-ink ${
                      isActive ? "bg-teal text-surface" : "text-ink hover:bg-paper"
                    }`
                  }
                >
                  <span aria-hidden="true">{item.icon}</span>
                  {t(`nav.${item.key}`)}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <main key={location.pathname} className="min-w-0 flex-1 p-4 md:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}

function TopBar({ onMenu, menuOpen }: { onMenu: () => void; menuOpen: boolean }) {
  const { t } = useTranslation();
  const { t: tc } = useTranslation("committee");
  const [accountOpen, setAccountOpen] = useState(false);

  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 p-3">
        <img src="/logo-light.svg" alt={t("appName")} className="h-10 w-auto" />
        {/* Society name comes from the signed-in membership in M2. */}
        <p className="min-w-0 flex-1 truncate text-body font-semibold">{tc("societyPlaceholder")}</p>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            icon={<Menu size={22} />}
            onClick={onMenu}
            aria-expanded={menuOpen}
            className="md:hidden"
          >
            {t("menu")}
          </Button>
          <LanguageSwitcher />
          <HelpButton support={support} />
          <Button variant="secondary" icon={<User size={22} />} onClick={() => setAccountOpen(true)}>
            {t("account")}
          </Button>
        </div>
      </div>
      <Dialog open={accountOpen} title={t("account")} onClose={() => setAccountOpen(false)}>
        <div className="flex flex-col gap-6">
          <TextSizeSwitcher />
          <ViewModeSwitcher />
          <div>
            <Button variant="secondary" disabled>
              {t("signOut")}
            </Button>
            <p className="mt-2 text-small text-muted">{t("signOutSoon")}</p>
          </div>
        </div>
      </Dialog>
    </header>
  );
}
