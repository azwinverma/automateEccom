"use client";

import { isApiError, type AdminMerchantDetail, type AdminMerchantSummary, type UsageLimit } from "@commerce-os/api-client";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { SelectField, TextField } from "@/components/ui/Field";
import { Badge, InlineAlert, RequestId, useToast, type Tone } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ConsoleHead } from "./ConsoleShell";
import { C, fmt } from "./copy";
import styles from "./console.module.css";

export const MERCHANT_TONE: Record<string, Tone> = { active: "success", suspended: "danger", closed: "neutral" };
const CONN_TONE: Record<string, Tone> = { connected: "success", expired: "warning", error: "danger", revoked: "danger" };

/** API errors in Console copy: the server message is already plain English for staff. */
export function ErrorLine({ error }: { error: unknown }) {
  if (!error) return null;
  const msg = isApiError(error) ? `${error.message || error.code} (${error.code})` : String(error);
  return (
    <InlineAlert tone="danger">
      {msg}
      <RequestId id={isApiError(error) ? error.requestId : null} />
    </InlineAlert>
  );
}

export function MerchantsView() {
  const { dateTime } = useI18n();
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [query, setQuery] = useState(q);
  const list = useApiQuery((a) => a.admin.merchants({ q: query || undefined, limit: 50 }), [query]);
  const selected = params.get("merchant");

  const open = (id: string | null) => {
    const next = new URLSearchParams(params.toString());
    if (id) next.set("merchant", id);
    else next.delete("merchant");
    router.replace(`${pathname}?${next.toString()}`, { scroll: false });
  };

  return (
    <>
      <ConsoleHead title={C.merchants.title} subtitle={C.merchants.subtitle}>
        <form
          role="search"
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(q.trim());
          }}
        >
          <TextField label={C.merchants.search} value={q} onChange={(e) => setQ(e.target.value)} type="search" maxLength={100} />
        </form>
      </ConsoleHead>
      {list.state.status === "loading" ? (
        <TableSkeleton columns="2fr 1fr 1fr 1fr" label={C.common.loading} />
      ) : list.state.status === "error" ? (
        <QueryError error={list.state.error} onRetry={list.reload} />
      ) : list.state.data.items.length === 0 ? (
        <EmptyState title={C.common.noResults} />
      ) : (
        <div className={table.wrap}>
          <table className={[table.table, table.dense].join(" ")} data-testid="merchants">
            <thead>
              <tr>
                <th scope="col">{C.merchants.colName}</th>
                <th scope="col">{C.merchants.colSlug}</th>
                <th scope="col">{C.common.status}</th>
                <th scope="col">{C.common.created}</th>
              </tr>
            </thead>
            <tbody>
              {list.state.data.items.map((m: AdminMerchantSummary) => (
                <tr key={m.id}>
                  <td>
                    <button type="button" className={styles.rowButton} onClick={() => open(m.id)}>
                      {m.name}
                    </button>
                  </td>
                  <td className={styles.mono}>{m.slug}</td>
                  <td>
                    <Badge tone={MERCHANT_TONE[m.status] ?? "neutral"}>{m.status}</Badge>
                  </td>
                  <td className={styles.muted}>{dateTime(m.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Drawer open={!!selected} onOpenChange={(o) => !o && open(null)} title={C.merchants.detailTitle} wide>
        {selected ? <MerchantDetail id={selected} onChanged={list.reload} /> : null}
      </Drawer>
    </>
  );
}

function usageText(u: UsageLimit): string {
  if (!u.included) return C.merchants.notIncluded;
  if (u.limit == null) return fmt(C.merchants.unlimited, { used: u.used ?? "–" });
  return fmt(C.merchants.used, { used: u.used ?? "–", limit: u.limit });
}

export function MerchantDetail({ id, onChanged }: { id: string; onChanged?: () => void }) {
  const { api } = useAuth();
  const { dateTime, relative } = useI18n();
  const toast = useToast();
  const detail = useApiQuery((a) => a.admin.merchant(id), [id]);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => setError(null), [id]);

  const run = async (key: string, fn: () => Promise<unknown>, done: string) => {
    setBusy(key);
    setError(null);
    try {
      const r = await fn();
      toast(typeof r === "string" ? r : done);
      detail.reload();
      onChanged?.();
      return true;
    } catch (e) {
      setError(e);
      return false;
    } finally {
      setBusy(null);
    }
  };

  if (detail.state.status === "loading") return <TableSkeleton columns="1fr 2fr" rows={6} label={C.common.loading} />;
  if (detail.state.status === "error") return <QueryError error={detail.state.error} onRetry={detail.reload} />;
  const d: AdminMerchantDetail = detail.state.data;
  const m = d.merchant;

  return (
    <div data-testid="merchant-detail">
      <h2 style={{ margin: "0 0 var(--space-3)", fontSize: "var(--font-size-lg)" }}>
        {m.name} <Badge tone={MERCHANT_TONE[m.status] ?? "neutral"}>{m.status}</Badge>
      </h2>
      <dl className={styles.dl}>
        <dt>ID</dt>
        <dd className={styles.mono}>{m.id}</dd>
        <dt>{C.merchants.plan}</dt>
        <dd>
          {d.plan ?? C.common.none} {d.subscription_status ? <span className={styles.muted}>({d.subscription_status})</span> : null}
        </dd>
        <dt>{C.merchants.credits}</dt>
        <dd>{d.credit_balance}</dd>
        <dt>{C.merchants.members}</dt>
        <dd>{d.members}</dd>
        <dt>{C.merchants.currency}</dt>
        <dd>
          {m.currency} · {m.country}
        </dd>
        <dt>{C.merchants.timezone}</dt>
        <dd>{m.timezone}</dd>
        <dt>{C.merchants.locale}</dt>
        <dd>{m.default_locale}</dd>
        <dt>{C.common.created}</dt>
        <dd>{dateTime(m.created_at)}</dd>
      </dl>
      <Link href={`/console/audit?merchant_id=${encodeURIComponent(m.id)}`}>{C.merchants.auditLink}</Link>
      <ErrorLine error={error} />

      <section className={styles.section} aria-labelledby="m-team">
        <h3 id="m-team">{C.merchants.team}</h3>
        <div className={table.wrap}>
          <table className={[table.table, table.dense].join(" ")}>
            <tbody>
              {d.team.map((t) => (
                <tr key={t.user_id}>
                  <td>
                    <div className={table.primaryCell}>
                      <strong>{t.full_name}</strong>
                      <span>{t.email}</span>
                    </div>
                  </td>
                  <td>{t.role}</td>
                  <td>{t.status}</td>
                  <td className={styles.muted}>{t.mfa_enabled ? C.merchants.mfaOn : C.merchants.mfaOff}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className={styles.section} aria-labelledby="m-usage">
        <h3 id="m-usage">{C.merchants.usage}</h3>
        <div className={table.wrap}>
          <table className={[table.table, table.dense].join(" ")} data-testid="merchant-usage">
            <tbody>
              {d.usage.map((u) => (
                <tr key={u.resource}>
                  <td className={styles.mono}>{u.resource}</td>
                  <td className={styles.muted}>{u.period}</td>
                  <td className={table.num}>{usageText(u)}</td>
                  <td>{u.alert_level && u.included ? <Badge tone={u.alert_level === "100" ? "danger" : "warning"}>{u.alert_level}%</Badge> : null}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className={styles.section} aria-labelledby="m-channels">
        <h3 id="m-channels">{C.merchants.channels}</h3>
        {d.connections.length === 0 ? (
          <p className={styles.muted}>{C.merchants.noChannels}</p>
        ) : (
          <div className={table.wrap}>
            <table className={[table.table, table.dense].join(" ")}>
              <tbody>
                {d.connections.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <div className={table.primaryCell}>
                        <strong>{c.display_name}</strong>
                        <span>{c.provider}</span>
                      </div>
                    </td>
                    <td>
                      <Badge tone={CONN_TONE[c.status] ?? "neutral"}>{c.status}</Badge>
                      {c.last_error_code ? <span className={styles.muted}> {c.last_error_code}</span> : null}
                    </td>
                    <td className={styles.muted}>
                      {c.last_healthy_at ? fmt(C.merchants.lastHealthy, { when: relative(c.last_healthy_at) }) : null}
                      {c.consecutive_failures ? ` · ${fmt(C.merchants.failures, { n: c.consecutive_failures })}` : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className={styles.section} aria-labelledby="m-overrides">
        <h3 id="m-overrides">{C.merchants.overrides}</h3>
        {d.overrides.length === 0 ? (
          <p className={styles.muted}>{C.merchants.noOverrides}</p>
        ) : (
          <div className={table.wrap}>
            <table className={[table.table, table.dense].join(" ")} data-testid="overrides">
              <tbody>
                {d.overrides.map((o) => (
                  <tr key={o.id}>
                    <td className={styles.mono}>
                      {o.resource_code ?? o.feature_code} · {o.period}
                    </td>
                    <td className={table.num}>{o.limit_value}</td>
                    <td>
                      <div className={table.primaryCell}>
                        <span>{o.reason}</span>
                        <span>{o.expires_at ? dateTime(o.expires_at) : C.common.none}</span>
                      </div>
                    </td>
                    <td className={table.actions}>
                      {o.active ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          loading={busy === `end-${o.id}`}
                          disabled={busy !== null}
                          onClick={() => run(`end-${o.id}`, () => api.admin.endOverride(m.id, o.id), C.merchants.overrideEnded)}
                        >
                          {C.merchants.endOverride}
                        </Button>
                      ) : (
                        <Badge tone="neutral">ended</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <OverrideForm
          resources={d.usage.map((u) => ({ code: u.resource, kind: u.kind }))}
          busy={busy === "override"}
          onSubmit={(body) => run("override", () => api.admin.createOverride(m.id, body), C.merchants.overrideSaved)}
        />
      </section>

      <section className={styles.section} aria-labelledby="m-credits">
        <h3 id="m-credits">{C.merchants.grant}</h3>
        <CreditsForm
          busy={busy === "credits"}
          onSubmit={(body) =>
            run("credits", async () => fmt(C.merchants.granted, { balance: (await api.admin.grantCredits(m.id, body)).balance }), "")
          }
        />
      </section>

      <section className={styles.section} aria-labelledby="m-status">
        <h3 id="m-status">{m.status === "suspended" ? C.merchants.reactivate : C.merchants.suspend}</h3>
        <p className={styles.muted}>{C.merchants.suspendHelp}</p>
        {m.status === "closed" ? null : (
          <StatusForm
            suspended={m.status === "suspended"}
            busy={busy === "status"}
            onSubmit={(reason) =>
              run(
                "status",
                () => api.admin.setStatus(m.id, m.status === "suspended" ? "active" : "suspended", reason),
                m.status === "suspended" ? C.merchants.reactivated : C.merchants.suspended,
              )
            }
          />
        )}
      </section>
    </div>
  );
}

function ReasonField({ value, onChange, id }: { value: string; onChange: (v: string) => void; id: string }) {
  return (
    <TextField id={id} label={C.common.reason} hint={C.common.reasonHint} value={value} onChange={(e) => onChange(e.target.value)} minLength={5} maxLength={300} required />
  );
}

function OverrideForm({
  resources,
  busy,
  onSubmit,
}: {
  resources: { code: string; kind?: string | null }[];
  busy: boolean;
  onSubmit: (b: { resource_code: string; period: "month" | "lifetime"; limit_value: number; reason: string; expires_at: string | null }) => Promise<boolean>;
}) {
  const [resource, setResource] = useState(resources[0]?.code ?? "");
  const [limit, setLimit] = useState("");
  const [reason, setReason] = useState("");
  const [expires, setExpires] = useState("");
  const kind = resources.find((r) => r.code === resource)?.kind;
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const ok = await onSubmit({
      resource_code: resource,
      period: kind === "gauge" ? "lifetime" : "month",
      limit_value: Number(limit),
      reason: reason.trim(),
      expires_at: expires ? new Date(expires).toISOString() : null,
    });
    if (ok) {
      setLimit("");
      setReason("");
      setExpires("");
    }
  };
  return (
    <form className={styles.form} onSubmit={submit} aria-label={C.merchants.addOverride} style={{ marginTop: "var(--space-3)" }}>
      <div className={styles.formRow}>
        <SelectField label={C.merchants.resource} value={resource} onChange={(e) => setResource(e.target.value)}>
          {resources.map((r) => (
            <option key={r.code} value={r.code}>
              {r.code}
            </option>
          ))}
        </SelectField>
        <TextField label={C.merchants.limit} type="number" inputMode="numeric" min={0} max={10_000_000} value={limit} onChange={(e) => setLimit(e.target.value)} required />
        <TextField label={C.merchants.expires} type="datetime-local" value={expires} onChange={(e) => setExpires(e.target.value)} />
      </div>
      <ReasonField id="override-reason" value={reason} onChange={setReason} />
      <div className={styles.actionsRow}>
        <Button type="submit" variant="primary" size="sm" loading={busy}>
          {C.merchants.addOverride}
        </Button>
      </div>
    </form>
  );
}

function CreditsForm({ busy, onSubmit }: { busy: boolean; onSubmit: (b: { amount: number; reason: string; idempotency_key: string }) => Promise<boolean> }) {
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  // One key per intended grant: a double-click or retry of the same form grants once.
  const [key, setKey] = useState(() => crypto.randomUUID());
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (await onSubmit({ amount: Number(amount), reason: reason.trim(), idempotency_key: key })) {
      setAmount("");
      setReason("");
      setKey(crypto.randomUUID());
    }
  };
  return (
    <form className={styles.form} onSubmit={submit} aria-label={C.merchants.grant}>
      <div className={styles.formRow}>
        <TextField label={C.merchants.amount} type="number" inputMode="numeric" min={1} max={1_000_000} value={amount} onChange={(e) => setAmount(e.target.value)} required />
      </div>
      <ReasonField id="credits-reason" value={reason} onChange={setReason} />
      <div className={styles.actionsRow}>
        <Button type="submit" variant="primary" size="sm" loading={busy}>
          {C.merchants.grant}
        </Button>
      </div>
    </form>
  );
}

function StatusForm({ suspended, busy, onSubmit }: { suspended: boolean; busy: boolean; onSubmit: (reason: string) => Promise<boolean> }) {
  const [reason, setReason] = useState("");
  return (
    <form
      className={styles.form}
      onSubmit={async (e) => {
        e.preventDefault();
        if (await onSubmit(reason.trim())) setReason("");
      }}
      aria-label={suspended ? C.merchants.reactivate : C.merchants.suspend}
    >
      <ReasonField id="status-reason" value={reason} onChange={setReason} />
      <div className={styles.actionsRow}>
        <Button type="submit" variant={suspended ? "primary" : "dangerSolid"} size="sm" loading={busy}>
          {suspended ? C.merchants.reactivate : C.merchants.suspend}
        </Button>
      </div>
    </form>
  );
}
