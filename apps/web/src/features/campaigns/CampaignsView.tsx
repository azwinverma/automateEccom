"use client";

import {
  isApiError,
  type Campaign,
  type CampaignKind,
  type CampaignPreview,
  type CampaignSegment,
  type CampaignStatus,
  type CampaignTemplate,
} from "@commerce-os/api-client";
import { useEffect, useState, type FormEvent } from "react";
import { LimitActions } from "@/components/commerce/UsageMeter";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog, Drawer } from "@/components/ui/Drawer";
import { TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, InlineAlert, PageHeader, RequestId, SectionHeader, Skeleton, useToast, type Tone } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import cx from "../settings/connect.module.css";
import wf from "../shared/workflow.module.css";

export const KINDS: CampaignKind[] = ["win_back", "repeat_reminder", "broadcast"];
const SEGMENTS: CampaignSegment[] = ["all", "repeat", "new", "inactive"];
const STATUS_TONE: Record<CampaignStatus, Tone> = { draft: "neutral", active: "automated", paused: "warning", completed: "success" };
const MAX_MESSAGE = 900;

function ErrorLine({ error }: { error: unknown }) {
  const { t } = useI18n();
  if (!error) return null;
  return (
    <InlineAlert tone="danger">
      {errorMessage(t, error)}
      <RequestId id={isApiError(error) ? error.requestId : null} />
    </InlineAlert>
  );
}

function Rules() {
  const { t } = useI18n();
  const rules = [
    ["customers", "ruleChat"],
    ["shield", "ruleStop"],
    ["clock", "ruleCap"],
    ["sun", "ruleHours"],
    ["check", "ruleResult"],
  ] as const;
  return (
    <>
      <p className={cx.howTitle} id="campaign-rules">
        {t("campaigns.rulesTitle")}
      </p>
      <ul className={cx.how} aria-labelledby="campaign-rules" data-testid="campaign-rules">
        {rules.map(([icon, k]) => (
          <li key={k}>
            <Icon name={icon} />
            <span>{t(`campaigns.${k}`)}</span>
          </li>
        ))}
      </ul>
    </>
  );
}

export function reasonLabel(t: ReturnType<typeof useI18n>["t"], reason: string): string {
  return t.dynamic(`campaigns.reason.${reason}`) ?? t("campaigns.reason.other");
}

/** Retain. Never calls the campaigns API without the plan feature and read access (ADR-072). */
export function CampaignsView() {
  const { t } = useI18n();
  const { feature, can } = useAuth();
  const f = feature("marketing.campaigns");
  return (
    <>
      <PageHeader title={t("campaigns.title")} subtitle={t("campaigns.subtitle")} />
      {f === "pending" ? (
        <Skeleton height={160} />
      ) : f === "no" ? (
        <>
          <Rules />
          <InlineAlert tone="info" title={t("campaigns.upsellTitle")} live={false}>
            <LimitActions buyCredits={false} upgrade />
          </InlineAlert>
        </>
      ) : !can("customers.read") ? (
        <InlineAlert tone="info" live={false}>
          {t("campaigns.noAccess")}
        </InlineAlert>
      ) : (
        <CampaignList />
      )}
    </>
  );
}

