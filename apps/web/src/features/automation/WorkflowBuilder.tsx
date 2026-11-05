"use client";

import type { AutomationCatalog, Condition, ConditionOp, DryRunResult, WorkflowDefinition, WorkflowStep } from "@commerce-os/api-client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { Checkbox, SelectField, TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, type Tone, useToast } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import orderStyles from "../orders/orders.module.css";
import { ErrorAlert } from "../orders/shared";
import products from "../products/products.module.css";
import { useActionLabel, useExplain } from "./shared";
import styles from "./automation.module.css";

type Row = { field: string; op: ConditionOp; value: string };
const RISK_TONE: Record<string, Tone> = { R0: "neutral", R1: "info", R2: "warning", R3: "danger" };
const BOOL_OPS: ConditionOp[] = ["is_true", "is_false"];

function toRows(when: Condition | undefined): { mode: "all" | "any"; rows: Row[] } {
  if (!when) return { mode: "all", rows: [] };
  const group = "all" in when ? { mode: "all" as const, items: when.all } : "any" in when ? { mode: "any" as const, items: when.any } : { mode: "all" as const, items: [when] };
  return {
    mode: group.mode,
    rows: group.items
      .filter((c): c is Extract<Condition, { field: string }> => "field" in c)
      .map((c) => ({ field: c.field, op: c.op, value: Array.isArray(c.value) ? c.value.join(", ") : c.value === undefined ? "" : String(c.value) })),
  };
}

function fromRows(mode: "all" | "any", rows: Row[], fields: Record<string, string>): Condition {
  const items: Condition[] = rows.map((r) => {
    const kind = fields[r.field];
    if (BOOL_OPS.includes(r.op)) return { field: r.field, op: r.op };
    if (r.op === "in" || r.op === "not_in") {
      const parts = r.value.split(",").map((x) => x.trim()).filter(Boolean);
      return { field: r.field, op: r.op, value: kind === "int" ? parts.map(Number) : parts };
    }
    return { field: r.field, op: r.op, value: kind === "int" ? Number(r.value) : r.value };
  });
  return mode === "all" ? { all: items } : { any: items };
}

