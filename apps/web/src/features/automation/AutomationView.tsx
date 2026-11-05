"use client";

import type { AutomationPolicy, Workflow } from "@commerce-os/api-client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { Checkbox, TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, PageHeader, SectionHeader, type Tone, useToast } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import products from "../products/products.module.css";
import { Approvals } from "./ControlCenter";
import { useActionLabel, useExplain } from "./shared";
import styles from "./automation.module.css";

type Tab = "workflows" | "rules" | "activity";
const TABS: Tab[] = ["workflows", "rules", "activity"];
const STATUS_TONE: Record<Workflow["status"], Tone> = { draft: "neutral", active: "success", paused: "warning" };

export function AutomationView() {
  const { t } = useI18n();
  const params = useSearchParams();
  const initial = (params.get("tab") as Tab | null) ?? "workflows";
  const [tab, setTab] = useState<Tab>(TABS.includes(initial) ? initial : "workflows");
  return (
    <>
      <PageHeader title={t("automation.title")} subtitle={t("automation.subtitle")} />
      <div role="tablist" aria-label={t("automation.tabsLabel")} className={products.tabs} style={{ marginBottom: "var(--space-4)", borderBottom: "1px solid var(--color-border-default)" }}>
        {TABS.map((k) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k} className={products.tab} onClick={() => setTab(k)} data-tab={k}>
            {t(`automation.tabs.${k}`)}
          </button>
        ))}
      </div>
      {tab === "workflows" ? <Workflows /> : tab === "rules" ? <Rules /> : <Activity />}
    </>
  );
}

