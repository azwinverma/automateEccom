"use client";

import { isApiError, type AutomationModeChoice, type AutopilotReadiness, type SetupApplyResult, type SetupStep, type SetupStepState } from "@commerce-os/api-client";
import { useEffect, useState } from "react";
import { QueryError } from "@/components/states/States";
import { Button, ButtonLink } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/Drawer";
import { Checkbox } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, InlineAlert, PageHeader, RequestId, SectionHeader, Skeleton, type Tone } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import cx from "../settings/connect.module.css";
import wf from "../shared/workflow.module.css";
import styles from "./setup.module.css";

const STATE_TONE: Record<SetupStepState, Tone> = { done: "success", partial: "info", todo: "warning", blocked: "neutral" };
const MODES: AutomationModeChoice[] = ["assisted", "smart", "autopilot"];
/** The server detail is English; show it only where it names the seller's own things. */
const SHOW_DETAIL: ReadonlySet<SetupStepState> = new Set(["done", "partial"]);

type T = ReturnType<typeof useI18n>["t"];

function stepTitle(t: T, key: string): string {
  return t.dynamic(`autopilotSetup.step.${key}`) ?? key;
}

export function workflowName(t: T, code: string, fallback: string): string {
  return t.dynamic(`autopilotSetup.workflow.${code}`) ?? fallback;
}

/** "Set up autopilot": the end-to-end selling path, then one switch for the recommended automations. */
export function AutopilotSetup() {
  const { t, number } = useI18n();
  const { can } = useAuth();
  const allowed = can("automation.read");
  const q = useApiQuery((a) => (allowed ? a.automation.setup() : Promise.resolve(null)), [allowed]);
  const data = q.state.status === "success" ? q.state.data : null;

  return (
    <>
      <PageHeader
        title={t("autopilotSetup.title")}
        subtitle={t("autopilotSetup.subtitle")}
        actions={data ? <Badge tone={data.done === data.total ? "success" : "info"}>{t("autopilotSetup.progress", { done: number(data.done), total: number(data.total) })}</Badge> : undefined}
      />
      {!allowed ? (
        <InlineAlert tone="info" live={false}>
          {t("autopilotSetup.noAccess")}
        </InlineAlert>
      ) : q.state.status === "loading" ? (
        <Skeleton height={320} />
      ) : q.state.status === "error" ? (
        <QueryError error={q.state.error} onRetry={q.reload} />
      ) : data ? (
        <>
          {data.needs_reconnect.length ? (
            <div style={{ marginBottom: "var(--space-4)" }}>
              <InlineAlert
                tone="warning"
                title={t("autopilotSetup.reconnect", { names: data.needs_reconnect.join(", ") })}
                action={
                  <ButtonLink href="/settings/channels" size="sm" variant="primary">
                    {t("channels.reconnect")}
                  </ButtonLink>
                }
              >
                {t("autopilotSetup.reconnectBody")}
              </InlineAlert>
            </div>
          ) : null}
          <meter className={styles.meter} min={0} max={data.total} value={data.done} aria-label={t("autopilotSetup.progress", { done: number(data.done), total: number(data.total) })} />
          <SectionHeader title={t("autopilotSetup.pathHeading")} id="setup-path" />
          <ol className={styles.path} aria-labelledby="setup-path" data-testid="setup-steps">
            {data.steps.map((s, i) => (
              <StepItem key={s.key} step={s} index={i} />
            ))}
          </ol>
          <ApplyPanel readiness={data} onApplied={(r) => q.setData(() => r)} />
        </>
      ) : null}
    </>
  );
}