export function WorkflowBuilder({ id }: { id: string }) {
  const { t } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const wf = useApiQuery((a) => a.automation.workflow(id), [id]);
  const catalog = useApiQuery((a) => a.automation.catalog());
  const runs = useApiQuery((a) => a.automation.runs(id), [id]);
  const [name, setName] = useState("");
  const [def, setDef] = useState<WorkflowDefinition | null>(null);

  useEffect(() => {
    if (wf.state.status === "success" && wf.state.data.definition) {
      setName(wf.state.data.name);
      setDef(wf.state.data.definition);
    }
  }, [wf.state]);

  if (wf.state.status === "error") return <QueryError error={wf.state.error} onRetry={wf.reload} />;
  if (wf.state.status !== "success" || catalog.state.status !== "success" || !def) return <TableSkeleton columns="2fr 1fr" rows={6} label={t("common.loading")} />;
  const w = wf.state.data;
  const cat = catalog.state.data;
  const write = can("automation.write");
  const trig = cat.triggers.find((x) => x.code === def.trigger.event) ?? cat.triggers[0]!;

  const save = async () => {
    const next = await action.run(() => api.automation.update(id, { name: name.trim(), definition: def }));
    if (next) {
      wf.setData(() => next);
      toast(t("automation.builder.saved"));
    }
  };
  const toggle = async () => {
    const next = await action.run(() => api.automation.setStatus(id, w.status === "active" ? "paused" : "active"));
    if (next) wf.setData(() => next);
  };

  return (
    <div data-testid="workflow-builder">
      <div className={products.editorHeader}>
        <div className={products.editorTitle}>
          <Link href="/automation" className={products.backLink}>
            ← {t("automation.builder.back")}
          </Link>
          <h1>
            {w.name} <Badge tone={w.status === "active" ? "success" : w.status === "paused" ? "warning" : "neutral"}>{t(`automation.status.${w.status}`)}</Badge>
          </h1>
          <p className={styles.muted}>{t("automation.version", { n: w.version ?? 1 })}</p>
        </div>
        <div className={styles.row}>
          {write ? (
            <Button variant="secondary" loading={action.pending} onClick={() => void save()}>
              {t("automation.builder.save")}
            </Button>
          ) : null}
          {can("automation.approve") ? (
            <Button variant={w.status === "active" ? "ghost" : "primary"} loading={action.pending} onClick={() => void toggle()} data-testid="toggle-workflow">
              {w.status === "active" ? t("automation.turnOff") : t("automation.turnOn")}
            </Button>
          ) : null}
        </div>
      </div>
      <ErrorAlert error={action.error} />
      <div className={styles.layout}>
        <div style={{ display: "grid", gap: "var(--space-4)" }}>
          <section className={orderStyles.panel} aria-labelledby="b-trigger">
            <h2 id="b-trigger">{t("automation.builder.trigger")}</h2>
            <div style={{ display: "grid", gap: "var(--space-3)" }}>
              <TextField label={t("automation.builder.name")} value={name} onChange={(e) => setName(e.target.value)} maxLength={120} disabled={!write} />
              <SelectField
                label={t("automation.builder.trigger")}
                value={def.trigger.event}
                disabled={!write}
                onChange={(e) => setDef({ trigger: { event: e.target.value as WorkflowDefinition["trigger"]["event"], filter: [] }, steps: def.steps })}
              >
                {cat.triggers.map((x) => (
                  <option key={x.code} value={x.code}>
                    {t.dynamic(`automation.trigger.${x.code.replace(".", "_")}`) ?? x.code}
                  </option>
                ))}
              </SelectField>
              {trig.filter_values.length ? (
                <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
                  <legend className={styles.muted} style={{ marginBottom: "var(--space-2)" }}>
                    {t("automation.builder.filter")}
                  </legend>
                  <div className={styles.row}>
                    {trig.filter_values.map((v) => (
                      <Checkbox
                        key={v}
                        label={statusLabel(t, trig.subject, v)}
                        checked={(def.trigger.filter ?? []).includes(v)}
                        disabled={!write}
                        onChange={(e) =>
                          setDef({ ...def, trigger: { ...def.trigger, filter: e.target.checked ? [...(def.trigger.filter ?? []), v] : (def.trigger.filter ?? []).filter((x) => x !== v) } })
                        }
                      />
                    ))}
                  </div>
                </fieldset>
              ) : null}
            </div>
          </section>
          <StepsEditor def={def} setDef={setDef} cat={cat} subject={trig.subject} fields={trig.fields} disabled={!write} />
        </div>
        <aside style={{ display: "grid", gap: "var(--space-4)" }}>
          <DryRun def={def} subject={trig.subject} />
          <Runs runs={runs.state.status === "success" ? runs.state.data.items : []} />
        </aside>
      </div>
    </div>
  );
}

function statusLabel(t: ReturnType<typeof useI18n>["t"], subject: string, v: string): string {
  const key = subject === "order" ? `orders.status.${v}` : subject === "shipment" ? `fulfillment.status.${v}` : `returns.status.${v}`;
  return t.dynamic(key) ?? v;
}