function Workflows() {
  const { t } = useI18n();
  const { api, can } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const action = useAction();
  const list = useApiQuery((a) => a.automation.workflows());
  const catalog = useApiQuery((a) => a.automation.catalog());
  const write = can("automation.write");

  const create = async (template_code: string | null) => {
    const w = await action.run(() =>
      template_code
        ? api.automation.create({ name: t.dynamic(`automation.template.${template_code}`) ?? template_code, template_code })
        : api.automation.create({
            name: t("automation.newBlank"),
            definition: { trigger: { event: "order.created" }, steps: [{ id: "s1", type: "action", action: "notify_seller", params: { message: "" } }] },
          }),
    );
    if (w) {
      toast(t("automation.builder.created"));
      router.push(`/automation/${w.id}`);
    }
  };

  return (
    <>
      <Approvals onChanged={list.reload} />
      <SectionHeader title={t("automation.yours")} id="wf-heading" />
      <ErrorAlert error={action.error} />
      {list.state.status === "loading" ? (
        <TableSkeleton columns="2fr 1fr 1fr" label={t("common.loading")} />
      ) : list.state.status === "error" ? (
        <QueryError error={list.state.error} onRetry={list.reload} />
      ) : list.state.data.items.length === 0 ? (
        <EmptyState title={t("automation.empty")} body={t("automation.emptyBody")} />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-labelledby="wf-heading" data-testid="workflows">
            <tbody>
              {list.state.data.items.map((w) => (
                <tr key={w.id} data-status={w.status}>
                  <td>
                    <div className={table.primaryCell}>
                      <strong>
                        <Link href={`/automation/${w.id}`} className={products.titleLink}>
                          {w.name}
                        </Link>
                      </strong>
                      <span>{t.dynamic(`automation.trigger.${w.trigger_event.replace(".", "_")}`) ?? w.trigger_event}</span>
                    </div>
                  </td>
                  <td>
                    <Badge tone={STATUS_TONE[w.status]}>{t(`automation.status.${w.status}`)}</Badge>
                    {w.paused_reason?.startsWith("circuit_breaker:") ? (
                      <div className={styles.muted}>{t("automation.pausedBreaker", { action: t.dynamic(`automation.action.${w.paused_reason.split(":")[1]}`) ?? "" })}</div>
                    ) : null}
                  </td>
                  <td className={[table.hideSm, table.muted].join(" ")}>
                    {t("automation.runsSummary", {
                      done: w.runs.completed ?? 0,
                      waiting: (w.runs.waiting ?? 0) + (w.runs.awaiting_approval ?? 0),
                      failed: w.runs.failed ?? 0,
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {write && catalog.state.status === "success" ? (
        <>
          <SectionHeader title={t("automation.templates")} id="tpl-heading" />
          <ul className={styles.list} aria-labelledby="tpl-heading" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))" }} data-testid="templates">
            {catalog.state.data.templates.map((tpl) => (
              <li key={tpl.code} className={styles.card}>
                <strong>{t.dynamic(`automation.template.${tpl.code}`) ?? tpl.code}</strong>
                <span className={styles.muted}>{t.dynamic(`automation.templateHint.${tpl.code}`) ?? ""}</span>
                <div>
                  <Button size="sm" loading={action.pending} onClick={() => void create(tpl.code)} aria-label={`${t("automation.useTemplate")}: ${t.dynamic(`automation.template.${tpl.code}`) ?? tpl.code}`}>
                    {t("automation.useTemplate")}
                  </Button>
                </div>
              </li>
            ))}
            <li className={styles.card}>
              <strong>{t("automation.newBlank")}</strong>
              <div>
                <Button size="sm" variant="ghost" loading={action.pending} onClick={() => void create(null)}>
                  <Icon name="plus" />
                  {t("automation.newBlank")}
                </Button>
              </div>
            </li>
          </ul>
        </>
      ) : null}
    </>
  );
}

const MATRIX: Record<string, Record<string, "auto" | "approval" | "ifSure" | "ifOn">> = {
  assisted: { R0: "auto", R1: "approval", R2: "approval", R3: "approval" },
  smart: { R0: "auto", R1: "ifSure", R2: "ifOn", R3: "approval" },
  autopilot: { R0: "auto", R1: "auto", R2: "ifOn", R3: "approval" },
};

function Rules() {
  const { t } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const pol = useApiQuery((a) => a.automation.policy());
  const cc = useApiQuery((a) => a.controlCenter(1));
  const [form, setForm] = useState<AutomationPolicy | null>(null);
  const [limits, setLimits] = useState<Record<string, string>>({});
  useEffect(() => {
    if (pol.state.status !== "success") return;
    const p = pol.state.data;
    setForm(p);
    setLimits(Object.fromEntries(Object.entries(p.thresholds).map(([k, v]) => [k, k.endsWith("_minor") ? String(v / 100) : String(v)])));
  }, [pol.state]);
  if (pol.state.status === "error") return <QueryError error={pol.state.error} onRetry={pol.reload} />;
  if (!form) return <TableSkeleton columns="1fr" rows={5} label={t("common.loading")} />;
  const mode = cc.state.status === "success" ? cc.state.data.mode : null;
  const write = can("automation.write");
  return (
    <form
      data-testid="automation-rules"
      style={{ display: "grid", gap: "var(--space-4)", maxWidth: 760 }}
      onSubmit={async (e) => {
        e.preventDefault();
        const thresholds = Object.fromEntries(
          Object.entries(limits).map(([k, v]) => [k, Math.max(0, Math.round((Number(v.replace(/,/g, "")) || 0) * (k.endsWith("_minor") ? 100 : 1)))]),
        );
        const next = await action.run(() => api.automation.updatePolicy({ thresholds, enabled_r2: form.enabled_r2, confidence_threshold: form.confidence_threshold }));
        if (next) {
          setForm(next);
          toast(t("automation.policy.saved"));
        }
      }}
    >
      <p className={styles.muted} style={{ margin: 0 }}>
        {t("automation.policy.subtitle")}
      </p>
      <ErrorAlert error={action.error} />
      <section aria-labelledby="matrix-h">
        <SectionHeader title={t("automation.policy.matrix")} id="matrix-h" meta={mode ? `${t("automation.policy.mode")}: ${t(`autopilot.${mode}`)}` : undefined} />
        <div className={table.wrap}>
          <table className={styles.matrix}>
            <thead>
              <tr>
                <th scope="col" />
                {(["assisted", "smart", "autopilot"] as const).map((m) => (
                  <th key={m} scope="col" aria-current={m === mode ? "true" : undefined}>
                    {t(`autopilot.${m}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(["R0", "R1", "R2", "R3"] as const).map((r) => (
                <tr key={r}>
                  <th scope="row">{t(`automation.policy.row.${r}`)}</th>
                  {(["assisted", "smart", "autopilot"] as const).map((m) => (
                    <td key={m} data-cell={MATRIX[m]![r]}>
                      {t(`automation.policy.cell.${MATRIX[m]![r]!}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className={styles.muted}>{t("automation.policy.modeHint")}</p>
      </section>
      <TextField
        label={t("automation.policy.confidence")}
        type="number"
        min={50}
        max={100}
        value={Math.round(form.confidence_threshold * 100)}
        disabled={!write}
        onChange={(e) => setForm({ ...form, confidence_threshold: Math.max(0.5, Math.min(1, (Number(e.target.value) || 50) / 100)) })}
      />
      <fieldset style={{ border: 0, margin: 0, padding: 0, display: "grid", gap: "var(--space-2)" }}>
        <legend style={{ fontWeight: "var(--font-weight-medium)", marginBottom: "var(--space-2)" }}>{t("automation.policy.r2")}</legend>
        {form.r2_actions.map((a) => (
          <Checkbox
            key={a}
            label={t.dynamic(`automation.action.${a}`) ?? a}
            checked={form.enabled_r2.includes(a)}
            disabled={!write}
            onChange={(e) => setForm({ ...form, enabled_r2: e.target.checked ? [...form.enabled_r2, a] : form.enabled_r2.filter((x) => x !== a) })}
          />
        ))}
      </fieldset>
      <fieldset style={{ border: 0, margin: 0, padding: 0, display: "grid", gap: "var(--space-2)" }}>
        <legend style={{ fontWeight: "var(--font-weight-medium)", marginBottom: "var(--space-2)" }}>{t("automation.policy.limits")}</legend>
        <div className={styles.grid}>
          {Object.keys(limits).map((k) => (
            <TextField
              key={k}
              label={t.dynamic(`automation.policy.limit.${k}`) ?? k}
              inputMode="decimal"
              value={limits[k]}
              disabled={!write}
              onChange={(e) => setLimits((l) => ({ ...l, [k]: e.target.value }))}
            />
          ))}
        </div>
      </fieldset>
      {write ? (
        <div>
          <Button type="submit" variant="primary" loading={action.pending}>
            {t("couriers.save")}
          </Button>
        </div>
      ) : null}
    </form>
  );
}

function Activity() {
  const { t, relative, dateTime, money } = useI18n();
  const decisions = useApiQuery((a) => a.automation.decisions());
  const label = useActionLabel();
  const explain = useExplain();
  if (decisions.state.status === "loading") return <TableSkeleton columns="2fr 1fr 1fr" label={t("common.loading")} />;
  if (decisions.state.status === "error") return <QueryError error={decisions.state.error} onRetry={decisions.reload} />;
  const items = decisions.state.data.items;
  if (!items.length) return <EmptyState title={t("automation.activity.empty")} />;
  return (
    <div className={table.wrap}>
      <table className={table.table} aria-label={t("automation.activity.title")} data-testid="decisions">
        <tbody>
          {items.map((d) => (
            <tr key={d.id} data-decision={d.decision}>
              <td>
                <div className={table.primaryCell}>
                  <strong>{label(d.action)}</strong>
                  <span>
                    {t.dynamic(`automation.activity.source.${d.source}`) ?? d.source} · {explain(d)}
                    {d.impact?.amount_minor != null && d.impact.currency ? ` · ${money(d.impact.amount_minor, d.impact.currency)}` : ""}
                  </span>
                </div>
              </td>
              <td>
                <Badge tone={d.decision === "AUTO_EXECUTE" ? "automated" : d.decision === "BLOCK" ? "danger" : "warning"} dot={false}>
                  {t(`automation.activity.decision.${d.decision}`)}
                </Badge>
              </td>
              <td className={[table.hideSm, table.muted].join(" ")}>
                <time dateTime={d.created_at} title={dateTime(d.created_at)}>
                  {relative(d.created_at)}
                </time>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
