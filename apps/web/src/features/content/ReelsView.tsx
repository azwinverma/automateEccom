"use client";

import { isApiError, type ReelAspect, type VideoJob } from "@commerce-os/api-client";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { LimitActions } from "@/components/commerce/UsageMeter";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { Checkbox, SelectField, TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, InlineAlert, PageHeader, RequestId, type Tone } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery, useIdempotencyKey } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { usePolling } from "@/lib/usePolling";
import { parseLimitOptions } from "@/lib/usage";
import productStyles from "../products/products.module.css";
import wf from "../shared/workflow.module.css";
import { ReelBestSettings, useCreativeSuggestions } from "../intelligence/CreativeSuggest";
import { paceFor } from "../intelligence/creativeLabels";
import { ContentTabs } from "./ContentTabs";
import { MediaPicker } from "./MediaPicker";

export const VIDEO_TERMINAL = new Set(["ready", "failed", "cancelled"]);
const ASPECTS: { value: ReelAspect; key: "a9x16" | "a1x1" | "a4x5" | "a16x9" }[] = [
  { value: "9:16", key: "a9x16" },
  { value: "1:1", key: "a1x1" },
  { value: "4:5", key: "a4x5" },
  { value: "16:9", key: "a16x9" },
];
const TONE: Record<string, Tone> = { ready: "success", failed: "danger", cancelled: "neutral", queued: "info", generating: "automated", post_processing: "automated" };

/** Live status of one reel; signed video URLs are short-lived, so a playback error refetches. */
export function ReelProgress({ initial, onSettled }: { initial: VideoJob; onSettled?: () => void }) {
  const { t, number } = useI18n();
  const { api } = useAuth();
  const poll = usePolling(() => api.media.video(initial.id), { key: initial.id, initial, isDone: (j) => VIDEO_TERMINAL.has(j.status) });
  const job = poll.data ?? initial;
  const done = VIDEO_TERMINAL.has(job.status);
  useEffect(() => {
    if (done) onSettled?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done]);
  const video = job.output?.derivatives.video?.url ?? null;
  const poster = job.output?.derivatives.poster?.url ?? undefined;

  if (!done) {
    return (
      <div className={wf.working} aria-live="polite" data-testid="reel-progress">
        <strong>{t("reels.making")}</strong>
        <span className={wf.hint}>{t(`reels.status.${job.status}`)}</span>
        <div className={wf.track} aria-hidden="true">
          <span />
        </div>
        <p className={wf.hint}>{t("reels.makingHint")}</p>
      </div>
    );
  }
  if (job.status !== "ready") {
    return (
      <InlineAlert tone={job.status === "failed" ? "danger" : "info"}>
        {job.status === "failed"
          ? t("reels.failed", { reason: job.error_code ? (t.dynamic(`errors.${job.error_code}`) ?? job.error_code) : "" })
          : t("reels.status.cancelled")}
      </InlineAlert>
    );
  }
  return (
    <div className={wf.stack} data-testid="reel-ready">
      {video ? (
        <video
          key={video}
          src={video}
          poster={poster}
          controls
          playsInline
          aria-label={t("reels.videoLabel")}
          onError={() => poll.refresh()}
          style={{ width: "100%", maxHeight: 520, background: "#000", borderRadius: "var(--radius-md)" }}
        />
      ) : null}
      <div className={wf.rowActions} style={{ justifyContent: "flex-start", alignItems: "center" }}>
        {video ? (
          <a href={video} download className={productStyles.titleLink}>
            <Icon name="download" /> {t("reels.download")}
          </a>
        ) : null}
        {job.duration_s ? <span className={wf.hint}>{t("reels.seconds", { seconds: number(job.duration_s, { maximumFractionDigits: 1 }) })}</span> : null}
        {job.credits_charged ? <span className={wf.hint}>{t("reels.credits", { count: number(job.credits_charged) })}</span> : null}
      </div>
    </div>
  );
}