function StepItem({ step, index }: { step: SetupStep; index: number }) {
  const { t, number } = useI18n();
  return (
    <li className={styles.step} data-state={step.state} data-key={step.key}>
      <span className={styles.marker} aria-hidden="true">
        {step.state === "done" ? <Icon name="check" /> : number(index + 1)}
      </span>
      <div className={styles.stepBody}>
        <div className={styles.stepHead}>
          <h3>{stepTitle(t, step.key)}</h3>
          <Badge tone={STATE_TONE[step.state]}>{t(`autopilotSetup.state.${step.state}`)}</Badge>
        </div>
        <p className={styles.help}>{t.dynamic(`autopilotSetup.stepHelp.${step.key}`) ?? step.detail}</p>
        {SHOW_DETAIL.has(step.state) && step.key !== "workflows" && step.detail ? <p className={styles.detail}>{step.detail}</p> : null}
        {step.workflows?.length ? (
          <ul className={styles.workflows}>
            {step.workflows.map((w) => (
              <li key={w.code}>
                <span>{workflowName(t, w.code, w.name)}</span>
                <Badge tone={w.status === "active" ? "success" : "neutral"} dot={false}>
                  {t.dynamic(`autopilotSetup.workflowStatus.${w.status ?? "none"}`) ?? w.status}
                </Badge>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
      {step.action ? (
        <ButtonLink href={step.action} size="sm" variant={step.state === "done" ? "ghost" : "secondary"} aria-label={`${t("autopilotSetup.open")}: ${stepTitle(t, step.key)}`}>
          {t("autopilotSetup.open")}
        </ButtonLink>
      ) : (
        <span />
      )}
    </li>
  );
}

function ApplyPanel({ readiness, onApplied }: { readiness: AutopilotReadiness; onApplied: (r: SetupApplyResult) => void }) {
  const { t } = useI18n();
  const { api, can } = useAuth();
  const action = useAction();
  const current = readiness.steps.find((s) => s.key === "sales_agent")?.mode;
  const [mode, setMode] = useState<AutomationModeChoice>(current === "autopilot" || current === "assisted" ? current : "smart");
  const [posting, setPosting] = useState(true);
  const [campaigns, setCampaigns] = useState(true);
  const [confirm, setConfirm] = useState(false);
  const [result, setResult] = useState<SetupApplyResult | null>(null);
  const workflows = readiness.steps.find((s) => s.key === "workflows")?.workflows ?? [];
  const approve = can("automation.approve");

  useEffect(() => {
    if (current === "autopilot" || current === "assisted" || current === "smart") setMode(current);
  }, [current]);

  const apply = async () => {
    const r = await action.run(() => api.automation.applySetup({ mode, posting, campaigns }));
    setConfirm(false);
    if (!r) return;
    setResult(r);
    onApplied(r);
  };

  return (
    <section aria-labelledby="apply-heading" className={styles.apply} data-testid="setup-apply">
      <SectionHeader title={t("autopilotSetup.applyHeading")} id="apply-heading" />
      <p className={wf.hint} style={{ marginTop: 0 }}>
        {t("autopilotSetup.applyBody")}
      </p>
      {!approve ? (
        <InlineAlert tone="info" live={false}>
          {t("autopilotSetup.approveOnly")}
        </InlineAlert>
      ) : (
        <div className={wf.stack} style={{ maxWidth: 640 }}>
          <fieldset className={cx.choice}>
            <legend>{t("autopilotSetup.modeLegend")}</legend>
            {MODES.map((m) => (
              <label key={m} className={cx.choiceOption}>
                <input type="radio" name="setup-mode" value={m} checked={mode === m} onChange={() => setMode(m)} />
                <strong>
                  {t(`autopilotSetup.mode.${m}`)}{" "}
                  {m === "smart" ? (
                    <Badge tone="success" dot={false}>
                      {t("autopilotSetup.recommended")}
                    </Badge>
                  ) : null}
                </strong>
                <span>{t(`autopilotSetup.modeHelp.${m}`)}</span>
              </label>
            ))}
          </fieldset>
          <Checkbox label={t("autopilotSetup.posting")} checked={posting} onChange={(e) => setPosting(e.target.checked)} />
          <Checkbox label={t("autopilotSetup.campaigns")} checked={campaigns} onChange={(e) => setCampaigns(e.target.checked)} />
          <div className={styles.summary} data-testid="setup-summary">
            <p className={cx.howTitle}>{t("autopilotSetup.summary")}</p>
            <ul>
              <li>{t("autopilotSetup.summaryMode", { mode: t(`autopilotSetup.mode.${mode}`) })}</li>
              {workflows.map((w) => (
                <li key={w.code}>{workflowName(t, w.code, w.name)}</li>
              ))}
              {posting ? <li>{t("autopilotSetup.summaryPosting")}</li> : null}
              {campaigns ? <li>{t("autopilotSetup.summaryCampaign")}</li> : null}
            </ul>
          </div>
          {action.error ? (
            <InlineAlert tone="danger">
              {errorMessage(t, action.error)}
              <RequestId id={isApiError(action.error) ? action.error.requestId : null} />
            </InlineAlert>
          ) : null}
          <div>
            <Button variant="primary" onClick={() => setConfirm(true)}>
              {t("autopilotSetup.apply")}
            </Button>
          </div>
          {result ? <ApplyResult result={result} /> : null}
        </div>
      )}
      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title={t("autopilotSetup.confirmTitle")}
        body={t("autopilotSetup.confirmBody")}
        confirmLabel={t("autopilotSetup.apply")}
        pending={action.pending}
        onConfirm={apply}
      />
    </section>
  );
}

export function changedLabel(t: T, item: string, names: Map<string, string>): string {
  const [kind, value = ""] = item.split(":");
  if (kind === "mode") return t("autopilotSetup.changedMode", { mode: t.dynamic(`autopilotSetup.mode.${value}`) ?? value });
  if (kind === "workflow") return workflowName(t, value, names.get(value) ?? value);
  if (kind === "posting") return t("autopilotSetup.changedPosting");
  if (kind === "campaign") return t("autopilotSetup.changedCampaign");
  return item;
}

function ApplyResult({ result }: { result: SetupApplyResult }) {
  const { t } = useI18n();
  const names = new Map((result.steps.find((s) => s.key === "workflows")?.workflows ?? []).map((w) => [w.code, w.name]));
  return (
    <div className={wf.stack} role="status" data-testid="setup-result">
      <InlineAlert tone="success" title={t("autopilotSetup.resultTitle")} live={false}>
        {result.changed.length === 0 ? (
          t("autopilotSetup.nothingChanged")
        ) : (
          <>
            <strong>{t("autopilotSetup.changedHeading")}</strong>
            <ul className={styles.resultList}>
              {result.changed.map((c) => (
                <li key={c}>{changedLabel(t, c, names)}</li>
              ))}
            </ul>
          </>
        )}
      </InlineAlert>
      {result.skipped.length ? (
        <InlineAlert tone="warning" title={t("autopilotSetup.skippedHeading")} live={false}>
          <ul className={styles.resultList}>
            {result.skipped.map((s) => (
              <li key={s.item}>
                {t.dynamic(`autopilotSetup.skipItem.${s.item}`) ?? s.item}: {t.dynamic(`autopilotSetup.skip.${s.reason}`) ?? s.reason}
              </li>
            ))}
          </ul>
        </InlineAlert>
      ) : null}
    </div>
  );
}

/** Home: shown until every step is ready. Never calls the API without automation.read. */
export function AutopilotSetupCard() {
  const { t, number } = useI18n();
  const { can } = useAuth();
  const allowed = can("automation.read");
  const q = useApiQuery((a) => (allowed ? a.automation.setup() : Promise.resolve(null)), [allowed]);
  const data = q.state.status === "success" ? q.state.data : null;
  if (!data || data.done >= data.total) return null;
  return (
    <section className={styles.card} aria-labelledby="setup-card-title" data-testid="setup-card">
      <div>
        <h2 id="setup-card-title">{t("autopilotSetup.homeTitle")}</h2>
        <p>{t("autopilotSetup.homeBody", { done: number(data.done), total: number(data.total) })}</p>
        {data.needs_reconnect.length ? <p className={styles.warn}>{t("autopilotSetup.reconnect", { names: data.needs_reconnect.join(", ") })}</p> : null}
      </div>
      <meter className={styles.meter} min={0} max={data.total} value={data.done} aria-hidden="true" />
      <ButtonLink href="/automation/setup" variant="primary">
        {t("autopilotSetup.cta")}
      </ButtonLink>
    </section>
  );
}
