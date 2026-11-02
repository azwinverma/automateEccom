"use client";

import type { AuditLogEntry, AuditLogQuery } from "@commerce-os/api-client";
import { useEffect, useState, type FormEvent } from "react";
import { EmptyState, ErrorState, QueryError, TableSkeleton, isPermissionDenied } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { TextField } from "@/components/ui/Field";
import { Badge, PageHeader, type Tone } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatValue, normalizeChanges, shortId } from "@/lib/audit";
import styles from "./settings.module.css";

const PAGE_SIZE = 50;
type Filters = Required<Pick<AuditLogQuery, "action" | "actor_id" | "resource_type" | "resource_id">>;
const EMPTY: Filters = { action: "", actor_id: "", resource_type: "", resource_id: "" };

type ListState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; items: AuditLogEntry[]; next: string | null; loadingMore: boolean; moreError: unknown };

const ACTOR_TONE: Record<string, Tone> = { user: "neutral", system: "info", automation: "automated", ai: "automated" };

function Detail({ entry }: { entry: AuditLogEntry }) {
  const { t, dateTime } = useI18n();
  const rows = normalizeChanges(entry.changes);
  const meta = entry.metadata && Object.keys(entry.metadata).length ? entry.metadata : null;
  return (
    <>
      <dl className={styles.detailList}>
        <dt>{t("audit.detailWhen")}</dt>
        <dd>{dateTime(entry.occurred_at)}</dd>
        <dt>{t("audit.detailActor")}</dt>
        <dd>
          {t.dynamic(`audit.actor.${entry.actor.type}`) ?? entry.actor.type}
          {entry.actor.display ? ` · ${entry.actor.display}` : ""}
          {entry.actor.id ? <div className={table.mono}>{entry.actor.id}</div> : null}
        </dd>
        <dt>{t("audit.detailResource")}</dt>
        <dd>
          {entry.resource_type}
          {entry.resource_id ? <div className={table.mono}>{entry.resource_id}</div> : null}
        </dd>
        {entry.source ? (
          <>
            <dt>{t("audit.detailSource")}</dt>
            <dd>{entry.source}</dd>
          </>
        ) : null}
        {entry.ip ? (
          <>
            <dt>{t("audit.detailIp")}</dt>
            <dd className={table.mono}>{entry.ip}</dd>
          </>
        ) : null}
        {entry.request_id ? (
          <>
            <dt>{t("audit.detailRequest")}</dt>
            <dd className={table.mono}>{entry.request_id}</dd>
          </>
        ) : null}
      </dl>

      <h3 style={{ marginBottom: "var(--space-2)" }}>{t("audit.changes")}</h3>
      {rows.length === 0 ? (
        <p className={table.empty}>{t("audit.noChanges")}</p>
      ) : (
        <div className={table.wrap}>
          <table className={[table.table, table.dense].join(" ")}>
            <thead>
              <tr>
                <th scope="col">{t("audit.field")}</th>
                <th scope="col">{t("audit.before")}</th>
                <th scope="col">{t("audit.after")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.field}>
                  <td className={table.mono}>{r.field}</td>
                  <td>{r.before === undefined ? <span className={table.muted}>{t("common.none")}</span> : <span className={styles.diffBefore}>{formatValue(r.before)}</span>}</td>
                  <td>{r.after === undefined ? <span className={table.muted}>{t("common.none")}</span> : <span className={styles.diffAfter}>{formatValue(r.after)}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {meta ? (
        <>
          <h3 style={{ margin: "var(--space-6) 0 var(--space-2)" }}>{t("audit.metadata")}</h3>
          <pre className={styles.pre}>{JSON.stringify(meta, null, 2)}</pre>
        </>
      ) : null}
    </>
  );
}

export function AuditView() {
  const { t, dateTime, relative } = useI18n();
  const { api, merchantId, membership } = useAuth();
  const [draft, setDraft] = useState<Filters>(EMPTY);
  const [applied, setApplied] = useState<Filters>(EMPTY);
  const [state, setState] = useState<ListState>({ status: "loading" });
  const [nonce, setNonce] = useState(0);
  const [selected, setSelected] = useState<AuditLogEntry | null>(null);
  const filtered = Object.values(applied).some(Boolean);

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });
    api.audit.list({ ...applied, limit: PAGE_SIZE }).then(
      (page) => !cancelled && setState({ status: "ready", items: page.items, next: page.next_cursor, loadingMore: false, moreError: null }),
      (error: unknown) => !cancelled && setState({ status: "error", error }),
    );
    return () => {
      cancelled = true;
    };
  }, [api, applied, merchantId, nonce]);

  const loadMore = async () => {
    if (state.status !== "ready" || !state.next || state.loadingMore) return;
    const cursor = state.next;
    setState({ ...state, loadingMore: true, moreError: null });
    try {
      const page = await api.audit.list({ ...applied, limit: PAGE_SIZE, cursor });
      setState((s) =>
        s.status === "ready" ? { status: "ready", items: [...s.items, ...page.items], next: page.next_cursor, loadingMore: false, moreError: null } : s,
      );
    } catch (error) {
      setState((s) => (s.status === "ready" ? { ...s, loadingMore: false, moreError: error } : s));
    }
  };

  const apply = (e: FormEvent) => {
    e.preventDefault();
    setApplied({
      action: draft.action.trim(),
      actor_id: draft.actor_id.trim(),
      resource_type: draft.resource_type.trim(),
      resource_id: draft.resource_id.trim(),
    });
  };
  const clear = () => {
    setDraft(EMPTY);
    setApplied(EMPTY);
  };
  const setField = (k: keyof Filters) => (e: { target: { value: string } }) => setDraft((d) => ({ ...d, [k]: e.target.value }));

  const denied = state.status === "error" && isPermissionDenied(state.error);

  return (
    <>
      <PageHeader level={2} title={t("audit.title")} subtitle={t("audit.subtitle", { business: membership?.merchant.name ?? "" })} />

      {denied ? null : (
        <form className={styles.filters} onSubmit={apply} role="search" aria-label={t("audit.filters")}>
          <TextField label={t("audit.filterAction")} placeholder={t("audit.filterActionPlaceholder")} value={draft.action} onChange={setField("action")} mono />
          <TextField label={t("audit.filterActor")} value={draft.actor_id} onChange={setField("actor_id")} mono />
          <TextField label={t("audit.filterResourceType")} value={draft.resource_type} onChange={setField("resource_type")} mono />
          <TextField label={t("audit.filterResourceId")} value={draft.resource_id} onChange={setField("resource_id")} mono />
          <div className={styles.filterActions}>
            <Button type="submit" variant="primary">
              {t("common.apply")}
            </Button>
            {filtered ? (
              <Button variant="ghost" onClick={clear}>
                {t("common.clear")}
              </Button>
            ) : null}
          </div>
        </form>
      )}

      {state.status === "loading" ? (
        <TableSkeleton columns="1fr 1.4fr 1.4fr 1.2fr 0.8fr" rows={8} label={t("common.loading")} />
      ) : state.status === "error" ? (
        <QueryError error={state.error} onRetry={() => setNonce((n) => n + 1)} />
      ) : state.items.length === 0 ? (
        <EmptyState title={filtered ? t("audit.emptyFiltered") : t("audit.empty")} />
      ) : (
        <>
          <div className={table.wrap}>
            <table className={[table.table, table.dense].join(" ")} aria-label={t("audit.title")}>
              <thead>
                <tr>
                  <th scope="col">{t("audit.colTime")}</th>
                  <th scope="col">{t("audit.colActor")}</th>
                  <th scope="col">{t("audit.colAction")}</th>
                  <th scope="col" className={table.hideSm}>
                    {t("audit.colResource")}
                  </th>
                  <th scope="col" className={table.hideSm}>
                    {t("audit.colSource")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {state.items.map((e) => (
                  <tr key={e.id} className={table.clickable} onClick={() => setSelected(e)}>
                    <td className={table.muted} style={{ whiteSpace: "nowrap" }}>
                      <time dateTime={e.occurred_at} title={dateTime(e.occurred_at)}>
                        {relative(e.occurred_at)}
                      </time>
                    </td>
                    <td>
                      <span className={styles.actorCell}>
                        <Badge tone={ACTOR_TONE[e.actor.type] ?? "neutral"} dot={false}>
                          {t.dynamic(`audit.actor.${e.actor.type}`) ?? e.actor.type}
                        </Badge>
                        <span className={styles.actorName}>{e.actor.display ?? shortId(e.actor.id)}</span>
                      </span>
                    </td>
                    <td>
                      <button
                        type="button"
                        className={table.mono}
                        style={{ background: "none", border: 0, padding: 0, cursor: "pointer", textAlign: "left", color: "var(--text-primary)" }}
                        onClick={(ev) => {
                          ev.stopPropagation();
                          setSelected(e);
                        }}
                      >
                        {e.action}
                      </button>
                    </td>
                    <td className={table.hideSm}>
                      <span>{e.resource_type}</span> <span className={[table.mono, table.muted].join(" ")}>{shortId(e.resource_id)}</span>
                    </td>
                    <td className={[table.hideSm, table.muted].join(" ")}>{e.source ?? t("common.none")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {state.moreError ? <ErrorState error={state.moreError} onRetry={loadMore} /> : null}
          <div className={styles.listEnd}>
            {state.next ? (
              <Button onClick={loadMore} loading={state.loadingMore}>
                {t("common.loadMore")}
              </Button>
            ) : (
              <span>{t("audit.end")}</span>
            )}
          </div>
        </>
      )}

      <Drawer
        open={selected !== null}
        onOpenChange={(o) => !o && setSelected(null)}
        title={selected ? <code>{selected.action}</code> : t("audit.detailTitle")}
        description={t("audit.detailTitle")}
        wide
      >
        {selected ? <Detail entry={selected} /> : null}
      </Drawer>
    </>
  );
}