function MakeReelDrawer({ open, onOpenChange, onCreated }: { open: boolean; onOpenChange: (o: boolean) => void; onCreated: () => void }) {
  const { t, locale } = useI18n();
  const { api } = useAuth();
  const [assets, setAssets] = useState<string[]>([]);
  const [aspect, setAspect] = useState<ReelAspect>("9:16");
  const [reelLocale, setReelLocale] = useState<"en" | "ne">(locale);
  const [headline, setHeadline] = useState("");
  const [cta, setCta] = useState("");
  const [productId, setProductId] = useState("");
  const [showPrice, setShowPrice] = useState(false);
  const [pace, setPace] = useState(2.5);
  // CGN-004: set when the seller applied the genome's settings; any manual change clears it.
  const [genomeVersion, setGenomeVersion] = useState<number | null>(null);
  const suggestions = useCreativeSuggestions(open);
  const [formErr, setFormErr] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [pending, setPending] = useState(false);
  const [job, setJob] = useState<VideoJob | null>(null);
  const { keyFor, reset } = useIdempotencyKey();
  const products = useApiQuery((a) => (open ? a.catalog.products({ limit: 200 }) : Promise.resolve({ items: [], next_cursor: null })), [open]);

  useEffect(() => {
    if (!open) return;
    setAssets([]);
    setHeadline("");
    setCta("");
    setProductId("");
    setShowPrice(false);
    setGenomeVersion(null);
    setFormErr(null);
    setError(null);
    setJob(null);
    reset();
  }, [open, reset]);

  const applyBest = () => {
    const r = suggestions?.reel;
    if (!r || !suggestions?.genome_version) return;
    if (r.target_seconds) setPace(paceFor(r.target_seconds, assets.length));
    if (r.show_price !== undefined) setShowPrice(r.show_price);
    setGenomeVersion(suggestions.genome_version);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!assets.length) return setFormErr(t("reels.pickPhotos"));
    if (showPrice && !productId) return setFormErr(t("errors.product_required_for_price"));
    setFormErr(null);
    setError(null);
    setPending(true);
    const body = {
      asset_ids: assets,
      aspect,
      locale: reelLocale,
      headline: headline.trim() || null,
      cta: cta.trim() || null,
      product_id: productId || null,
      show_price: showPrice,
      seconds_per_slide: pace,
      ...(genomeVersion ? { genome_version: genomeVersion } : {}),
    };
    try {
      setJob(await api.media.createAutoReel(body, { idempotencyKey: keyFor(body) }));
      onCreated();
    } catch (err) {
      setError(err);
    } finally {
      setPending(false);
    }
  };

  const limited = isApiError(error) && (error.code === "usage_limit_reached" || error.code === "feature_not_in_plan");
  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={t("reels.make")}
      wide
      footer={
        job ? (
          <Button onClick={() => onOpenChange(false)}>{t("common.close")}</Button>
        ) : (
          <Button variant="primary" type="submit" form="reel-form" loading={pending}>
            {pending ? t("reels.submitting") : t("reels.submit")}
          </Button>
        )
      }
    >
      {job ? (
        <ReelProgress initial={job} onSettled={onCreated} />
      ) : (
        <form id="reel-form" className={wf.stack} onSubmit={submit} noValidate>
          {limited && isApiError(error) ? (
            <InlineAlert tone="warning" title={errorMessage(t, error)}>
              <LimitActions
                buyCredits={parseLimitOptions(error.details.options).includes("buy_credits")}
                upgrade={error.code === "feature_not_in_plan" || parseLimitOptions(error.details.options).includes("upgrade")}
              />
              <RequestId id={error.requestId} />
            </InlineAlert>
          ) : error ? (
            <InlineAlert tone={isApiError(error) && error.code === "text_shaping_unavailable" ? "warning" : "danger"}>
              {errorMessage(t, error)}
              <RequestId id={isApiError(error) ? error.requestId : null} />
            </InlineAlert>
          ) : null}
          {formErr ? (
            <p className={productStyles.cellError} role="alert" style={{ maxWidth: "none" }}>
              {formErr}
            </p>
          ) : null}
          <div>
            <span className={productStyles.fieldLabel}>{t("reels.photos")}</span>
            <MediaPicker value={assets} onChange={setAssets} max={10} />
          </div>
          <ReelBestSettings suggestions={suggestions} applied={genomeVersion !== null} onApply={applyBest} />
          <div className={productStyles.row2}>
            <SelectField label={t("reels.aspect")} value={aspect} onChange={(e) => setAspect(e.target.value as ReelAspect)}>
              {ASPECTS.map((a) => (
                <option key={a.value} value={a.value}>
                  {t(`reels.aspectLabel.${a.key}`)}
                </option>
              ))}
            </SelectField>
            <SelectField label={t("reels.language")} value={reelLocale} onChange={(e) => setReelLocale(e.target.value as "en" | "ne")}>
              <option value="ne">{t("language.ne")}</option>
              <option value="en">{t("language.en")}</option>
            </SelectField>
          </div>
          <TextField label={t("reels.headline")} optionalLabel={t("common.optional")} value={headline} onChange={(e) => setHeadline(e.target.value)} maxLength={80} lang={reelLocale} />
          <TextField
            label={t("reels.cta")}
            optionalLabel={t("common.optional")}
            value={cta}
            onChange={(e) => setCta(e.target.value)}
            maxLength={60}
            placeholder={t("reels.ctaPlaceholder")}
            lang={reelLocale}
          />
          <SelectField label={t("reels.product")} value={productId} onChange={(e) => setProductId(e.target.value)}>
            <option value="">{t("reels.noProduct")}</option>
            {products.state.status === "success"
              ? products.state.data.items.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))
              : null}
          </SelectField>
          <div>
            <Checkbox
              label={t("reels.showPrice")}
              checked={showPrice}
              onChange={(e) => {
                setShowPrice(e.target.checked);
                setGenomeVersion(null);
              }}
            />
            <p className={wf.hint} style={{ marginTop: "var(--space-1)" }}>
              {t("reels.priceNote")}
            </p>
          </div>
          <div>
            <label htmlFor="reel-pace" className={productStyles.fieldLabel}>
              {t("reels.pace", { seconds: pace })}
            </label>
            <input id="reel-pace" type="range" min={1.5} max={6} step={0.5} value={pace} onChange={(e) => {
                setPace(Number(e.target.value));
                setGenomeVersion(null);
              }}
              style={{ width: "100%" }}
            />
          </div>
        </form>
      )}
    </Drawer>
  );
}

