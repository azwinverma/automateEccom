"use client";

import type { AdminAuditEntry, AdminFeatureFlag } from "@commerce-os/api-client";
import { useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { Checkbox, SelectField, TextField } from "@/components/ui/Field";
import { Badge, useToast, type Tone } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ConsoleHead } from "./ConsoleShell";
import { C } from "./copy";
import { ErrorLine } from "./MerchantsView";
import styles from "./console.module.css";

const EVENT_TONE: Record<string, Tone> = {
  processed: "success",
  dispatched: "success",
  received: "info",
  pending: "info",
  ignored: "neutral",
  failed: "warning",
  dead: "danger",
};

function useRowAction() {
  const toast = useToast();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const run = async (id: string, fn: () => Promise<unknown>, done: string, after: () => void) => {
    setBusy(id);
    setError(null);
    try {
      await fn();
      toast(done);
      after();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(null);
    }
  };
  return { busy, error, run };
}

/* ---------- Webhooks ---------- */
export function WebhooksView() {
  const { api } = useAuth();
  const { dateTime } = useI18n();
  const [status, setStatus] = useState("");
  const [provider, setProvider] = useState("");
  const list = useApiQuery((a) => a.admin.webhooks({ status: status || undefined, provider: provider || undefined, limit: 100 }), [status, provider]);
  const act = useRowAction();
  return (
    <>
      <ConsoleHead title={C.webhooks.title} subtitle={C.webhooks.subtitle}>
        <SelectField label={C.common.status} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">{C.audit.any}</option>
          {["received", "processed", "ignored", "failed", "dead"].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </SelectField>
        <TextField label={C.webhooks.provider} value={provider} onChange={(e) => setProvider(e.target.value.trim())} maxLength={40} />
      </ConsoleHead>
      <ErrorLine error={act.error} />
      {list.state.status === "loading" ? (
        <TableSkeleton columns="1fr 1fr 1fr 1fr" label={C.common.loading} />
      ) : list.state.status === "error" ? (
        <QueryError error={list.state.error} onRetry={list.reload} />
      ) : list.state.data.items.length === 0 ? (
        <EmptyState title={C.common.noResults} />
      ) : (
        <div className={table.wrap}>
          <table className={[table.table, table.dense].join(" ")} data-testid="webhooks">
            <thead>
              <tr>
                <th scope="col">{C.webhooks.colEvent}</th>
                <th scope="col">{C.common.status}</th>
                <th scope="col" className={table.num}>
                  {C.webhooks.colAttempts}
                </th>
                <th scope="col" className={table.num}>
                  {C.webhooks.colDupes}
                </th>
                <th scope="col">{C.webhooks.colReceived}</th>
                <th scope="col" className={table.actions}>
                  <span className="srOnly">{C.common.actions}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {list.state.data.items.map((w) => (
                <tr key={w.id}>
                  <td>
                    <div className={table.primaryCell}>
                      <strong>{w.event_type}</strong>
                      <span>{w.provider}</span>
                    </div>
                  </td>
                  <td>
                    <Badge tone={EVENT_TONE[w.status] ?? "neutral"}>{w.status}</Badge>
                    {w.last_error ? <span className={[styles.muted, styles.err].join(" ")} title={w.last_error}>{w.last_error}</span> : null}
                  </td>
                  <td className={table.num}>{w.attempts}</td>
                  <td className={table.num}>{w.duplicates}</td>
                  <td className={styles.muted}>{dateTime(w.received_at)}</td>
                  <td className={table.actions}>
                    {w.status === "failed" || w.status === "dead" || w.status === "ignored" ? (
                      <Button
                        size="sm"
                        loading={act.busy === w.id}
                        disabled={act.busy !== null}
                        onClick={() => act.run(w.id, () => api.admin.replayWebhook(w.id), C.webhooks.replayed, list.reload)}
                        aria-label={`${C.webhooks.replay}: ${w.event_type}`}
                      >
                        {C.webhooks.replay}
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

/* ---------- Outbox ---------- */
export function OutboxView() {
  const { api } = useAuth();
  const { dateTime } = useI18n();
  const [status, setStatus] = useState<"dead" | "pending" | "dispatched">("dead");
  const list = useApiQuery((a) => a.admin.outbox(status), [status]);
  const act = useRowAction();
  return (
    <>
      <ConsoleHead title={C.outbox.title} subtitle={C.outbox.subtitle}>
        <SelectField label={C.common.status} value={status} onChange={(e) => setStatus(e.target.value as typeof status)}>
          <option value="dead">dead</option>
          <option value="pending">pending</option>
          <option value="dispatched">dispatched</option>
        </SelectField>
      </ConsoleHead>
      <ErrorLine error={act.error} />
      {list.state.status === "loading" ? (
        <TableSkeleton columns="1fr 1fr 1fr" label={C.common.loading} />
      ) : list.state.status === "error" ? (
        <QueryError error={list.state.error} onRetry={list.reload} />
      ) : list.state.data.items.length === 0 ? (
        <EmptyState title={status === "dead" ? C.outbox.deadEmpty : C.common.noResults} />
      ) : (
        <div className={table.wrap}>
          <table className={[table.table, table.dense].join(" ")} data-testid="outbox">
            <thead>
              <tr>
                <th scope="col">{C.outbox.colEvent}</th>
                <th scope="col" className={table.num}>
                  {C.outbox.colAttempts}
                </th>
                <th scope="col">{C.outbox.colError}</th>
                <th scope="col">{C.outbox.colCreated}</th>
                <th scope="col" className={table.actions}>
                  <span className="srOnly">{C.common.actions}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {list.state.data.items.map((e) => (
                <tr key={e.id}>
                  <td>
                    <div className={table.primaryCell}>
                      <strong>{e.event_type}</strong>
                      <span className={styles.mono}>{e.merchant_id ?? "platform"}</span>
                    </div>
                  </td>
                  <td className={table.num}>{e.attempts}</td>
                  <td>{e.last_error ? <span className={[styles.muted, styles.err].join(" ")} title={e.last_error}>{e.last_error}</span> : null}</td>
                  <td className={styles.muted}>{dateTime(e.created_at)}</td>
                  <td className={table.actions}>
                    {e.status === "dead" ? (
                      <Button
                        size="sm"
                        loading={act.busy === e.id}
                        disabled={act.busy !== null}
                        onClick={() => act.run(e.id, () => api.admin.retryOutbox(e.id), C.outbox.retried, list.reload)}
                        aria-label={`${C.outbox.retry}: ${e.event_type}`}
                      >
                        {C.outbox.retry}
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

/* ---------- AI providers ---------- */
const CIRCUIT_TONE: Record<string, Tone> = { closed: "success", half_open: "warning", open: "danger", unknown: "neutral" };

export function ProvidersView() {
  const list = useApiQuery((a) => a.admin.providers());
  return (
    <>
      <ConsoleHead title={C.ai.title} subtitle={C.ai.subtitle}>
        <Button size="sm" onClick={list.reload}>
          {C.common.retry}
        </Button>
      </ConsoleHead>
      {list.state.status === "loading" ? (
        <TableSkeleton columns="1fr 1fr 1fr" label={C.common.loading} />
      ) : list.state.status === "error" ? (
        <QueryError error={list.state.error} onRetry={list.reload} />
      ) : (
        <div className={table.wrap}>
          <table className={[table.table, table.dense].join(" ")} data-testid="providers">
            <thead>
              <tr>
                <th scope="col">{C.ai.colProvider}</th>
                <th scope="col">{C.ai.colModel}</th>
                <th scope="col">{C.ai.colConfigured}</th>
                <th scope="col">{C.ai.colState}</th>
                <th scope="col" className={table.num}>
                  {C.ai.colSuccess}
                </th>
                <th scope="col" className={table.num}>
                  {C.ai.colLatency}
                </th>
              </tr>
            </thead>
            <tbody>
              {list.state.data.items.map((p) => (
                <tr key={`${p.provider}:${p.model}`}>
                  <td>{p.provider}</td>
                  <td className={styles.mono}>{p.model}</td>
                  <td>
                    <Badge tone={p.configured ? "success" : "warning"}>{p.configured ? C.ai.configured : C.ai.missing}</Badge>
                  </td>
                  <td>
                    <Badge tone={CIRCUIT_TONE[p.state] ?? "neutral"}>{p.state}</Badge>
                  </td>
                  <td className={table.num}>
                    {p.success_rate_1h == null ? "–" : `${Math.round(p.success_rate_1h * 100)}% (${p.attempts_1h ?? 0})`}
                  </td>
                  <td className={table.num}>{p.last_latency_ms == null ? "–" : `${p.last_latency_ms} ms`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

/* ---------- Feature flags ---------- */
const EMPTY_FLAG: AdminFeatureFlag = { key: "", description: "", default_enabled: false, rollout_percentage: 0, kill_switch: false };

export function FlagsView() {
  const { api } = useAuth();
  const toast = useToast();
  const list = useApiQuery((a) => a.admin.flags());
  const [editing, setEditing] = useState<AdminFeatureFlag | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!editing) return;
    setBusy(true);
    setError(null);
    try {
      const { key, ...body } = editing;
      await api.admin.upsertFlag(key.trim(), body);
      toast(C.flags.saved);
      setEditing(null);
      list.reload();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <ConsoleHead title={C.flags.title} subtitle={C.flags.subtitle}>
        <Button size="sm" variant="primary" onClick={() => setEditing({ ...EMPTY_FLAG })}>
          {C.flags.newFlag}
        </Button>
      </ConsoleHead>
      <ErrorLine error={error} />
      {editing ? (
        <form className={styles.form} onSubmit={save} aria-label={C.flags.save} style={{ marginBottom: "var(--space-4)" }}>
          <div className={styles.formRow}>
            <TextField
              label={C.flags.key}
              value={editing.key}
              onChange={(e) => setEditing({ ...editing, key: e.target.value })}
              required
              pattern="[a-z0-9._-]+"
              maxLength={80}
              mono
            />
            <TextField
              label={C.flags.rollout}
              type="number"
              min={0}
              max={100}
              value={editing.rollout_percentage}
              onChange={(e) => setEditing({ ...editing, rollout_percentage: Number(e.target.value) })}
            />
          </div>
          <TextField label={C.flags.description} value={editing.description} onChange={(e) => setEditing({ ...editing, description: e.target.value })} maxLength={500} />
          <Checkbox label={C.flags.colDefault} checked={editing.default_enabled} onChange={(e) => setEditing({ ...editing, default_enabled: e.target.checked })} />
          <Checkbox label={C.flags.colKill} checked={editing.kill_switch} onChange={(e) => setEditing({ ...editing, kill_switch: e.target.checked })} />
          <div className={styles.actionsRow}>
            <Button type="submit" variant="primary" size="sm" loading={busy}>
              {C.flags.save}
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => setEditing(null)}>
              {C.common.cancel}
            </Button>
          </div>
        </form>
      ) : null}
      {list.state.status === "loading" ? (
        <TableSkeleton columns="1fr 1fr 1fr" label={C.common.loading} />
      ) : list.state.status === "error" ? (
        <QueryError error={list.state.error} onRetry={list.reload} />
      ) : list.state.data.items.length === 0 ? (
        <EmptyState title={C.common.noResults} />
      ) : (
        <div className={table.wrap}>
          <table className={[table.table, table.dense].join(" ")} data-testid="flags">
            <thead>
              <tr>
                <th scope="col">{C.flags.colKey}</th>
                <th scope="col">{C.flags.colDefault}</th>
                <th scope="col" className={table.num}>
                  {C.flags.colRollout}
                </th>
                <th scope="col">{C.flags.colKill}</th>
                <th scope="col" className={table.actions}>
                  <span className="srOnly">{C.common.actions}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {list.state.data.items.map((f) => (
                <tr key={f.key}>
                  <td>
                    <div className={table.primaryCell}>
                      <strong className={styles.mono}>{f.key}</strong>
                      <span>{f.description}</span>
                    </div>
                  </td>
                  <td>{f.default_enabled ? C.flags.on : C.flags.off}</td>
                  <td className={table.num}>{f.rollout_percentage}%</td>
                  <td>{f.kill_switch ? <Badge tone="danger">{C.flags.on}</Badge> : C.flags.off}</td>
                  <td className={table.actions}>
                    <Button size="sm" variant="ghost" onClick={() => setEditing({ ...f })} aria-label={`${C.flags.edit}: ${f.key}`}>
                      {C.flags.edit}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

/* ---------- Audit ---------- */
export function AuditView() {
  const { api } = useAuth();
  const { dateTime } = useI18n();
  const params = useSearchParams();
  const [merchant, setMerchant] = useState(params.get("merchant_id") ?? "");
  const [actor, setActor] = useState("");
  const [action, setAction] = useState("");
  const [items, setItems] = useState<AdminAuditEntry[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  const q = { merchant_id: /^[0-9a-f-]{36}$/i.test(merchant) ? merchant : undefined, actor_type: actor || undefined, action: action || undefined, limit: 50 };
  const key = JSON.stringify(q);

  const load = async (after?: string) => {
    setLoading(true);
    setError(null);
    try {
      const page = await api.admin.audit({ ...q, cursor: after });
      setItems((prev) => (after ? [...prev, ...page.items] : page.items));
      setCursor(page.next_cursor);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return (
    <>
      <ConsoleHead title={C.audit.title} subtitle={C.audit.subtitle}>
        <TextField label={C.audit.merchant} value={merchant} onChange={(e) => setMerchant(e.target.value.trim())} mono maxLength={36} />
        <SelectField label={C.audit.actor} value={actor} onChange={(e) => setActor(e.target.value)}>
          <option value="">{C.audit.any}</option>
          {["staff", "user", "system", "automation", "ai", "webhook"].map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </SelectField>
        <TextField label={C.audit.action} value={action} onChange={(e) => setAction(e.target.value.trim())} maxLength={100} mono />
      </ConsoleHead>
      {error ? <QueryError error={error} onRetry={() => load()} /> : null}
      {loading && items.length === 0 ? (
        <TableSkeleton columns="1fr 1fr 2fr 1fr" label={C.common.loading} />
      ) : items.length === 0 && !error ? (
        <EmptyState title={C.common.noResults} />
      ) : (
        <div className={table.wrap}>
          <table className={[table.table, table.dense].join(" ")} data-testid="audit">
            <thead>
              <tr>
                <th scope="col">{C.audit.colWhen}</th>
                <th scope="col">{C.audit.colActor}</th>
                <th scope="col">{C.audit.colAction}</th>
                <th scope="col">{C.audit.colResource}</th>
                <th scope="col">{C.audit.colShop}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id}>
                  <td className={styles.muted}>{dateTime(a.occurred_at)}</td>
                  <td>
                    <div className={table.primaryCell}>
                      <strong>{a.actor.display ?? a.actor.type}</strong>
                      <span>{a.actor.type}</span>
                    </div>
                  </td>
                  <td>
                    <div className={table.primaryCell}>
                      <strong className={styles.mono}>{a.action}</strong>
                      {a.metadata && typeof a.metadata.reason === "string" ? <span>{a.metadata.reason}</span> : null}
                    </div>
                  </td>
                  <td className={styles.mono}>
                    {a.resource_type}
                    {a.resource_id ? `:${a.resource_id.slice(0, 8)}` : ""}
                  </td>
                  <td className={styles.mono}>{a.merchant_id ? a.merchant_id.slice(0, 8) : "platform"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {cursor ? (
        <div style={{ marginTop: "var(--space-3)" }}>
          <Button size="sm" loading={loading} onClick={() => load(cursor)}>
            {C.audit.more}
          </Button>
        </div>
      ) : null}
    </>
  );
}