function CampaignList() {
  const { t, money, number } = useI18n();
  const { can } = useAuth();
  const toast = useToast();
  const list = useApiQuery((a) => a.campaigns.list());
  const templates = useApiQuery((a) => a.campaigns.templates());
  const [creating, setCreating] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const write = can("automation.write");
  const items = list.state.status === "success" ? list.state.data.items : [];
  const open = items.find((c) => c.id === openId) ?? null;

  return (
    <>
      <Rules />
      <SectionHeader
        title={t("campaigns.title")}
        id="campaigns-heading"
        action={
          write ? (
            <Button size="sm" variant="primary" onClick={() => setCreating(true)}>
              <Icon name="plus" />
              {t("campaigns.new")}
            </Button>
          ) : undefined
        }
      />
      {list.state.status === "loading" ? (
        <TableSkeleton columns="1.6fr 1fr 1.6fr" rows={3} label={t("common.loading")} />
      ) : list.state.status === "error" ? (
        <QueryError error={list.state.error} onRetry={list.reload} />
      ) : items.length === 0 ? (
        <EmptyState
          title={t("campaigns.empty")}
          body={t("campaigns.emptyBody")}
          actions={
            write ? (
              <Button variant="primary" onClick={() => setCreating(true)}>
                {t("campaigns.new")}
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className={table.wrap}>
          <table className={[table.table, table.clickable].join(" ")} aria-labelledby="campaigns-heading" data-testid="campaigns">
            <thead>
              <tr>
                <th scope="col">{t("campaigns.colCampaign")}</th>
                <th scope="col">{t("campaigns.colStatus")}</th>
                <th scope="col" className={table.hideSm}>
                  {t("campaigns.colResults")}
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} data-kind={c.kind}>
                  <td>
                    <div className={table.primaryCell}>
                      <strong>
                        <button type="button" className={cx.rowButton} onClick={() => setOpenId(c.id)}>
                          {c.name}
                        </button>
                      </strong>
                      <span>{t(`campaigns.kind.${c.kind}`)}</span>
                    </div>
                  </td>
                  <td>
                    <Badge tone={STATUS_TONE[c.status]}>{t(`campaigns.status.${c.status}`)}</Badge>
                  </td>
                  <td className={table.hideSm}>
                    {t("campaigns.results", { sent: number(c.stats.sent), replied: number(c.stats.replied), orders: number(c.stats.orders) })}
                    {c.stats.revenue_minor > 0 ? <span className={cx.meta}>{t("campaigns.revenue", { amount: money(c.stats.revenue_minor) })}</span> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <CreateDrawer
        open={creating}
        templates={templates.state.status === "success" ? templates.state.data : null}
        onOpenChange={setCreating}
        onCreated={(c) => {
          setCreating(false);
          list.setData((d) => ({ items: [c, ...d.items] }));
          toast(t("campaigns.created"));
          setOpenId(c.id);
        }}
      />
      <CampaignDrawer
        campaign={open}
        placeholders={templates.state.status === "success" ? templates.state.data.placeholders : []}
        onClose={() => setOpenId(null)}
        onChanged={(c) => list.setData((d) => ({ items: d.items.map((x) => (x.id === c.id ? c : x)) }))}
      />
    </>
  );
}

function MessageField({ id, label, value, onChange, disabled }: { id: string; label: string; value: string; onChange: (v: string) => void; disabled?: boolean }) {
  const { t, number } = useI18n();
  return (
    <div>
      <label htmlFor={id} className={cx.label}>
        {label}
      </label>
      <textarea id={id} className={cx.textarea} value={value} onChange={(e) => onChange(e.target.value)} maxLength={MAX_MESSAGE} disabled={disabled} aria-describedby={`${id}-count`} />
      <p id={`${id}-count`} className={cx.counter} aria-live="off">
        {number(value.length)} / {number(MAX_MESSAGE)}
        <span className="srOnly">{t("campaigns.optOutAdded")}</span>
      </p>
    </div>
  );
}

function Placeholders({ tokens }: { tokens: string[] }) {
  const { t } = useI18n();
  if (!tokens.length) return null;
  return (
    <div className={wf.stack} style={{ gap: "var(--space-1)" }}>
      <p className={cx.tokens}>
        <span>{t("campaigns.placeholders")}</span>
        {tokens.map((p) => (
          <code key={p}>{p}</code>
        ))}
      </p>
      <p className={wf.hint} style={{ margin: 0 }}>
        {t("campaigns.placeholderHelp")} {t("campaigns.optOutAdded")}
      </p>
    </div>
  );
}

function CreateDrawer({
  open,
  templates,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  templates: { items: CampaignTemplate[]; placeholders: string[] } | null;
  onOpenChange: (o: boolean) => void;
  onCreated: (c: Campaign) => void;
}) {
  const { t } = useI18n();
  const { api } = useAuth();
  const action = useAction();
  const [kind, setKind] = useState<CampaignKind>("win_back");
  const [name, setName] = useState("");
  const [days, setDays] = useState("");
  const [segment, setSegment] = useState<CampaignSegment>("all");
  const [en, setEn] = useState("");
  const [ne, setNe] = useState("");
  const [limit, setLimit] = useState("200");
  const [attempted, setAttempted] = useState(false);
  const tpl = templates?.items.find((x) => x.kind === kind);

  useEffect(() => {
    if (!open) return;
    setKind("win_back");
    setName("");
    setSegment("all");
    setLimit("200");
    setAttempted(false);
    action.clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);
  useEffect(() => {
    setEn(tpl?.message_en ?? "");
    setNe(tpl?.message_ne ?? "");
    setDays(tpl?.default_days ? String(tpl.default_days) : "");
  }, [tpl]);

  const daysN = Number(days);
  const daysErr = kind !== "broadcast" && attempted && !(Number.isInteger(daysN) && daysN >= 1 && daysN <= 365) ? t("errors.invalid_days") : undefined;
  const nameErr = attempted && !name.trim() ? t("errors.field.required") : undefined;
  const msgErr = attempted && !en.trim() ? t("errors.message_required") : undefined;
  const limitN = Number(limit);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setAttempted(true);
    if (!name.trim() || !en.trim() || (kind !== "broadcast" && !(Number.isInteger(daysN) && daysN >= 1 && daysN <= 365))) return;
    const c = await action.run(() =>
      api.campaigns.create({
        name: name.trim(),
        kind,
        days: kind === "broadcast" ? null : daysN,
        segment: kind === "broadcast" ? segment : null,
        message_en: en.trim(),
        message_ne: ne.trim() || null,
        daily_limit: Number.isInteger(limitN) && limitN >= 1 && limitN <= 2000 ? limitN : 200,
      }),
    );
    if (c) onCreated(c);
  };

  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      wide
      title={t("campaigns.new")}
      footer={
        <>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            {t("common.cancel")}
          </Button>
          <Button variant="primary" type="submit" form="campaign-form" loading={action.pending}>
            {t("campaigns.saveDraft")}
          </Button>
        </>
      }
    >
      <form id="campaign-form" className={wf.stack} onSubmit={submit} noValidate>
        <ErrorLine error={action.error} />
        <fieldset className={cx.choice}>
          <legend>{t("campaigns.typeLegend")}</legend>
          {KINDS.map((k) => (
            <label key={k} className={cx.choiceOption}>
              <input type="radio" name="campaign-kind" value={k} checked={kind === k} onChange={() => setKind(k)} />
              <strong>{t(`campaigns.kind.${k}`)}</strong>
              <span>{t(`campaigns.kindHelp.${k}`)}</span>
            </label>
          ))}
        </fieldset>
        <TextField label={t("campaigns.name")} value={name} onChange={(e) => setName(e.target.value)} error={nameErr} maxLength={120} placeholder={t(`campaigns.kind.${kind}`)} />
        {kind === "broadcast" ? (
          <fieldset className={cx.choice}>
            <legend>{t("campaigns.audienceLegend")}</legend>
            {SEGMENTS.map((s) => (
              <label key={s} className={cx.choiceOption}>
                <input type="radio" name="campaign-segment" value={s} checked={segment === s} onChange={() => setSegment(s)} />
                <strong>{t(`campaigns.segment.${s}`)}</strong>
                <span />
              </label>
            ))}
          </fieldset>
        ) : (
          <TextField
            label={kind === "win_back" ? t("campaigns.daysWinBack") : t("campaigns.daysReminder")}
            value={days}
            onChange={(e) => setDays(e.target.value.replace(/\D/g, ""))}
            error={daysErr}
            inputMode="numeric"
            maxLength={3}
          />
        )}
        <Placeholders tokens={templates?.placeholders ?? []} />
        <MessageField id="campaign-en" label={t("campaigns.messageEn")} value={en} onChange={setEn} />
        {msgErr ? <p className={wf.hint} role="alert">{msgErr}</p> : null}
        <MessageField id="campaign-ne" label={t("campaigns.messageNe")} value={ne} onChange={setNe} />
        <TextField label={t("campaigns.dailyLimit")} value={limit} onChange={(e) => setLimit(e.target.value.replace(/\D/g, ""))} inputMode="numeric" maxLength={4} />
      </form>
    </Drawer>
  );
}

function PreviewPanel({ campaignId, version }: { campaignId: string; version: number }) {
  const { t, number } = useI18n();
  const { api } = useAuth();
  const [p, setP] = useState<CampaignPreview | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    let live = true;
    setP(null);
    setError(null);
    api.campaigns.preview(campaignId).then(
      (r) => live && setP(r),
      (e) => live && setError(e),
    );
    return () => {
      live = false;
    };
  }, [api, campaignId, version]);
  return (
    <section aria-labelledby="preview-heading" className={wf.stack} data-testid="campaign-preview">
      <h3 id="preview-heading" className={cx.howTitle}>
        {t("campaigns.previewHeading")}
      </h3>
      {error ? (
        <ErrorLine error={error} />
      ) : !p ? (
        <p className={wf.hint} role="status">
          {t("campaigns.previewLoading")}
        </p>
      ) : (
        <>
          <p style={{ margin: 0 }}>
            {p.audience === 0 ? t("campaigns.previewNone") : t("campaigns.previewReach", { reachable: number(p.reachable), audience: number(p.audience) })}
          </p>
          {Object.keys(p.unreachable).length ? (
            <>
              <p className={cx.howTitle}>{t("campaigns.unreachable")}</p>
              <ul className={cx.reasons}>
                {Object.entries(p.unreachable).map(([r, n]) => (
                  <li key={r}>
                    <span>{reasonLabel(t, r)}</span>
                    <span>{number(n ?? 0)}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          <p className={cx.howTitle}>{t("campaigns.sample")}</p>
          <blockquote className={cx.sample} data-testid="campaign-sample">
            {p.sample_en}
          </blockquote>
        </>
      )}
    </section>
  );
}

function CampaignDrawer({ campaign, placeholders, onClose, onChanged }: { campaign: Campaign | null; placeholders: string[]; onClose: () => void; onChanged: (c: Campaign) => void }) {
  const { t, money, number, relative } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const [en, setEn] = useState("");
  const [ne, setNe] = useState("");
  const [confirm, setConfirm] = useState<"active" | "completed" | null>(null);
  const [version, setVersion] = useState(0);
  const write = can("automation.write");
  const approve = can("automation.approve");
  const editable = campaign !== null && (campaign.status === "draft" || campaign.status === "paused") && write;

  useEffect(() => {
    setEn(campaign?.message_en ?? "");
    setNe(campaign?.message_ne ?? "");
    action.clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campaign?.id]);

  if (!campaign) return null;
  const dirty = en !== campaign.message_en || ne !== (campaign.message_ne ?? "");

  const setStatus = async (status: "active" | "paused" | "completed") => {
    const c = await action.run(() => api.campaigns.setStatus(campaign.id, status));
    setConfirm(null);
    if (!c) return;
    onChanged(c);
    toast(t(status === "active" ? "campaigns.started" : status === "paused" ? "campaigns.paused" : "campaigns.finished"));
  };
  const save = async () => {
    const c = await action.run(() => api.campaigns.update(campaign.id, { message_en: en.trim(), message_ne: ne.trim() || null }));
    if (!c) return;
    onChanged(c);
    setVersion((v) => v + 1);
    toast(t("campaigns.savedToast"));
  };
  const skipped = Object.entries(campaign.stats.skipped);

  return (
    <>
      <Drawer
        open
        onOpenChange={(o) => !o && onClose()}
        wide
        title={t("campaigns.detailTitle", { name: campaign.name })}
        description={`${t(`campaigns.kind.${campaign.kind}`)} · ${t(`campaigns.status.${campaign.status}`)}`}
        footer={
          approve ? (
            <div className={wf.rowActions} style={{ width: "100%", justifyContent: "flex-end" }}>
              {campaign.status === "active" ? (
                <Button variant="secondary" loading={action.pending} onClick={() => setStatus("paused")}>
                  {t("campaigns.pause")}
                </Button>
              ) : null}
              {campaign.status === "active" || campaign.status === "paused" ? (
                <Button variant="ghost" onClick={() => setConfirm("completed")}>
                  {t("campaigns.finish")}
                </Button>
              ) : null}
              {campaign.status === "draft" || campaign.status === "paused" ? (
                <Button variant="primary" disabled={dirty} onClick={() => setConfirm("active")}>
                  {campaign.status === "paused" ? t("campaigns.resume") : t("campaigns.start")}
                </Button>
              ) : null}
            </div>
          ) : undefined
        }
      >
        <div className={wf.stack}>
          <ErrorLine error={action.error} />
          {!approve && campaign.status !== "completed" ? (
            <InlineAlert tone="info" live={false}>
              {t("campaigns.approveOnly")}
            </InlineAlert>
          ) : null}
          {campaign.status !== "draft" ? (
            <section aria-labelledby="stats-heading" className={wf.stack}>
              <h3 id="stats-heading" className={cx.howTitle}>
                {t("campaigns.statsHeading")}
              </h3>
              <dl className={cx.stats} data-testid="campaign-stats">
                <div>
                  <dt>{t("campaigns.statSent")}</dt>
                  <dd>{number(campaign.stats.sent)}</dd>
                </div>
                <div>
                  <dt>{t("campaigns.statReplied")}</dt>
                  <dd>{number(campaign.stats.replied)}</dd>
                </div>
                <div>
                  <dt>{t("campaigns.statOrders")}</dt>
                  <dd>{number(campaign.stats.orders)}</dd>
                </div>
                <div>
                  <dt>{t("campaigns.statRevenue")}</dt>
                  <dd>{money(campaign.stats.revenue_minor)}</dd>
                </div>
              </dl>
              <p className={wf.hint} style={{ margin: 0 }}>
                {campaign.last_run_at ? t("campaigns.lastRun", { when: relative(campaign.last_run_at) }) : t("campaigns.notRun")}
              </p>
              {skipped.length ? (
                <>
                  <p className={cx.howTitle}>{t("campaigns.skippedHeading")}</p>
                  <ul className={cx.reasons}>
                    {skipped.map(([r, n]) => (
                      <li key={r}>
                        <span>{reasonLabel(t, r)}</span>
                        <span>{number(n ?? 0)}</span>
                      </li>
                    ))}
                  </ul>
                </>
              ) : null}
            </section>
          ) : null}
          {campaign.status !== "completed" ? <PreviewPanel campaignId={campaign.id} version={version} /> : null}
          <Placeholders tokens={placeholders} />
          {campaign.status === "active" && write ? <p className={wf.hint}>{t("campaigns.editLocked")}</p> : null}
          <MessageField id="detail-en" label={t("campaigns.messageEn")} value={en} onChange={setEn} disabled={!editable} />
          <MessageField id="detail-ne" label={t("campaigns.messageNe")} value={ne} onChange={setNe} disabled={!editable} />
          {editable ? (
            <div>
              <Button variant="secondary" disabled={!dirty || !en.trim()} loading={action.pending} onClick={save}>
                {t("campaigns.save")}
              </Button>
            </div>
          ) : null}
        </div>
      </Drawer>
      <ConfirmDialog
        open={confirm !== null}
        onOpenChange={(o) => !o && setConfirm(null)}
        title={confirm === "completed" ? t("campaigns.finishTitle", { name: campaign.name }) : t("campaigns.startTitle", { name: campaign.name })}
        body={confirm === "completed" ? t("campaigns.finishBody") : t("campaigns.startBody")}
        confirmLabel={confirm === "completed" ? t("campaigns.finish") : campaign.status === "paused" ? t("campaigns.resume") : t("campaigns.start")}
        destructive={confirm === "completed"}
        pending={action.pending}
        onConfirm={() => confirm && setStatus(confirm)}
      >
        <ErrorLine error={action.error} />
      </ConfirmDialog>
    </>
  );
}
