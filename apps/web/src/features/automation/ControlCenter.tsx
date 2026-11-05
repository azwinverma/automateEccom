"use client";

import type { AutomationApproval } from "@commerce-os/api-client";
import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/Drawer";
import { TextField } from "@/components/ui/Field";
import { Badge, SectionHeader, useToast } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import { useActionLabel, useExplain } from "./shared";
import styles from "./automation.module.css";

/** UX-016: "Your store is running." Real numbers from the last 7 days, and what needs the seller. */
export function ControlCenter({ onChanged }: { onChanged?: () => void }) {
  const { t, money, number, relative, dateTime } = useI18n();
  const cc = useApiQuery((a) => a.controlCenter(7));
  const label = useActionLabel();
  const explain = useExplain();
  if (cc.state.status !== "success") return null;
  const c = cc.state.data;
  const total = c.automation.done_automatically + c.automation.done_by_team;
  return (
    <section className={styles.board} aria-labelledby="cc-title" data-testid="control-center" data-state={c.state}>
      <div className={styles.headline}>
        <span className={styles.pulse} data-state={c.state} aria-hidden />
        <h2 id="cc-title">{t(`control.state.${c.state}`)}</h2>
        <Badge tone="automated" dot={false}>
          {t(`autopilot.${c.mode}`)}
        </Badge>
        <span className={styles.muted}>{t("control.period")}</span>
      </div>
      <dl className={styles.tiles}>
        <div>
          <dt>{t("control.orders")}</dt>
          <dd>{number(c.metrics.orders)}</dd>
        </div>
        {c.metrics.revenue_minor !== null ? (
          <div>
            <dt>{t("control.revenue")}</dt>
            <dd>{money(c.metrics.revenue_minor, c.currency)}</dd>
          </div>
        ) : null}
        <div>
          <dt>{t("control.aiMessages")}</dt>
          <dd>{number(c.metrics.ai_messages)}</dd>
        </div>
        <div>
          <dt>{t("control.delivered")}</dt>
          <dd>{number(c.metrics.delivered)}</dd>
        </div>
        <div>
          <dt>{t("control.inTransit")}</dt>
          <dd>{number(c.metrics.in_transit)}</dd>
        </div>
        <div>
          <dt>{t("control.returns")}</dt>
          <dd>{number(c.metrics.returns)}</dd>
        </div>
      </dl>
      {total ? (
        <div className={styles.split}>
          <div className={styles.bar} role="img" aria-label={t("control.share", { pct: Math.round((c.automation.share_automatic ?? 0) * 100) })}>
            <span className={styles.barAuto} style={{ flexGrow: c.automation.done_automatically }} />
            <span className={styles.barTeam} style={{ flexGrow: c.automation.done_by_team }} />
          </div>
          <div className={styles.legend}>
            <span>
              {t("control.automatic")}: {number(c.automation.done_automatically)}
            </span>
            <span>
              {t("control.byTeam")}: {number(c.automation.done_by_team)}
            </span>
          </div>
        </div>
      ) : null}
      <Approvals onChanged={() => (cc.reload(), onChanged?.())} />
      <div>
        <SectionHeader title={t("control.feed")} id="cc-feed" action={<Link href="/automation?tab=activity">{t("control.seeAll")}</Link>} />
        {c.feed.length ? (
          <ol className={styles.feed} aria-labelledby="cc-feed" data-testid="autopilot-feed">
            {c.feed.slice(0, 6).map((d) => (
              <li key={d.id}>
                <span>{label(d.action)}</span>
                <span className={styles.muted}>
                  {explain(d)} ·{" "}
                  <time dateTime={d.created_at} title={dateTime(d.created_at)}>
                    {relative(d.created_at)}
                  </time>
                </span>
              </li>
            ))}
          </ol>
        ) : (
          <p className={styles.muted}>{t("control.feedEmpty")}</p>
        )}
      </div>
    </section>
  );
}

export function Approvals({ onChanged }: { onChanged?: () => void }) {
  const { t, relative } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const list = useApiQuery((a) => (can("automation.read") ? a.automation.approvals() : Promise.resolve({ items: [] as AutomationApproval[] })));
  const [skipping, setSkipping] = useState<AutomationApproval | null>(null);
  const [note, setNote] = useState("");
  const label = useActionLabel();
  const explain = useExplain();
  const items = list.state.status === "success" ? list.state.data.items : [];
  if (!items.length) return null;
  const done = (ok: unknown) => {
    if (!ok) return;
    toast(t("automation.approvals.done"));
    list.reload();
    onChanged?.();
  };
  return (
    <div data-testid="automation-approvals">
      <SectionHeader title={t("automation.approvals.title")} id="cc-approvals" />
      <ErrorAlert error={action.error} />
      <ul className={styles.list} aria-labelledby="cc-approvals">
        {items.map((a) => (
          <li key={a.id} className={styles.card}>
            <div className={styles.cardHead}>
              <strong>
                {a.kind === "approval" ? (a.note ?? a.workflow_name) : label(a.action)}
                {a.order_number ? (
                  <>
                    {" · "}
                    <Link href={`/orders/${a.order_id}`}>{t("automation.approvals.order", { number: a.order_number })}</Link>
                  </>
                ) : null}
              </strong>
              <span className={styles.muted}>{relative(a.requested_at)}</span>
            </div>
            <span className={styles.muted}>
              {a.workflow_name}
              {a.decision ? ` · ${t("automation.approvals.why", { reason: explain(a.decision) })}` : ""}
            </span>
            {can("automation.approve") ? (
              <div className={styles.row}>
                <Button size="sm" variant="primary" loading={action.pending} onClick={async () => done(await action.run(() => api.automation.approve(a.id)))}>
                  {t("automation.approvals.approve")}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setSkipping(a)}>
                  {t("automation.approvals.reject")}
                </Button>
              </div>
            ) : (
              <span className={styles.muted}>{t("automation.approvals.managerOnly")}</span>
            )}
          </li>
        ))}
      </ul>
      <ConfirmDialog
        open={skipping !== null}
        onOpenChange={(v) => !v && setSkipping(null)}
        title={t("automation.approvals.rejectTitle")}
        body={t("automation.approvals.rejectBody")}
        confirmLabel={t("automation.approvals.reject")}
        pending={action.pending}
        onConfirm={async () => {
          if (!skipping) return;
          done(await action.run(() => api.automation.reject(skipping.id, note.trim() || null)));
          setSkipping(null);
          setNote("");
        }}
      >
        <TextField label={t("automation.approvals.note")} value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} />
      </ConfirmDialog>
    </div>
  );
}
