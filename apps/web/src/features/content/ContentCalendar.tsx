"use client";

import type { ContentPost } from "@commerce-os/api-client";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Badge, PageHeader, SectionHeader } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { INTL_LOCALE } from "@/i18n/config";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { isUnscheduledWork } from "@/lib/content/actions";
import { addDays, addMonths, dayKey, monthGrid, timeOf, utcRange, weekDays } from "@/lib/content/calendar";
import wf from "../shared/workflow.module.css";
import { ContentTabs } from "./ContentTabs";
import styles from "./content.module.css";
import { NewPostDrawer } from "./NewPostDrawer";
import { POST_TONE, PostDrawer, SourceTag } from "./PostDrawer";
import { useMerchantTimezone } from "./useMerchantTimezone";

const MONTH_CELL_MAX = 3;

function utcDate(key: string): Date {
  const [y, m, d] = key.split("-").map(Number) as [number, number, number];
  return new Date(Date.UTC(y, m - 1, d, 12));
}

export function ContentCalendar() {
  const { t, locale, relative } = useI18n();
  const { can } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const tz = useMerchantTimezone();
  const today = dayKey(new Date(), tz);
  const [view, setView] = useState<"week" | "month">("week");
  const [anchor, setAnchor] = useState(today);
  const [openId, setOpenId] = useState<string | null>(params.get("post"));
  const [newOpen, setNewOpen] = useState(false);

  const days = view === "week" ? weekDays(anchor) : monthGrid(anchor);
  const range = utcRange(days, tz);
  const scheduled = useApiQuery((a) => a.content.posts(range), [range.from, range.to]);
  // No unscheduled filter or single-post read exists, so the unfiltered list (≤500) backs both.
  const all = useApiQuery((a) => a.content.posts());
  const connections = useApiQuery((a) => a.channels.list());
  const connById = useMemo(
    () => new Map((connections.state.status === "success" ? connections.state.data.items : []).map((c) => [c.id, c])),
    [connections.state],
  );

  const byDay = useMemo(() => {
    const m = new Map<string, ContentPost[]>();
    if (scheduled.state.status !== "success") return m;
    for (const p of scheduled.state.data.items) {
      if (!p.scheduled_at) continue;
      const k = dayKey(p.scheduled_at, tz);
      m.set(k, [...(m.get(k) ?? []), p]);
    }
    for (const list of m.values()) list.sort((a, b) => a.scheduled_at!.localeCompare(b.scheduled_at!));
    return m;
  }, [scheduled.state, tz]);

  const allPosts = all.state.status === "success" ? all.state.data.items : [];
  const unscheduled = allPosts.filter(isUnscheduledWork);
  const openPost =
    allPosts.find((p) => p.id === openId) ??
    (scheduled.state.status === "success" ? scheduled.state.data.items.find((p) => p.id === openId) : undefined) ??
    null;

  const monthFmt = new Intl.DateTimeFormat(INTL_LOCALE[locale], { month: "long", year: "numeric", timeZone: "UTC", numberingSystem: "latn" });
  const dayFmt = new Intl.DateTimeFormat(INTL_LOCALE[locale], { month: "short", day: "numeric", timeZone: "UTC", numberingSystem: "latn" });
  const periodLabel = view === "month" ? monthFmt.format(utcDate(anchor)) : `${dayFmt.format(utcDate(days[0]!))} – ${dayFmt.format(utcDate(days[6]!))}`;
  const month = anchor.slice(0, 7);

  const move = (dir: 1 | -1) => setAnchor((a) => (view === "week" ? addDays(a, 7 * dir) : addMonths(a, dir)));
  const reload = () => {
    scheduled.reload();
    all.reload();
  };
  const close = () => {
    setOpenId(null);
    if (params.get("post")) router.replace("/content");
  };

  const chip = (p: ContentPost) => (
    <button
      key={p.id}
      type="button"
      className={[styles.chip, styles[`s_${p.status}`]].filter(Boolean).join(" ")}
      onClick={() => setOpenId(p.id)}
    >
      <span className={styles.chipTime}>{timeOf(p.scheduled_at!, tz)}</span>
      {/* The accessible name is the visible text plus channel and status (WCAG 2.5.3 label in name). */}
      <span className="srOnly">
        {` · ${connById.get(p.connection_id)?.display_name ?? ""} · ${t(`content.status.${p.status}`)} · `}
      </span>
      <span className={styles.chipText}>{p.caption}</span>
    </button>
  );

  return (
    <>
      <PageHeader
        title={t("content.title")}
        subtitle={t("content.subtitle")}
        actions={
          <>
            {can("media.write") ? (
              <ButtonLink href="/content/reels?new=1">
                <Icon name="content" />
                {t("content.makeReel")}
              </ButtonLink>
            ) : null}
            {can("content.write") ? (
              <Button variant="primary" onClick={() => setNewOpen(true)}>
                <Icon name="plus" />
                {t("content.newPost")}
              </Button>
            ) : null}
          </>
        }
      />
      <ContentTabs />

      <div className={styles.toolbar}>
        <div className={styles.nav}>
          <Button size="sm" iconOnly aria-label={t("content.prev")} onClick={() => move(-1)}>
            <Icon name="chevronRight" style={{ transform: "rotate(180deg)" }} />
          </Button>
          <Button size="sm" onClick={() => setAnchor(today)}>
            {t("content.today")}
          </Button>
          <Button size="sm" iconOnly aria-label={t("content.next")} onClick={() => move(1)}>
            <Icon name="chevronRight" />
          </Button>
          <h2 className={styles.period} aria-live="polite">
            {periodLabel}
          </h2>
        </div>
        <div className={styles.nav}>
          <span className={wf.hint}>{t("content.tzNote", { tz })}</span>
          <div className={styles.segmented} role="group" aria-label={t("content.viewLabel")}>
            {(["week", "month"] as const).map((v) => (
              <button key={v} type="button" aria-pressed={view === v} onClick={() => setView(v)}>
                {t(`content.${v}`)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {scheduled.state.status === "error" ? (
        <QueryError error={scheduled.state.error} onRetry={scheduled.reload} />
      ) : (
        <div className={styles.grid} data-testid="calendar" aria-busy={scheduled.state.status === "loading"}>
          {[0, 1, 2, 3, 4, 5, 6].map((d) => (
            <div key={d} className={styles.dow} aria-hidden="true">
              {t(`content.weekday.d${d}` as "content.weekday.d0")}
            </div>
          ))}
          {days.map((k) => {
            const posts = byDay.get(k) ?? [];
            const shown = view === "month" ? posts.slice(0, MONTH_CELL_MAX) : posts;
            return (
              <div
                key={k}
                className={[styles.day, view === "week" && styles.weekDay, view === "month" && k.slice(0, 7) !== month && styles.dayOther, k === today && styles.today]
                  .filter(Boolean)
                  .join(" ")}
                data-day={k}
              >
                <span className={styles.dayNum}>{Number(k.slice(8))}</span>
                {shown.map(chip)}
                {posts.length > shown.length ? (
                  <button
                    type="button"
                    className={[styles.linkButton, styles.more].join(" ")}
                    onClick={() => {
                      setAnchor(k);
                      setView("week");
                    }}
                  >
                    {t("content.morePosts", { count: posts.length - shown.length })}
                  </button>
                ) : null}
              </div>
            );
          })}
        </div>
      )}
      {scheduled.state.status === "success" && scheduled.state.data.items.length === 0 ? (
        <p className={wf.hint} style={{ paddingTop: "var(--space-2)" }}>
          {t("content.emptyRange")}
        </p>
      ) : null}

      <SectionHeader title={t("content.unscheduled")} id="unscheduled-heading" />
      {all.state.status === "loading" ? (
        <TableSkeleton columns="2fr 1fr 1fr 0.8fr 0.8fr" rows={3} label={t("common.loading")} />
      ) : all.state.status === "error" ? (
        <QueryError error={all.state.error} onRetry={all.reload} />
      ) : unscheduled.length === 0 ? (
        <EmptyState title={t("content.unscheduledEmpty")} />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-labelledby="unscheduled-heading" data-testid="unscheduled">
            <thead>
              <tr>
                <th scope="col">{t("content.colPost")}</th>
                <th scope="col" className={table.hideSm}>
                  {t("content.colChannel")}
                </th>
                <th scope="col">{t("content.colStatus")}</th>
                <th scope="col" className={table.hideSm}>
                  {t("content.colSource")}
                </th>
                <th scope="col" className={table.hideSm}>
                  {t("content.colCreated")}
                </th>
              </tr>
            </thead>
            <tbody>
              {unscheduled.map((p) => (
                <tr key={p.id}>
                  <td className={styles.captionCell}>
                    <button type="button" className={styles.linkButton} onClick={() => setOpenId(p.id)}>
                      {p.caption.slice(0, 80) || t(`content.kind.${p.kind}`)}
                    </button>
                  </td>
                  <td className={table.hideSm}>{connById.get(p.connection_id)?.display_name ?? t("content.unknownChannel")}</td>
                  <td>
                    <Badge tone={POST_TONE[p.status] ?? "neutral"}>{t(`content.status.${p.status}`)}</Badge>
                  </td>
                  <td className={table.hideSm}>
                    <SourceTag source={p.source} />
                  </td>
                  <td className={[table.hideSm, table.muted].join(" ")}>{relative(p.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <PostDrawer
        post={openPost}
        connection={openPost ? connById.get(openPost.connection_id) : undefined}
        tz={tz}
        onClose={close}
        onChanged={() => reload()}
      />
      <NewPostDrawer
        open={newOpen}
        onOpenChange={setNewOpen}
        connections={connections.state.status === "success" ? connections.state.data.items : []}
        onCreated={() => {
          setNewOpen(false);
          reload();
        }}
      />
    </>
  );
}
