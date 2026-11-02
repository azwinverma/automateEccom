"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ElementType, type ReactNode } from "react";
import { NivaroLogo } from "@/components/brand/Brand";
import { Icon } from "@/components/ui/Icon";
import { LOCALES } from "@/i18n/config";
import { useI18n } from "@/i18n/I18nProvider";
import { ThemeToggle } from "@/lib/theme/ThemeToggle";
import type { SiteCopy } from "./copy";
import styles from "./site.module.css";

/** No motion when the user asks for less, or when the browser can't observe scrolling (content just shows). */
const reduced = () =>
  typeof window === "undefined" ||
  typeof IntersectionObserver === "undefined" ||
  Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);

/**
 * Marks a section visible the first time it scrolls into view (once). CSS does the motion:
 * children with `.rv` rise in, ribbons trace, hand accents draw. Without JS, or with reduced motion,
 * everything is simply shown (hiding only applies once `data-reveal-ready` is set).
 */
export function Reveal({ as: Tag = "section", children, ...rest }: { as?: ElementType; children: ReactNode } & Record<string, unknown>) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (reduced()) {
      el.setAttribute("data-visible", "");
      return;
    }
    const r = el.getBoundingClientRect();
    if (r.top < window.innerHeight * 0.9 && r.bottom > 0) el.setAttribute("data-visible", "");
    el.setAttribute("data-reveal-ready", "");
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.setAttribute("data-visible", "");
            io.unobserve(e.target);
          }
        }
      },
      { rootMargin: "0px 0px -12% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <Tag ref={ref} {...rest}>
      {children}
    </Tag>
  );
}

/** Counts up to `value` once when scrolled into view; static under reduced motion. */
export function CountUp({ value, format }: { value: number; format?: (n: number) => string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [n, setN] = useState(value);
  useEffect(() => {
    const el = ref.current;
    if (!el || reduced()) return;
    setN(0);
    let raf = 0;
    const io = new IntersectionObserver(([e]) => {
      if (!e?.isIntersecting) return;
      io.disconnect();
      const start = performance.now();
      const tick = (t: number) => {
        const p = Math.min(1, (t - start) / 900);
        setN(Math.round(value * (1 - Math.pow(1 - p, 3))));
        if (p < 1) raf = requestAnimationFrame(tick);
      };
      raf = requestAnimationFrame(tick);
    });
    io.observe(el);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [value]);
  return (
    <span ref={ref} className={styles.count}>
      {format ? format(n) : n}
    </span>
  );
}

function LangSwitch() {
  const { t, locale, setLocale } = useI18n();
  return (
    <div className={styles.lang} role="group" aria-label={t("language.label")}>
      {LOCALES.map((l) => (
        <button key={l} type="button" lang={l} aria-pressed={locale === l} onClick={() => setLocale(l)}>
          {l === "en" ? "EN" : "ने"}
        </button>
      ))}
    </div>
  );
}

export function SiteHeader({ copy, signedIn }: { copy: SiteCopy["nav"]; signedIn: boolean }) {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 8);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  const links: [string, string][] = [
    ["#how", copy.how],
    ["#product", copy.product],
    ["#intelligence", copy.intelligence],
    ["#plans", copy.plans],
  ];
  return (
    <header className={styles.header} data-scrolled={scrolled || undefined} data-open={open || undefined}>
      <a href="#top" className={styles.skip}>
        {copy.skip}
      </a>
      <div className={styles.headerInner}>
        <Link href="/" className={styles.brand} aria-label="Nivaro">
          <NivaroLogo height={26} />
        </Link>
        <nav className={styles.nav} aria-label="Nivaro">
          {links.map(([href, label]) => (
            <a key={href} href={href} onClick={() => setOpen(false)}>
              {label}
            </a>
          ))}
        </nav>
        <div className={styles.headerTools}>
          <ThemeToggle />
          <LangSwitch />
        </div>
        <div className={styles.headerActions}>
          {signedIn ? (
            <Link href="/home" className={styles.btnPrimary}>
              {copy.open}
            </Link>
          ) : (
            <>
              <Link href="/login" className={styles.btnGhost}>
                {copy.signIn}
              </Link>
              <Link href="/register" className={styles.btnPrimary}>
                {copy.start}
              </Link>
            </>
          )}
        </div>
        <button
          type="button"
          className={styles.menuButton}
          aria-expanded={open}
          aria-controls="site-menu"
          aria-label={copy.menu}
          onClick={() => setOpen((o) => !o)}
        >
          <Icon name={open ? "close" : "menu"} />
        </button>
      </div>
      <div id="site-menu" className={styles.mobileMenu} hidden={!open}>
        {links.map(([href, label]) => (
          <a key={href} href={href} onClick={() => setOpen(false)}>
            {label}
          </a>
        ))}
        <div className={styles.mobileTools}>
          <ThemeToggle />
          <LangSwitch />
        </div>
        {signedIn ? (
          <Link href="/home" className={styles.btnPrimary}>
            {copy.open}
          </Link>
        ) : (
          <div className={styles.mobileActions}>
            <Link href="/login" className={styles.btnGhost}>
              {copy.signIn}
            </Link>
            <Link href="/register" className={styles.btnPrimary}>
              {copy.start}
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
