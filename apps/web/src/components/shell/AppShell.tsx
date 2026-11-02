"use client";

import * as Dialog from "@radix-ui/react-dialog";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { LOCALES, type AppLocale } from "@/i18n/config";
import { useI18n } from "@/i18n/I18nProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import { NAV_GROUPS, SECTIONS } from "@/lib/sections";
import { NivaroLogo, NivaroMark } from "../brand/Brand";
import { Button } from "../ui/Button";
import { Icon } from "../ui/Icon";
import {
  MenuContent,
  MenuItem,
  MenuLabel,
  MenuRadioGroup,
  MenuRadioItem,
  MenuRoot,
  MenuSeparator,
  MenuTrigger,
} from "../ui/Menu";
import { ToastProvider } from "../ui/misc";
import { CommandPalette } from "./CommandPalette";
import styles from "./shell.module.css";

function initials(text: string): string {
  const parts = text.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "·";
}

function useIsMac() {
  const [mac, setMac] = useState(false);
  useEffect(() => {
    setMac(/Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent));
  }, []);
  return mac;
}

function MerchantSwitcher() {
  const { t } = useI18n();
  const { activeMemberships, membership, selectMerchant } = useAuth();
  const router = useRouter();
  const name = membership?.merchant.name ?? "";
  return (
    <MenuRoot>
      <MenuTrigger asChild>
        <button type="button" className={styles.switcher} aria-label={`${t("shell.switchBusiness")}: ${name}`}>
          <span className={styles.monogram} aria-hidden="true">
            {initials(name)}
          </span>
          <span className={styles.switcherText}>
            <span className={styles.switcherName}>{name}</span>
            {membership ? <span className={styles.switcherRole}>{t(`shell.role.${membership.role}`)}</span> : null}
          </span>
          <Icon name="chevronDown" />
        </button>
      </MenuTrigger>
      <MenuContent>
        <MenuLabel>{t("shell.switchBusiness")}</MenuLabel>
        <MenuRadioGroup value={membership?.merchant.id} onValueChange={(id) => selectMerchant(id)}>
          {activeMemberships.map((m) => (
            <MenuRadioItem key={m.merchant.id} value={m.merchant.id}>
              <Icon name="store" />
              {m.merchant.name}
            </MenuRadioItem>
          ))}
        </MenuRadioGroup>
        <MenuSeparator />
        <MenuItem onSelect={() => router.push("/onboarding")}>
          <Icon name="plus" />
          {t("shell.addBusiness")}
        </MenuItem>
      </MenuContent>
    </MenuRoot>
  );
}

function UserMenu() {
  const { t, locale, setLocale } = useI18n();
  const { me, signOut, api } = useAuth();
  const router = useRouter();
  if (!me) return null;
  const changeLocale = (next: string) => {
    const l = next as AppLocale;
    setLocale(l);
    void api.me.update({ locale: l }).catch(() => {
      /* preference still stored in cookie */
    });
  };
  return (
    <MenuRoot>
      <MenuTrigger asChild>
        <button type="button" className={styles.userButton} aria-label={`${t("shell.accountMenu")}: ${me.user.full_name}`}>
          <span className={styles.avatar} aria-hidden="true">
            {initials(me.user.full_name || me.user.email)}
          </span>
          <span className={styles.userText}>
            <span>{me.user.full_name}</span>
            <span>{me.user.email}</span>
          </span>
        </button>
      </MenuTrigger>
      <MenuContent side="top" align="start">
        <MenuLabel>{t("language.label")}</MenuLabel>
        <MenuRadioGroup value={locale} onValueChange={changeLocale}>
          {LOCALES.map((l) => (
            <MenuRadioItem key={l} value={l}>
              <span lang={l}>{t(`language.${l}`)}</span>
            </MenuRadioItem>
          ))}
        </MenuRadioGroup>
        <MenuSeparator />
        <MenuItem
          onSelect={() => {
            void signOut().finally(() => router.replace("/login"));
          }}
        >
          <Icon name="logout" />
          {t("shell.signOut")}
        </MenuItem>
      </MenuContent>
    </MenuRoot>
  );
}

