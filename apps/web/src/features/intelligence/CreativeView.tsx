"use client";

import { isApiError, type CreativeAttribute, type CreativeExperiment, type CreativeGenome, type CreativePostRow } from "@commerce-os/api-client";
import { useState, type FormEvent } from "react";
import { LimitActions } from "@/components/commerce/UsageMeter";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { SelectField, TextField } from "@/components/ui/Field";
import { Badge, InlineAlert, PageHeader, Skeleton, useToast } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery, type QueryResult } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ContentTabs } from "../content/ContentTabs";
import { ErrorAlert } from "../orders/shared";
import { attrLabel, CREATIVE_ATTRIBUTES, CREATIVE_VOCAB, outcomeWord, times, valueLabel } from "./creativeLabels";
import styles from "./intelligence.module.css";
import { isPlanGate } from "./ProfitView";

/** Content → What sells: Creative Genome (UX-022), post results (CNT-013/014) and tests (CGN-003). */
export function CreativeView() {
  const { t } = useI18n();
  const genome = useApiQuery((a) => a.intelligence.creativeGenome());
  const gated = genome.state.status === "error" && isPlanGate(genome.state.error);
  return (
    <>
      <PageHeader title={t("content.title")} subtitle={t("intel.creative.subtitle")} />
      <ContentTabs />
      <GenomePanel q={genome} />
      <PostResults />
      {gated ? null : <Experiments />}
    </>
  );
}

type GenomeQuery = QueryResult<CreativeGenome>;