function StepsEditor({
  def,
  setDef,
  cat,
  subject,
  fields,
  disabled,
}: {
  def: WorkflowDefinition;
  setDef: (d: WorkflowDefinition) => void;
  cat: AutomationCatalog;
  subject: string;
  fields: Record<string, string>;
  disabled: boolean;
}) {
  const { t } = useI18n();
  const [newType, setNewType] = useState<WorkflowStep["type"]>("action");
  const steps = def.steps;
  const actions = cat.actions.filter((a) => a.subjects.includes(subject));
  const set = (i: number, s: WorkflowStep) => setDef({ ...def, steps: steps.map((x, j) => (j === i ? s : x)) });
  const freshId = () => {
    let n = steps.length + 1;
    while (steps.some((s) => s.id === `s${n}`)) n += 1;
    return `s${n}`;
  };
  const add = () => {
    const id = freshId();
    const firstField = Object.keys(fields)[0] ?? "";
    const step: WorkflowStep =
      newType === "condition"
        ? { id, type: "condition", when: { all: [{ field: firstField, op: "eq", value: "" }] }, else: "stop" }
        : newType === "branch"
          ? { id, type: "branch", when: { all: [{ field: firstField, op: "eq", value: "" }] }, then: "stop", else: "stop" }
          : newType === "wait"
            ? { id, type: "wait", hours: 24 }
            : newType === "approval"
              ? { id, type: "approval", note: "" }
              : { id, type: "action", action: actions[0]!.code, params: {} };
    setDef({ ...def, steps: [...steps, step] });
  };
  const move = (i: number, d: -1 | 1) => {
    const next = [...steps];
    [next[i], next[i + d]] = [next[i + d]!, next[i]!];
    setDef({ ...def, steps: next });
  };
  const forward = (i: number) => steps.slice(i + 1).map((s, k) => ({ id: s.id, label: t("automation.builder.stepN", { n: i + k + 2 }) }));

  return (
    <section className={orderStyles.panel} aria-labelledby="b-steps">
      <h2 id="b-steps">{t("automation.builder.steps")}</h2>
      <ol className={styles.steps} data-testid="steps">
        {steps.map((s, i) => (
          <li key={s.id} className={styles.step} data-type={s.type}>
            <div className={styles.stepHead}>
              <strong>{t(`automation.stepType.${s.type}`)}</strong>
              {!disabled ? (
                <span className={styles.row}>
                  <Button size="sm" variant="ghost" iconOnly disabled={i === 0} aria-label={t("automation.builder.moveUp", { n: i + 1 })} onClick={() => move(i, -1)}>
                    <Icon name="chevronDown" style={{ transform: "rotate(180deg)" }} />
                  </Button>
                  <Button size="sm" variant="ghost" iconOnly disabled={i === steps.length - 1} aria-label={t("automation.builder.moveDown", { n: i + 1 })} onClick={() => move(i, 1)}>
                    <Icon name="chevronDown" />
                  </Button>
                  <Button size="sm" variant="ghost" iconOnly disabled={steps.length === 1} aria-label={t("automation.builder.remove", { n: i + 1 })} onClick={() => setDef({ ...def, steps: steps.filter((_, j) => j !== i) })}>
                    <Icon name="close" />
                  </Button>
                </span>
              ) : null}
            </div>
            {s.type === "condition" || s.type === "branch" ? (
              <ConditionEditor step={s} n={i + 1} fields={fields} disabled={disabled} onChange={(when) => set(i, { ...s, when } as WorkflowStep)} />
            ) : null}
            {s.type === "branch" ? (
              <div className={styles.grid}>
                <SelectField label={t("automation.builder.then")} value={s.then} disabled={disabled} onChange={(e) => set(i, { ...s, then: e.target.value })}>
                  {forward(i).map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.label}
                    </option>
                  ))}
                  <option value="stop">{t("automation.builder.stop")}</option>
                </SelectField>
                <SelectField label={t("automation.builder.otherwise")} value={s.else ?? "stop"} disabled={disabled} onChange={(e) => set(i, { ...s, else: e.target.value })}>
                  {forward(i).map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.label}
                    </option>
                  ))}
                  <option value="stop">{t("automation.builder.stop")}</option>
                </SelectField>
              </div>
            ) : null}
            {s.type === "condition" ? (
              <SelectField label={t("automation.builder.otherwise")} value={s.else ?? "stop"} disabled={disabled} onChange={(e) => set(i, { ...s, else: e.target.value })}>
                <option value="stop">{t("automation.builder.stop")}</option>
                {forward(i).map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.label}
                  </option>
                ))}
              </SelectField>
            ) : null}
            {s.type === "wait" ? (
              <TextField label={t("automation.builder.hours")} type="number" min={1} max={720} value={s.hours} disabled={disabled} onChange={(e) => set(i, { ...s, hours: Math.max(1, Math.min(720, Number(e.target.value) || 1)) })} />
            ) : null}
            {s.type === "approval" ? (
              <TextField label={t("automation.builder.approvalNote")} value={s.note ?? ""} disabled={disabled} onChange={(e) => set(i, { ...s, note: e.target.value })} maxLength={200} />
            ) : null}
            {s.type === "action" ? <ActionEditor step={s} cat={cat} actions={actions} disabled={disabled} onChange={(next) => set(i, next)} /> : null}
            {s.type === "action" || s.type === "wait" ? (
              <SelectField
                label={t("automation.builder.nextStep")}
                value={s.next ?? ""}
                disabled={disabled}
                onChange={(e) => set(i, { ...s, next: e.target.value || undefined } as WorkflowStep)}
              >
                <option value="">{forward(i)[0]?.label ?? t("automation.builder.stop")}</option>
                {forward(i)
                  .slice(1)
                  .map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.label}
                    </option>
                  ))}
                {forward(i).length ? <option value="stop">{t("automation.builder.stop")}</option> : null}
              </SelectField>
            ) : null}
          </li>
        ))}
      </ol>
      {!disabled && steps.length < 20 ? (
        <div className={styles.row} style={{ marginTop: "var(--space-3)", alignItems: "flex-end" }}>
          <SelectField label={t("automation.builder.addStep")} value={newType} onChange={(e) => setNewType(e.target.value as WorkflowStep["type"])}>
            {(["action", "condition", "branch", "wait", "approval"] as const).map((k) => (
              <option key={k} value={k}>
                {t(`automation.stepType.${k}`)}
              </option>
            ))}
          </SelectField>
          <Button size="sm" onClick={add}>
            <Icon name="plus" />
            {t("automation.builder.addStep")}
          </Button>
        </div>
      ) : null}
    </section>
  );
}

