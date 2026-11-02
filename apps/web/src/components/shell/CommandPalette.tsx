"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useRouter } from "next/navigation";
import { useEffect, useId, useMemo, useState, type KeyboardEvent } from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { confirmLeave } from "@/lib/navigationGuard";
import { SECTIONS, SETTINGS_PAGES } from "@/lib/sections";
import { Icon, type IconName } from "../ui/Icon";
import styles from "./shell.module.css";

interface Entry {
  id: string;
  label: string;
  href: string;
  icon: IconName;
  group: "pages" | "settings";
  phase?: number;
  keywords: string;
}

export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const { t, number } = useI18n();
  const router = useRouter();
  const listId = useId();
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);

  const entries = useMemo<Entry[]>(
    () => [
      ...SECTIONS.map((s) => ({
        id: `p-${s.key}`,
        label: t(`nav.${s.key}`),
        href: s.href,
        icon: s.icon,
        group: "pages" as const,
        phase: s.phase,
        keywords: s.key,
      })),
      ...SETTINGS_PAGES.map((s) => ({
        id: `s-${s.key}`,
        label: t(`settings.${s.key}`),
        href: s.href,
        icon: s.icon,
        group: "settings" as const,
        keywords: `settings ${s.key}`,
      })),
    ],
    [t],
  );

  const q = query.trim().toLowerCase();
  const results = q ? entries.filter((e) => e.label.toLowerCase().includes(q) || e.keywords.includes(q)) : entries;

  useEffect(() => {
    setActive(0);
  }, [q]);
  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  const go = (entry: Entry | undefined) => {
    if (!entry || !confirmLeave()) return;
    onOpenChange(false);
    router.push(entry.href);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => (results.length ? (i + 1) % results.length : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (results.length ? (i - 1 + results.length) % results.length : 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      go(results[active]);
    }
  };

  const optionId = (i: number) => `${listId}-opt-${i}`;
  let lastGroup: Entry["group"] | null = null;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className={styles.scrim} />
        <Dialog.Content className={styles.palette} aria-describedby={undefined}>
          <Dialog.Title className="srOnly">{t("command.title")}</Dialog.Title>
          <div className={styles.paletteInputRow}>
            <Icon name="search" />
            <input
              className={styles.paletteInput}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={t("command.placeholder")}
              aria-label={t("command.placeholder")}
              role="combobox"
              aria-expanded="true"
              aria-controls={listId}
              aria-autocomplete="list"
              aria-activedescendant={results.length ? optionId(active) : undefined}
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          {results.length === 0 ? (
            <p className={styles.paletteEmpty} role="status">
              {t("command.empty", { query })}
            </p>
          ) : (
            <ul id={listId} role="listbox" className={styles.paletteList} aria-label={t("command.title")}>
              {results.map((entry, i) => {
                const header =
                  entry.group !== lastGroup ? (
                    <li role="presentation" className={styles.paletteGroup} key={`g-${entry.group}`}>
                      {t(entry.group === "pages" ? "command.groupPages" : "command.groupSettings")}
                    </li>
                  ) : null;
                lastGroup = entry.group;
                return [
                  header,
                  <li
                    key={entry.id}
                    id={optionId(i)}
                    role="option"
                    aria-selected={i === active}
                    className={styles.paletteOption}
                    onMouseMove={() => setActive(i)}
                    onClick={() => go(entry)}
                  >
                    <Icon name={entry.icon} />
                    {entry.label}
                    {entry.phase ? <span className={styles.phase}>{t("nav.phaseShort", { phase: number(entry.phase) })}</span> : null}
                  </li>,
                ];
              })}
            </ul>
          )}
          <p className={styles.paletteHint} aria-hidden="true">
            {t("command.hint")}
          </p>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