export function GenomePanel({ q }: { q: GenomeQuery }) {
  const { t, number } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  if (q.state.status === "loading") return <Skeleton height={120} />;
  if (q.state.status === "error") {
    if (isPlanGate(q.state.error))
      return (
        <InlineAlert tone="info" title={t("intel.creative.upsell")}>
          <LimitActions buyCredits={false} upgrade />
        </InlineAlert>
      );
    return <ErrorAlert error={q.state.error} />;
  }
  const g = q.state.data;
  const outcome = outcomeWord(t, g.baseline?.outcome);
  const recommended = g.preferences.filter((p) => p.recommended);
  const likes = g.preferences.filter((p) => p.engagement_only);
  const refresh = async () => {
    if (await action.run(() => api.intelligence.refreshCreative())) {
      toast(t("intel.creative.refreshed"));
      q.reload();
    }
  };
  return (
    <section className={styles.card} aria-labelledby="genome-title" data-testid="creative-genome" data-status={g.status}>
      <div className={styles.head}>
        <h2 id="genome-title">{g.status === "ready" ? t("intel.creative.readyTitle") : t("intel.creative.learningTitle")}</h2>
        <span className={styles.row}>
          {g.version ? <span className={styles.muted}>{t("intel.creative.version", { v: g.version })}</span> : null}
          <Button size="sm" variant="ghost" loading={action.pending} onClick={refresh}>
            {t("intel.creative.refresh")}
          </Button>
        </span>
      </div>
      <ErrorAlert error={action.error} />
      {g.status === "learning" ? (
        <>
          <p style={{ margin: 0 }}>{t("intel.creative.learningBody", { n: g.measured_posts, min: g.min_posts })}</p>
          <div
            className={styles.meter}
            role="meter"
            aria-valuemin={0}
            aria-valuemax={g.min_posts}
            aria-valuenow={Math.min(g.measured_posts, g.min_posts)}
            aria-label={t("intel.creative.learningMeter", { n: g.measured_posts, min: g.min_posts })}
          >
            <span style={{ width: `${Math.min(100, (100 * g.measured_posts) / Math.max(1, g.min_posts))}%` }} />
          </div>
          <span className={styles.muted} data-testid="genome-progress">
            {t("intel.creative.learningMeter", { n: g.measured_posts, min: g.min_posts })}
          </span>
        </>
      ) : (
        <>
          <span className={styles.muted}>{t("intel.creative.basedOn", { n: g.posts, days: g.baseline?.lookback_days ?? 180, outcome })}</span>
          {g.baseline?.outcome === "inquiries" ? <span className={styles.muted}>{t("intel.creative.outcomeNoteInquiries")}</span> : null}
          <h3 className={styles.subhead}>{t("intel.creative.doMore")}</h3>
          {recommended.length === 0 ? (
            <p className={styles.muted} style={{ margin: 0 }}>
              {t("intel.creative.noneYet")}
            </p>
          ) : (
            <ul className={styles.patterns}>
              {recommended.map((p) => (
                <li key={`${p.attribute}:${p.value}`} className={styles.pattern} data-testid="genome-pattern" data-attribute={p.attribute}>
                  <span className={styles.patternLabel}>{attrLabel(t, p.attribute)}</span>
                  <strong>{valueLabel(t, p.attribute, p.value)}</strong>
                  <span>{t("intel.creative.patternLift", { times: times(number, p.lift), outcome })}</span>
                  <span className={styles.row}>
                    <Badge tone={p.confidence === "high" ? "success" : "info"} dot={false}>
                      {t(p.confidence === "high" ? "intel.creative.conf_high" : p.confidence === "medium" ? "intel.creative.conf_medium" : "intel.creative.conf_low")}
                    </Badge>
                    <span className={styles.muted}>{t("intel.creative.sample", { n: p.n })}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
          {likes.length ? (
            <div data-testid="genome-likes">
              <h3 className={styles.subhead}>{t("intel.creative.likesTitle")}</h3>
              <span className={styles.muted}>{t("intel.creative.likesHint")}</span>
              <ul className={styles.missing} style={{ color: "var(--color-text-primary)" }}>
                {likes.map((p) => (
                  <li key={`${p.attribute}:${p.value}`}>
                    {t("intel.creative.likesItem", { pattern: valueLabel(t, p.attribute, p.value), pct: Math.round((p.engagement_lift ?? 0) * 100) })}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      )}
      <ImpactNote g={g} />
    </section>
  );
}

function ImpactNote({ g }: { g: CreativeGenome }) {
  const { t, number } = useI18n();
  const i = g.impact;
  const f = (x: number | null) => (x === null ? "–" : number(x, { maximumFractionDigits: 1 }));
  return (
    <div className={styles.fair} data-testid="genome-impact">
      <strong>{t("intel.creative.impactTitle")}</strong>{" "}
      {i.genome_posts === 0 ? (
        t("intel.creative.impactEmpty")
      ) : (
        <>
          {t("intel.creative.impactBody", { gn: i.genome_posts, gm: f(i.genome_mean_orders), om: f(i.other_mean_orders), on: i.other_posts })}
          {typeof i.lift === "number" ? ` ${t("intel.creative.impactLift", { times: times(number, i.lift) })}` : null} {t("intel.creative.impactNote")}
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ post results */
export function PostResults() {
  const { t } = useI18n();
  const q = useApiQuery((a) => a.intelligence.creativePosts(50));
  const [adding, setAdding] = useState<CreativePostRow | null>(null);
  if (q.state.status === "loading") return <Skeleton height={80} />;
  if (q.state.status === "error") return <ErrorAlert error={q.state.error} />;
  const { items, currency } = q.state.data;
  return (
    <section className={styles.card} aria-labelledby="results-title" data-testid="post-results">
      <div className={styles.head}>
        <h2 id="results-title">{t("intel.creative.resultsTitle")}</h2>
      </div>
      <span className={styles.muted}>{t("intel.creative.resultsHint")}</span>
      {items.length === 0 ? (
        <p className={styles.muted} style={{ margin: 0 }}>
          {t("intel.creative.resultsEmpty")}
        </p>
      ) : (
        <>
          <ul className={styles.postRows}>
            {items.map((r) => (
              <PostResultRow key={r.post_id} row={r} currency={currency} onAdd={() => setAdding(r)} />
            ))}
          </ul>
          <span className={styles.muted}>{t("intel.creative.ordersShared")}</span>
        </>
      )}
      <AddResultsDrawer
        key={adding?.post_id ?? "none"}
        row={adding}
        onClose={() => setAdding(null)}
        onSaved={() => {
          setAdding(null);
          q.reload();
        }}
      />
    </section>
  );
}

function PostResultRow({ row, currency, onAdd }: { row: CreativePostRow; currency?: string; onAdd: () => void }) {
  const { t, number, money, date } = useI18n();
  const { can } = useAuth();
  const m = row.metrics;
  const n = (x: number | null | undefined) => (x === null || x === undefined ? "–" : number(x));
  const source = m?.source ?? null;
  return (
    <li className={styles.postRow} data-testid="post-result" data-post={row.post_id}>
      <div className={styles.postHead}>
        <span className={styles.postCaption}>
          <strong>{t.dynamic(`content.kind.${row.kind}`) ?? row.kind}</strong> · {row.caption}
        </span>
        <span className={styles.row}>
          {row.published_at ? <span className={styles.muted}>{t("intel.creative.publishedOn", { when: date(row.published_at) })}</span> : null}
          {row.genome_version ? (
            <Badge tone="automated" dot={false}>
              {t("intel.creative.genomeTag")}
            </Badge>
          ) : null}
        </span>
      </div>
      <dl className={styles.postStats}>
        <div>
          <dt>{t("intel.creative.views")}</dt>
          <dd>{n(m?.views)}</dd>
        </div>
        <div>
          <dt>{t("intel.creative.engagements")}</dt>
          <dd>{n(m?.engagements)}</dd>
        </div>
        <div>
          <dt>{t("intel.creative.clicks")}</dt>
          <dd>{n(m?.clicks)}</dd>
        </div>
        <div>
          <dt>{t("intel.creative.chats")}</dt>
          <dd>{n(m?.inquiries ?? 0)}</dd>
        </div>
        <div>
          <dt>{t("intel.creative.orders")}</dt>
          <dd>{number(m?.orders ?? 0, { maximumFractionDigits: 1 })}</dd>
        </div>
        <div>
          <dt>{t("intel.creative.revenue")}</dt>
          <dd>{money(m?.revenue_minor ?? 0, currency)}</dd>
        </div>
        <div>
          <dt>{t("intel.creative.margin")}</dt>
          <dd>{m && m.contribution_minor !== null ? money(m.contribution_minor, currency) : m && m.orders > 0 ? t("intel.creative.costNotSet") : "–"}</dd>
        </div>
      </dl>
      <div className={styles.row} style={{ justifyContent: "space-between" }}>
        <span className={styles.row}>
          <span className={styles.sourceTag} data-source={source ?? "none"}>
            {t(source === "channel" ? "intel.creative.source_channel" : source === "manual" ? "intel.creative.source_manual" : "intel.creative.source_none")}
          </span>
          <span className={styles.muted}>{t(`intel.creative.method_${m?.attribution.method ?? "none"}`)}</span>
          {m && !m.window_complete ? <span className={styles.muted}>{t("intel.creative.measuring")}</span> : null}
        </span>
        {can("content.write") ? (
          <Button size="sm" variant="secondary" onClick={onAdd}>
            {t("intel.creative.addResults")}
          </Button>
        ) : null}
      </div>
    </li>
  );
}

const FIELDS = ["views", "likes", "comments", "shares", "saves", "clicks"] as const;
type MetricField = (typeof FIELDS)[number];

export function AddResultsDrawer({ row, onClose, onSaved }: { row: CreativePostRow | null; onClose: () => void; onSaved: () => void }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const action = useAction();
  const [vals, setVals] = useState<Record<MetricField, string>>({ views: "", likes: "", comments: "", shares: "", saves: "", clicks: "" });
  const [formErr, setFormErr] = useState<string | null>(null);
  if (!row) return null;
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const body: Partial<Record<MetricField, number>> = {};
    for (const f of FIELDS) {
      const raw = vals[f].trim();
      if (!raw) continue;
      const v = Number(raw);
      if (!Number.isInteger(v) || v < 0) return setFormErr(t("intel.creative.wholeNumber"));
      body[f] = v;
    }
    if (!Object.keys(body).length) return setFormErr(t("intel.creative.needOne"));
    setFormErr(null);
    if (await action.run(() => api.intelligence.addPostMetrics(row.post_id, body))) {
      toast(t("intel.creative.saved"));
      onSaved();
    }
  };
  return (
    <Drawer
      open
      onOpenChange={(o) => !o && onClose()}
      title={t("intel.creative.addTitle")}
      description={row.caption}
      footer={
        <Button variant="primary" type="submit" form="post-metrics-form" loading={action.pending}>
          {t("intel.creative.saveResults")}
        </Button>
      }
    >
      <form id="post-metrics-form" onSubmit={submit} noValidate className={styles.formStack} data-testid="post-metrics-form">
        <p className={styles.muted} style={{ margin: 0 }}>
          {t("intel.creative.addHint")}
        </p>
        {formErr ? (
          <p role="alert" className={styles.formError}>
            {formErr}
          </p>
        ) : null}
        {action.error ? <InlineAlert tone="danger">{errorMessage(t, action.error)}</InlineAlert> : null}
        <div className={styles.formGrid}>
          {FIELDS.map((f) => (
            <TextField
              key={f}
              label={t(`intel.creative.${f}`)}
              type="number"
              inputMode="numeric"
              min={0}
              step={1}
              value={vals[f]}
              onChange={(e) => setVals((v) => ({ ...v, [f]: e.target.value }))}
            />
          ))}
        </div>
      </form>
    </Drawer>
  );
}

/* ------------------------------------------------------------------ experiments */
export function Experiments() {
  const { t, number, date } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const q = useApiQuery((a) => a.intelligence.experiments());
  const [creating, setCreating] = useState(false);
  if (q.state.status === "loading") return <Skeleton height={80} />;
  if (q.state.status === "error") return isPlanGate(q.state.error) ? null : <ErrorAlert error={q.state.error} />;
  const items = q.state.data.items;
  const canRun = can("content.publish");
  return (
    <section className={styles.card} aria-labelledby="exp-title" data-testid="creative-experiments">
      <div className={styles.head}>
        <h2 id="exp-title">{t("intel.creative.expTitle")}</h2>
        {canRun ? (
          <Button size="sm" variant="secondary" onClick={() => setCreating(true)}>
            {t("intel.creative.expNew")}
          </Button>
        ) : null}
      </div>
      <span className={styles.muted}>{t("intel.creative.expHint")}</span>
      <ErrorAlert error={action.error} />
      {items.length === 0 ? (
        <p className={styles.muted} style={{ margin: 0 }}>
          {t("intel.creative.expEmpty")}
        </p>
      ) : (
        <ul className={styles.facts}>
          {items.map((e) => (
            <li key={e.id} className={styles.fact} data-testid="experiment" data-status={e.status}>
              <span className={styles.row} style={{ justifyContent: "space-between" }}>
                <strong>{e.name}</strong>
                <Badge tone={e.status === "running" ? "info" : e.status === "concluded" ? "success" : "neutral"} dot={false}>
                  {t(`intel.creative.status_${e.status}`)}
                </Badge>
              </span>
              <span>{e.hypothesis}</span>
              <span className={styles.muted}>
                {attrLabel(t, e.attribute)}: {valueLabel(t, e.attribute, e.variant_a)} / {valueLabel(t, e.attribute, e.variant_b)}
              </span>
              <span data-testid="experiment-verdict">{verdict(t, number, e)}</span>
              <span className={styles.muted}>
                {t("intel.creative.expProgress", {
                  a: valueLabel(t, e.attribute, e.variant_a),
                  b: valueLabel(t, e.attribute, e.variant_b),
                  an: e.result?.a.n ?? 0,
                  bn: e.result?.b.n ?? 0,
                  min: e.min_posts,
                })}
                {e.status === "running" ? ` · ${t("intel.creative.expEndsBy", { date: date(e.ends_by) })}` : null}
              </span>
              {e.status === "running" && canRun ? (
                <span className={styles.row}>
                  <Button
                    size="sm"
                    variant="ghost"
                    loading={action.pending}
                    onClick={async () => {
                      if (await action.run(() => api.intelligence.stopExperiment(e.id))) {
                        toast(t("intel.creative.expStopped"));
                        q.reload();
                      }
                    }}
                  >
                    {t("intel.creative.expStop")}
                  </Button>
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      <NewExperimentDrawer
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={() => {
          setCreating(false);
          toast(t("intel.creative.expCreated"));
          q.reload();
        }}
      />
    </section>
  );
}

type T = ReturnType<typeof useI18n>["t"];

export function verdict(t: T, number: ReturnType<typeof useI18n>["number"], e: CreativeExperiment): string {
  const r = e.result;
  if (!r || "status" in r) return t("intel.creative.verdict_collecting");
  if (r.verdict === "clear" && r.winner) {
    const win = r.winner === "a" ? r.a : r.b;
    const lose = r.winner === "a" ? r.b : r.a;
    const f = (x: number | null) => (x === null ? "–" : number(x, { maximumFractionDigits: 2 }));
    return t("intel.creative.verdict_clear", {
      winner: valueLabel(t, e.attribute, r.winner === "a" ? e.variant_a : e.variant_b),
      wm: f(win.mean),
      lm: f(lose.mean),
      outcome: outcomeWord(t, e.metric),
    });
  }
  return t(r.verdict === "no_clear_difference" ? "intel.creative.verdict_no_clear_difference" : "intel.creative.verdict_not_enough_posts");
}

export function NewExperimentDrawer({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const action = useAction();
  const [name, setName] = useState("");
  const [hypothesis, setHypothesis] = useState("");
  const [attribute, setAttribute] = useState<CreativeAttribute>("hook_type");
  const [a, setA] = useState(CREATIVE_VOCAB.hook_type[0]!);
  const [b, setB] = useState(CREATIVE_VOCAB.hook_type[1]!);
  const [metric, setMetric] = useState<"orders" | "inquiries">("orders");
  const [minPosts, setMinPosts] = useState("5");
  const [maxDays, setMaxDays] = useState("30");
  const [formErr, setFormErr] = useState<string | null>(null);
  if (!open) return null;
  const vocab = CREATIVE_VOCAB[attribute];
  const pickAttribute = (x: CreativeAttribute) => {
    setAttribute(x);
    setA(CREATIVE_VOCAB[x][0]!);
    setB(CREATIVE_VOCAB[x][1]!);
  };
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const mp = Number(minPosts);
    const md = Number(maxDays);
    if (name.trim().length < 3 || hypothesis.trim().length < 3) return setFormErr(t("intel.creative.expRequired"));
    if (a === b) return setFormErr(t("intel.creative.expSame"));
    if (!Number.isInteger(mp) || mp < 3 || mp > 50 || !Number.isInteger(md) || md < 7 || md > 90) return setFormErr(t("intel.creative.expRange"));
    setFormErr(null);
    const body = { name: name.trim(), hypothesis: hypothesis.trim(), attribute, variant_a: a, variant_b: b, metric, min_posts: mp, max_days: md };
    if (await action.run(() => api.intelligence.createExperiment(body))) {
      setName("");
      setHypothesis("");
      onCreated();
    }
  };
  const conflict = isApiError(action.error) && action.error.status === 409;
  return (
    <Drawer
      open
      onOpenChange={(o) => !o && onClose()}
      title={t("intel.creative.expNew")}
      footer={
        <Button variant="primary" type="submit" form="experiment-form" loading={action.pending}>
          {t("intel.creative.expCreate")}
        </Button>
      }
    >
      <form id="experiment-form" onSubmit={submit} noValidate className={styles.formStack} data-testid="experiment-form">
        {formErr ? (
          <p role="alert" className={styles.formError}>
            {formErr}
          </p>
        ) : null}
        {action.error ? <InlineAlert tone={conflict ? "warning" : "danger"}>{errorMessage(t, action.error)}</InlineAlert> : null}
        <TextField label={t("intel.creative.expName")} value={name} onChange={(e) => setName(e.target.value)} maxLength={120} required />
        <TextField label={t("intel.creative.expHypothesis")} value={hypothesis} onChange={(e) => setHypothesis(e.target.value)} maxLength={300} required />
        <SelectField label={t("intel.creative.expAttribute")} value={attribute} onChange={(e) => pickAttribute(e.target.value as CreativeAttribute)}>
          {CREATIVE_ATTRIBUTES.map((x) => (
            <option key={x} value={x}>
              {attrLabel(t, x)}
            </option>
          ))}
        </SelectField>
        <div className={styles.formGrid}>
          <SelectField label={t("intel.creative.expA")} value={a} onChange={(e) => setA(e.target.value)}>
            {vocab.map((v) => (
              <option key={v} value={v}>
                {valueLabel(t, attribute, v)}
              </option>
            ))}
          </SelectField>
          <SelectField label={t("intel.creative.expB")} value={b} onChange={(e) => setB(e.target.value)}>
            {vocab.map((v) => (
              <option key={v} value={v}>
                {valueLabel(t, attribute, v)}
              </option>
            ))}
          </SelectField>
        </div>
        <SelectField label={t("intel.creative.expMetric")} value={metric} onChange={(e) => setMetric(e.target.value as "orders" | "inquiries")}>
          <option value="orders">{t("intel.creative.orders")}</option>
          <option value="inquiries">{t("intel.creative.chats")}</option>
        </SelectField>
        <div className={styles.formGrid}>
          <TextField label={t("intel.creative.expMinPosts")} type="number" inputMode="numeric" min={3} max={50} value={minPosts} onChange={(e) => setMinPosts(e.target.value)} />
          <TextField label={t("intel.creative.expMaxDays")} type="number" inputMode="numeric" min={7} max={90} value={maxDays} onChange={(e) => setMaxDays(e.target.value)} />
        </div>
        <p className={styles.muted} style={{ margin: 0 }}>
          {t("intel.creative.expHowTo")}
        </p>
      </form>
    </Drawer>
  );
}