export function ReelsView() {
  const { t, relative, number } = useI18n();
  const { api, can } = useAuth();
  const params = useSearchParams();
  const router = useRouter();
  const [open, setOpen] = useState(params.get("new") === "1");
  const [round, setRound] = useState(0);
  const [viewing, setViewing] = useState<VideoJob | null>(null);
  const list = usePolling(() => api.media.videos(), {
    key: `videos:${round}`,
    isDone: (r) => r.items.every((j) => VIDEO_TERMINAL.has(j.status)),
    delay: () => 3000,
  });

  return (
    <>
      <PageHeader
        title={t("content.title")}
        subtitle={t("reels.subtitle")}
        actions={
          can("media.write") ? (
            <Button variant="primary" onClick={() => setOpen(true)}>
              <Icon name="plus" />
              {t("reels.make")}
            </Button>
          ) : null
        }
      />
      <ContentTabs />
      {!list.data ? (
        list.error ? (
          <QueryError error={list.error} onRetry={list.retry} />
        ) : (
          <TableSkeleton columns="2fr 1fr 0.6fr 1fr" rows={3} label={t("common.loading")} />
        )
      ) : list.data.items.length === 0 ? (
        <EmptyState
          title={t("reels.empty")}
          actions={can("media.write") ? <Button onClick={() => setOpen(true)}>{t("reels.make")}</Button> : null}
        />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} data-testid="reels">
            <thead>
              <tr>
                <th scope="col">{t("reels.colReel")}</th>
                <th scope="col">{t("reels.colStatus")}</th>
                <th scope="col" className={[table.num, table.hideSm].join(" ")}>
                  {t("reels.colLength")}
                </th>
                <th scope="col" className={table.hideSm}>
                  {t("reels.colCreated")}
                </th>
              </tr>
            </thead>
            <tbody>
              {list.data.items.map((j) => (
                <tr key={j.id}>
                  <td>
                    <button type="button" className={productStyles.titleLink} style={{ all: "unset", cursor: "pointer", fontWeight: 500 }} onClick={() => setViewing(j)}>
                      {j.headline || t("reels.untitled", { count: j.asset_ids.length })}
                    </button>
                    <div className={table.muted} style={{ fontSize: "var(--font-size-xs)" }}>
                      {j.aspect}
                    </div>
                  </td>
                  <td>
                    <Badge tone={TONE[j.status] ?? "neutral"}>{t(`reels.status.${j.status}`)}</Badge>
                  </td>
                  <td className={[table.num, table.hideSm].join(" ")}>{j.duration_s ? t("reels.seconds", { seconds: number(j.duration_s, { maximumFractionDigits: 1 }) }) : t("common.none")}</td>
                  <td className={[table.muted, table.hideSm].join(" ")}>{relative(j.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <MakeReelDrawer
        open={open}
        onOpenChange={(o) => {
          setOpen(o);
          if (!o && params.get("new")) router.replace("/content/reels");
        }}
        onCreated={() => setRound((r) => r + 1)}
      />
      <Drawer open={viewing !== null} onOpenChange={(o) => !o && setViewing(null)} title={viewing?.headline || t("reels.title")} wide>
        {viewing ? <ReelProgress initial={viewing} onSettled={() => setRound((r) => r + 1)} /> : null}
      </Drawer>
    </>
  );
}