function ConditionEditor({
  step,
  n,
  fields,
  disabled,
  onChange,
}: {
  step: Extract<WorkflowStep, { type: "condition" | "branch" }>;
  n: number;
  fields: Record<string, string>;
  disabled: boolean;
  onChange: (c: Condition) => void;
}) {
  const { t } = useI18n();
  const initial = useMemo(() => toRows(step.when), [step.when]);
  const { mode, rows } = initial;
  const emit = (m: "all" | "any", r: Row[]) => onChange(fromRows(m, r, fields));
  const opsFor = (field: string): ConditionOp[] =>
    fields[field] === "bool" ? BOOL_OPS : fields[field] === "int" ? ["eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in"] : ["eq", "ne", "in", "not_in"];
  return (
    <div style={{ display: "grid", gap: "var(--space-2)" }}>
      <SelectField label={`${t("automation.builder.match")} (${t("automation.builder.stepN", { n })})`} value={mode} disabled={disabled} onChange={(e) => emit(e.target.value as "all" | "any", rows)}>
        <option value="all">{t("automation.builder.matchAll")}</option>
        <option value="any">{t("automation.builder.matchAny")}</option>
      </SelectField>
      {rows.map((r, k) => {
        const label = (key: "conditionField" | "conditionOp" | "conditionValue") => `${t(`automation.builder.${key}`, { n: k + 1 })} (${t("automation.builder.stepN", { n })})`;
        const update = (patch: Partial<Row>) => emit(mode, rows.map((x, j) => (j === k ? { ...x, ...patch } : x)));
        return (
          <div key={k} className={styles.grid}>
            <SelectField label={label("conditionField")} value={r.field} disabled={disabled} onChange={(e) => update({ field: e.target.value, op: opsFor(e.target.value)[0]!, value: "" })}>
              {Object.keys(fields).map((f) => (
                <option key={f} value={f}>
                  {t.dynamic(`automation.field.${f.replace(".", "_")}`) ?? f}
                </option>
              ))}
            </SelectField>
            <SelectField label={label("conditionOp")} value={r.op} disabled={disabled} onChange={(e) => update({ op: e.target.value as ConditionOp })}>
              {opsFor(r.field).map((o) => (
                <option key={o} value={o}>
                  {t(`automation.op.${o}`)}
                </option>
              ))}
            </SelectField>
            {!BOOL_OPS.includes(r.op) ? (
              <TextField
                label={label("conditionValue")}
                hint={r.op === "in" || r.op === "not_in" ? t("automation.builder.listHint") : undefined}
                inputMode={fields[r.field] === "int" ? "numeric" : undefined}
                value={r.value}
                disabled={disabled}
                onChange={(e) => update({ value: e.target.value })}
              />
            ) : (
              <span />
            )}
            {!disabled && rows.length > 1 ? (
              <Button size="sm" variant="ghost" iconOnly aria-label={t("automation.builder.removeCondition", { n: k + 1 })} onClick={() => emit(mode, rows.filter((_, j) => j !== k))}>
                <Icon name="close" />
              </Button>
            ) : null}
          </div>
        );
      })}
      {!disabled && rows.length < 10 ? (
        <div>
          <Button size="sm" variant="ghost" onClick={() => emit(mode, [...rows, { field: Object.keys(fields)[0] ?? "", op: opsFor(Object.keys(fields)[0] ?? "")[0]!, value: "" }])}>
            <Icon name="plus" />
            {t("automation.builder.addCondition")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function ActionEditor({
  step,
  cat,
  actions,
  disabled,
  onChange,
}: {
  step: Extract<WorkflowStep, { type: "action" }>;
  cat: AutomationCatalog;
  actions: AutomationCatalog["actions"];
  disabled: boolean;
  onChange: (s: WorkflowStep) => void;
}) {
  const { t } = useI18n();
  const def = cat.actions.find((a) => a.code === step.action);
  return (
    <div style={{ display: "grid", gap: "var(--space-2)" }}>
      <div className={styles.grid}>
        <SelectField label={t("automation.builder.action")} value={step.action} disabled={disabled} onChange={(e) => onChange({ ...step, action: e.target.value as typeof step.action, params: {} })}>
          {actions.map((a) => (
            <option key={a.code} value={a.code}>
              {t(`automation.action.${a.code}`)}
            </option>
          ))}
        </SelectField>
        {def ? (
          <span>
            <Badge tone={RISK_TONE[def.risk_class] ?? "neutral"} dot={false}>
              {t.dynamic(`automation.builder.risk.${def.risk_class}`) ?? def.risk_class}
            </Badge>
          </span>
        ) : null}
      </div>
      {def?.params.map((p) => (
        <TextField
          key={p}
          label={t.dynamic(`automation.builder.param.${p}`) ?? p}
          value={step.params?.[p] ?? ""}
          required={def.required_params.includes(p)}
          disabled={disabled}
          maxLength={1000}
          onChange={(e) => onChange({ ...step, params: { ...(step.params ?? {}), [p]: e.target.value } })}
        />
      ))}
      {def?.params.some((p) => p.startsWith("text_") || p === "message" || p === "note") ? <span className={styles.muted}>{t("automation.builder.placeholders")}</span> : null}
    </div>
  );
}

function DryRun({ def, subject }: { def: WorkflowDefinition; subject: string }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const action = useAction();
  const orders = useApiQuery((a) => (subject === "order" ? a.orders.list({ limit: 20 }) : Promise.resolve({ items: [], next_cursor: null })), [subject]);
  const [subjectId, setSubjectId] = useState("");
  const [result, setResult] = useState<DryRunResult | null>(null);
  const label = useActionLabel();
  const explain = useExplain();
  const opts = orders.state.status === "success" ? orders.state.data.items : [];
  return (
    <section className={orderStyles.panel} aria-labelledby="b-dry" data-testid="dry-run">
      <h2 id="b-dry">{t("automation.builder.dryRun")}</h2>
      <p className={styles.muted} style={{ marginTop: 0 }}>
        {t("automation.builder.dryRunHint")}
      </p>
      <ErrorAlert error={action.error} />
      <div style={{ display: "grid", gap: "var(--space-2)" }}>
        {subject === "order" ? (
          <SelectField label={t("automation.builder.dryRunOrder")} value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
            <option value="">–</option>
            {opts.map((o) => (
              <option key={o.id} value={o.id}>
                #{o.number} · {o.customer?.display_name ?? ""} · {t(`orders.status.${o.status}`)}
              </option>
            ))}
          </SelectField>
        ) : (
          <TextField label={t("automation.builder.dryRunSubject")} value={subjectId} onChange={(e) => setSubjectId(e.target.value.trim())} />
        )}
        <div>
          <Button size="sm" disabled={!subjectId} loading={action.pending} onClick={async () => setResult((await action.run(() => api.automation.dryRun(def, subjectId))) ?? null)}>
            {t("automation.builder.dryRunGo")}
          </Button>
        </div>
      </div>
      {result ? (
        <ol className={styles.trace} style={{ marginTop: "var(--space-3)" }} data-testid="dry-run-trace">
          {result.trace.map((x, i) => (
            <li key={`${x.step}-${i}`} data-step={x.step}>
              <strong>{x.step === "trigger" ? t("automation.builder.trigger") : x.type ? t.dynamic(`automation.stepType.${x.type}`) : x.step}</strong>
              <span>
                {x.note === "trigger_filter_not_met"
                  ? t("automation.builder.trace.trigger_filter_not_met")
                  : x.result !== undefined
                    ? t(x.result ? "automation.builder.trace.true" : "automation.builder.trace.false")
                    : x.action
                      ? `${label(x.action)}: ${x.decision ? t(`automation.activity.decision.${x.decision}`) : ""} (${explain({ rule: x.rule ?? "" })})`
                      : (x.note ?? (x.decision ? t(`automation.activity.decision.${x.decision}`) : ""))}
              </span>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}

function Runs({ runs }: { runs: import("@commerce-os/api-client").WorkflowRunView[] }) {
  const { t, relative } = useI18n();
  const label = useActionLabel();
  const explain = useExplain();
  return (
    <section className={orderStyles.panel} aria-labelledby="b-runs" data-testid="runs">
      <h2 id="b-runs">{t("automation.builder.runs")}</h2>
      {runs.length === 0 ? <p className={styles.muted}>{t("automation.builder.noRuns")}</p> : null}
      <ul className={styles.list}>
        {runs.slice(0, 10).map((r) => (
          <li key={r.id} className={styles.card} data-status={r.status}>
            <div className={styles.cardHead}>
              <Badge tone={r.status === "completed" ? "success" : r.status === "failed" ? "danger" : r.status === "awaiting_approval" ? "warning" : "neutral"} dot={false}>
                {t(`automation.builder.runStatus.${r.status}`)}
              </Badge>
              <span className={styles.muted}>{relative(r.created_at)}</span>
            </div>
            <ol className={styles.trace}>
              {(r.steps ?? []).map((s) => (
                <li key={s.id}>
                  <span>{s.action ? label(s.action) : t(`automation.stepType.${s.kind}`)}</span>
                  <span className={styles.muted}>
                    {t(`automation.builder.stepStatus.${s.status}`)}
                    {s.decision ? ` · ${explain(s.decision)}` : ""}
                    {s.error ? ` · ${t.dynamic(`errors.${s.error}`) ?? s.error}` : ""}
                  </span>
                </li>
              ))}
            </ol>
          </li>
        ))}
      </ul>
    </section>
  );
}