function SidebarContent({ onOpenSearch, onNavigate }: { onOpenSearch: () => void; onNavigate?: () => void }) {
  const { t, number } = useI18n();
  const pathname = usePathname();
  const isMac = useIsMac();
  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  return (
    <div className={styles.sidebarInner}>
      <Link href="/home" className={styles.brandRow} onClick={onNavigate}>
        <NivaroLogo height={20} label={t("brand.name")} />
      </Link>
      <MerchantSwitcher />
      <button type="button" className={styles.searchButton} onClick={onOpenSearch}>
        <Icon name="search" />
        {t("shell.search")}
        <kbd className={styles.kbd}>{isMac ? "⌘K" : "Ctrl K"}</kbd>
      </button>
      <nav className={styles.nav} aria-label={t("nav.primary")}>
        {NAV_GROUPS.map(({ group, labelKey }) => {
          const items = SECTIONS.filter((s) => s.group === group);
          const labelId = `nav-group-${group}`;
          return (
            <div key={group}>
              {labelKey ? (
                <p className={styles.groupLabel} id={labelId}>
                  {t(labelKey)}
                </p>
              ) : null}
              <ul className={styles.group} aria-labelledby={labelKey ? labelId : undefined}>
                {items.map((s) => (
                  <li key={s.key}>
                    <Link
                      href={s.href}
                      className={styles.link}
                      aria-current={isActive(s.href) ? "page" : undefined}
                      onClick={onNavigate}
                    >
                      <Icon name={s.icon} />
                      {t(`nav.${s.key}`)}
                      {s.phase ? (
                        <span className={styles.phase} title={t("nav.phaseLabel", { phase: number(s.phase) })}>
                          {t("nav.phaseShort", { phase: number(s.phase) })}
                        </span>
                      ) : null}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </nav>
      <div className={styles.sidebarFooter}>
        <Link
          href="/settings/team"
          className={styles.link}
          aria-current={isActive("/settings") ? "page" : undefined}
          onClick={onNavigate}
        >
          <Icon name="settings" />
          {t("nav.settings")}
        </Link>
        <UserMenu />
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const { membership } = useAuth();
  const [searchOpen, setSearchOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setNavOpen(false);
        setSearchOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    setNavOpen(false);
  }, [pathname]);

  return (
    <ToastProvider>
      <a href="#main" className={styles.skip}>
        {t("common.skipToContent")}
      </a>
      <div className={styles.shell}>
        <aside className={styles.sidebar}>
          <SidebarContent onOpenSearch={() => setSearchOpen(true)} />
        </aside>

        <div className={styles.main}>
          <header className={styles.topbar}>
            <Dialog.Root open={navOpen} onOpenChange={setNavOpen}>
              <Dialog.Trigger asChild>
                <Button variant="ghost" iconOnly aria-label={t("nav.openMenu")}>
                  <Icon name="menu" />
                </Button>
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className={styles.scrim} />
                <Dialog.Content className={styles.mobileNav} aria-describedby={undefined}>
                  <Dialog.Title className="srOnly">{t("nav.primary")}</Dialog.Title>
                  <SidebarContent
                    onOpenSearch={() => {
                      setNavOpen(false);
                      setSearchOpen(true);
                    }}
                    onNavigate={() => setNavOpen(false)}
                  />
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
            <NivaroMark size={20} title={t("brand.name")} />
            <span className={styles.topbarTitle}>{membership?.merchant.name}</span>
            <Button variant="ghost" iconOnly aria-label={t("shell.search")} onClick={() => setSearchOpen(true)}>
              <Icon name="search" />
            </Button>
          </header>
          <main id="main" className={styles.content} tabIndex={-1}>
            {children}
          </main>
        </div>
      </div>
      <CommandPalette open={searchOpen} onOpenChange={setSearchOpen} />
    </ToastProvider>
  );
}
