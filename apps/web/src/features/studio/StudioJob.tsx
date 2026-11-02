"use client";

import { isApiError, type ProductCreateInput, type StudioJob, type StudioIssue } from "@commerce-os/api-client";
import { useRouter } from "next/navigation";
import { useCallback, useMemo, useState } from "react";
import { LimitActions } from "@/components/commerce/UsageMeter";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button, ButtonLink } from "@/components/ui/Button";
import { ConfirmDialog, Drawer } from "@/components/ui/Drawer";
import { Checkbox, TextField } from "@/components/ui/Field";
import { InlineAlert, PageHeader, RequestId, SectionHeader, useToast } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { buildCreateBody, emptyForm, newRow, validateForm, type ProductForm } from "@/lib/catalog/editor";
import { cleanOptions, syncRows } from "@/lib/catalog/variants";
import { usePolling } from "@/lib/usePolling";
import { parseLimitOptions } from "@/lib/usage";
import productStyles from "../products/products.module.css";
import { VariantGrid } from "../products/VariantGrid";
import wf from "../shared/workflow.module.css";
import { PhotoFeedback } from "./PhotoTile";

/** Below this, attribute suggestions are not auto-kept by the backend and need a human look. */
export const ATTRIBUTE_CHECK_THRESHOLD = 0.75;
const WORKING = new Set(["queued", "running"]);

export function issueText(t: ReturnType<typeof useI18n>["t"], issue: StudioIssue): string {
  if (issue.kind.startsWith("unsupported_claim:")) {
    const claim = issue.kind.split(":")[1] ?? "other";
    return t("studio.issue.claim", {
      claim: t.dynamic(`studio.claim.${claim}`) ?? t("studio.claim.other"),
      excerpt: issue.excerpt ?? "",
    });
  }
  return t.dynamic(`studio.issue.${issue.kind}`, { field: issue.field }) ?? t("studio.issue.too_long", { field: issue.field });
}

/** Initial review form from the AI draft. Prices are always left blank for the seller. */
export function formFromDraft(job: StudioJob): ProductForm {
  const d = job.draft!;
  const f = emptyForm();
  const bullets = d.bullets_en.filter(Boolean).map((b) => `• ${b}`).join("\n");
  f.title = (job.locale === "ne" ? d.title_ne || d.title_en : d.title_en || d.title_ne) ?? "";
  f.title_ne = d.title_ne ?? "";
  f.description = [d.description_en, bullets].filter(Boolean).join("\n\n");
  f.description_ne = d.description_ne ?? "";
  f.options = cleanOptions(d.suggested_options ?? []).slice(0, 3);
  f.variants = syncRows([], f.options, [], newRow);
  return f;
}

function DraftPhotos({ assetIds }: { assetIds: string[] }) {
  const { api } = useAuth();
  const assets = useApiQuery(() => Promise.all(assetIds.map((id) => api.media.get(id))), [assetIds.join(",")]);
  if (assets.state.status !== "success") return null;
  return (
    <ul className={wf.photoGrid}>
      {assets.state.data.map((a) => (
        <li key={a.id} className={wf.photo}>
          <div className={wf.photoFrame}>
            {a.derivatives.thumb?.url ? (
              // eslint-disable-next-line @next/next/no-img-element -- signed, short-lived URL
              <img src={a.derivatives.thumb.url} alt={a.file_name} />
            ) : null}
          </div>
          <PhotoFeedback asset={a} />
        </li>
      ))}
    </ul>
  );
}

export function CreatePostsDrawer({ jobId, open, onOpenChange }: { jobId: string; open: boolean; onOpenChange: (o: boolean) => void }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const router = useRouter();
  const connections = useApiQuery((a) => a.channels.list());
  const [picked, setPicked] = useState<string[]>([]);
  const action = useAction();
  const postable = connections.state.status === "success" ? connections.state.data.items.filter((c) => c.capabilities.includes("content_publish") && c.status === "connected") : [];

  const create = async () => {
    const r = await action.run(() => api.content.fromStudio({ job_id: jobId, connection_ids: picked }));
    if (r) {
      toast(t("studio.postsCreated", { count: r.items.length }));
      onOpenChange(false);
      router.push("/content");
    }
  };

  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={t("studio.createPostsTitle")}
      description={t("studio.createPostsBody")}
      footer={
        <Button variant="primary" onClick={create} loading={action.pending} disabled={!picked.length}>
          {t("studio.createPosts")}
        </Button>
      }
    >
      <div className={wf.stack}>
        {action.error ? (
          <InlineAlert tone="danger">
            {errorMessage(t, action.error)}
            <RequestId id={isApiError(action.error) ? action.error.requestId : null} />
          </InlineAlert>
        ) : null}
        {connections.state.status === "loading" ? (
          <TableSkeleton columns="1fr" rows={2} label={t("common.loading")} />
        ) : postable.length === 0 ? (
          <div className={wf.stack}>
            <p className={wf.hint}>{t("content.new.noChannels")}</p>
            <div>
              <ButtonLink href="/settings/channels" size="sm">
                {t("listings.connectLink")}
              </ButtonLink>
            </div>
          </div>
        ) : (
          <fieldset style={{ border: 0, margin: 0, padding: 0 }} className={wf.checklist}>
            <legend className={productStyles.fieldLabel}>{t("content.new.channels")}</legend>
            {postable.map((c) => (
              <Checkbox
                key={c.id}
                label={c.display_name}
                checked={picked.includes(c.id)}
                onChange={(e) => setPicked((p) => (e.target.checked ? [...p, c.id] : p.filter((x) => x !== c.id)))}
              />
            ))}
          </fieldset>
        )}
      </div>
    </Drawer>
  );
}

function Review({ job, onDiscarded }: { job: StudioJob; onDiscarded: () => void }) {
  const { t, percent } = useI18n();
  const { api, can } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const draft = job.draft!;
  const [form, setFormState] = useState<ProductForm>(() => formFromDraft(job));
  const setForm = useCallback((u: (f: ProductForm) => ProductForm) => setFormState(u), []);
  const [categoryText, setCategoryText] = useState((draft.category?.path ?? []).join(" > "));
  const [kept, setKept] = useState<Set<string>>(() => new Set(draft.attributes.filter((a) => a.confidence >= ATTRIBUTE_CHECK_THRESHOLD).map((a) => a.key)));
  const [ticked, setTicked] = useState<Set<number>>(new Set());
  const [attempted, setAttempted] = useState(false);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const [postsOpen, setPostsOpen] = useState(false);
  const apply = useAction();
  const discard = useAction();

  const errors = useMemo(() => (attempted ? validateForm(form, "create") : {}), [attempted, form]);
  const errorText = (key: string) => (errors[key] ? (t.dynamic(`products.editor.err.${errors[key]}`) ?? t("errors.field.invalid")) : undefined);
  const needs = draft.needs_seller_input ?? [];
  const unticked = needs.length - ticked.size;

  const save = async () => {
    setAttempted(true);
    if (Object.keys(validateForm(form, "create")).length || unticked > 0) return;
    const product: ProductCreateInput = {
      ...buildCreateBody(form),
      seo_title: draft.seo?.title || undefined,
      seo_description: draft.seo?.description || undefined,
    };
    const path = categoryText
      .split(">")
      .map((s) => s.trim())
      .filter(Boolean)
      .slice(0, 6);
    const d = await apply.run(() => api.studio.apply(job.id, { product, category_path: path.length ? path : null, accepted_attribute_keys: [...kept] }));
    if (d) {
      toast(t("studio.applied"));
      router.push(`/products/${d.id}`);
    }
  };

  const doDiscard = async () => {
    const ok = await discard.run(async () => {
      await api.studio.discard(job.id);
      return true;
    });
    if (ok) {
      setConfirmDiscard(false);
      toast(t("studio.discardedToast"));
      onDiscarded();
    }
  };

  const applyErr = apply.error;
  const limited = isApiError(applyErr) && applyErr.code === "usage_limit_reached";

  return (
    <>
      <PageHeader
        title={t("studio.review")}
        subtitle={t("studio.reviewHint")}
        actions={job.confidence !== null ? <span className={wf.aiTag}>{t("studio.confidence", { percent: percent(job.confidence) })}</span> : null}
      />
      <div className={wf.split}>
        <div className={wf.stack}>
          {limited && isApiError(applyErr) ? (
            <InlineAlert tone="warning" title={t("products.editor.planLimitTitle")}>
              <LimitActions buyCredits={parseLimitOptions(applyErr.details.options).includes("buy_credits")} upgrade />
            </InlineAlert>
          ) : applyErr ? (
            <InlineAlert tone="danger">
              {errorMessage(t, applyErr)}
              <RequestId id={isApiError(applyErr) ? applyErr.requestId : null} />
            </InlineAlert>
          ) : null}
          {job.issues.length ? (
            <InlineAlert tone="warning" title={t("studio.issuesTitle")}>
              <ul className={wf.issueList} data-testid="studio-issues">
                {job.issues.map((i, n) => (
                  <li key={n}>{issueText(t, i)}</li>
                ))}
              </ul>
            </InlineAlert>
          ) : null}

          <DraftPhotos assetIds={job.asset_ids} />

          <div className={wf.aiRule}>
            <div className={productStyles.fields} style={{ marginTop: 0 }}>
              <TextField
                label={t("products.editor.titleLabel")}
                value={form.title}
                onChange={(e) => setFormState((f) => ({ ...f, title: e.target.value }))}
                error={errorText("title")}
                maxLength={255}
              />
              <div>
                <label htmlFor="studio-desc" className={productStyles.fieldLabel}>
                  {t("products.editor.description")}
                </label>
                <textarea
                  id="studio-desc"
                  className={productStyles.textarea}
                  value={form.description}
                  onChange={(e) => setFormState((f) => ({ ...f, description: e.target.value }))}
                  style={{ minHeight: 140 }}
                />
              </div>
              <fieldset className={productStyles.nepaliGroup} lang="ne">
                <legend>{t("products.editor.nepali")}</legend>
                <TextField label={t("products.editor.titleNe")} value={form.title_ne} onChange={(e) => setFormState((f) => ({ ...f, title_ne: e.target.value }))} />
                <div>
                  <label htmlFor="studio-desc-ne" className={productStyles.fieldLabel}>
                    {t("products.editor.descriptionNe")}
                  </label>
                  <textarea
                    id="studio-desc-ne"
                    className={productStyles.textarea}
                    value={form.description_ne}
                    onChange={(e) => setFormState((f) => ({ ...f, description_ne: e.target.value }))}
                  />
                </div>
              </fieldset>
              <div>
                <TextField label={t("studio.category")} value={categoryText} onChange={(e) => setCategoryText(e.target.value)} hint={t("studio.categoryHint")} />
                {draft.category && draft.category.confidence < ATTRIBUTE_CHECK_THRESHOLD ? <span className={wf.aiTag}>{t("studio.pleaseCheck")}</span> : null}
              </div>
            </div>
          </div>

          <SectionHeader title={t("studio.pricesTitle")} />
          <p className={wf.hint}>{t("studio.pricesHint")}</p>
          <VariantGrid mode="create" form={form} setForm={setForm} errorText={errorText} readOnly={false} />

          {draft.attributes.length ? (
            <>
              <SectionHeader title={t("studio.attributes")} />
              <p className={wf.hint}>{t("studio.attrHint", { percent: percent(ATTRIBUTE_CHECK_THRESHOLD) })}</p>
              <div className={table.wrap}>
                <table className={[table.table, table.dense].join(" ")} data-testid="studio-attributes">
                  <thead>
                    <tr>
                      <th scope="col">{t("studio.attrKeep")}</th>
                      <th scope="col">{t("studio.colDetail")}</th>
                      <th scope="col">{t("studio.colValue")}</th>
                      <th scope="col">{t("studio.colConfidence")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {draft.attributes.map((a) => {
                      const auto = a.confidence >= ATTRIBUTE_CHECK_THRESHOLD;
                      return (
                        <tr key={a.key} data-check={!auto || undefined}>
                          <td>
                            <input
                              type="checkbox"
                              aria-label={`${t("studio.attrKeep")}: ${a.key}`}
                              checked={kept.has(a.key)}
                              disabled={auto}
                              onChange={(e) =>
                                setKept((s) => {
                                  const n = new Set(s);
                                  if (e.target.checked) n.add(a.key);
                                  else n.delete(a.key);
                                  return n;
                                })
                              }
                            />
                          </td>
                          <td className={table.mono}>{a.key}</td>
                          <td>{a.value}</td>
                          <td>{auto ? percent(a.confidence) : <span className={wf.aiTag}>{`${t("studio.pleaseCheck")} · ${percent(a.confidence)}`}</span>}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          ) : null}
        </div>

        <aside className={wf.aside}>
          {needs.length ? (
            <div>
              <h3>{t("studio.needsInputTitle")}</h3>
              <p className={wf.hint} style={{ marginBottom: "var(--space-2)" }}>
                {t("studio.needsInputHint")}
              </p>
              <div className={wf.checklist} data-testid="needs-input">
                {needs.map((n, i) => (
                  <Checkbox
                    key={i}
                    label={n}
                    checked={ticked.has(i)}
                    onChange={(e) =>
                      setTicked((s) => {
                        const x = new Set(s);
                        if (e.target.checked) x.add(i);
                        else x.delete(i);
                        return x;
                      })
                    }
                  />
                ))}
              </div>
              {attempted && unticked > 0 ? (
                <p className={productStyles.cellError} role="alert" style={{ maxWidth: "none" }}>
                  {t("studio.needsInputHint")}
                </p>
              ) : null}
            </div>
          ) : null}
          {draft.captions?.instagram || draft.captions?.facebook ? (
            <div className={wf.stack}>
              <div>
                <h3>{t("studio.captions")}</h3>
                <p className={wf.hint}>{t("studio.captionsHint")}</p>
              </div>
              {(["instagram", "facebook", "tiktok"] as const).map((k) =>
                draft.captions[k] ? (
                  <div key={k}>
                    <span className={productStyles.fieldLabel} style={{ textTransform: "capitalize" }}>
                      {k}
                    </span>
                    <p className={wf.caption}>{draft.captions[k]}</p>
                  </div>
                ) : null,
              )}
            </div>
          ) : null}
          {draft.hashtags?.length ? (
            <div>
              <h3>{t("studio.hashtags")}</h3>
              <p className={wf.hint}>{draft.hashtags.map((h) => (h.startsWith("#") ? h : `#${h}`)).join(" ")}</p>
            </div>
          ) : null}
        </aside>
      </div>

      <div className={wf.footerBar}>
        {can("content.write") ? <Button onClick={() => setPostsOpen(true)}>{t("studio.createPosts")}</Button> : null}
        <Button variant="ghost" onClick={() => setConfirmDiscard(true)}>
          {t("studio.discard")}
        </Button>
        <Button variant="primary" onClick={save} loading={apply.pending}>
          {apply.pending ? t("studio.applying") : t("studio.apply")}
        </Button>
      </div>
      <ConfirmDialog
        open={confirmDiscard}
        onOpenChange={setConfirmDiscard}
        title={t("studio.discardTitle")}
        body={t("studio.discardBody")}
        confirmLabel={t("studio.discard")}
        onConfirm={doDiscard}
        pending={discard.pending}
        destructive
      />
      <CreatePostsDrawer jobId={job.id} open={postsOpen} onOpenChange={setPostsOpen} />
    </>
  );
}

export function StudioJobView({ id }: { id: string }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const router = useRouter();
  const poll = usePolling(() => api.studio.job(id), { key: id, isDone: (j) => !WORKING.has(j.status) });
  const retry = useAction();
  const job = poll.data;

  if (!job) {
    if (poll.error) return <QueryError error={poll.error} onRetry={poll.retry} />;
    return <TableSkeleton columns="1fr 1fr" rows={4} label={t("common.loading")} />;
  }
  if (WORKING.has(job.status)) {
    return (
      <>
        <PageHeader title={t("studio.title")} />
        <div className={wf.working} aria-live="polite" data-testid="studio-working">
          <strong>{t(job.status === "queued" ? "studio.job.queued" : "studio.job.running")}</strong>
          <div className={wf.track} aria-hidden="true">
            <span />
          </div>
          <p className={wf.hint}>{t("studio.job.runningHint")}</p>
        </div>
      </>
    );
  }
  if (job.status === "failed") {
    return (
      <>
        <PageHeader title={t("studio.title")} />
        <div className={wf.stack} style={{ maxWidth: 560 }}>
          <InlineAlert tone="danger" title={t("studio.job.failed")}>
            {job.error_code ? (t.dynamic(`errors.${job.error_code}`) ?? t("errors.dependency_unavailable")) : null}
          </InlineAlert>
          {retry.error ? <InlineAlert tone="danger">{errorMessage(t, retry.error)}</InlineAlert> : null}
          <div className={wf.rowActions} style={{ justifyContent: "flex-start" }}>
            <Button
              variant="primary"
              loading={retry.pending}
              onClick={async () => {
                const j = await retry.run(() => api.studio.retry(id));
                if (j) {
                  poll.setData(j);
                  poll.retry();
                }
              }}
            >
              {t("studio.retry")}
            </Button>
            <ButtonLink href="/products">{t("studio.backToProducts")}</ButtonLink>
          </div>
        </div>
      </>
    );
  }
  if (job.status === "applied" || job.status === "discarded" || !job.draft) {
    return (
      <>
        <PageHeader title={t("studio.title")} />
        <EmptyState
          title={t(job.status === "applied" ? "studio.job.applied" : "studio.job.discarded")}
          actions={
            job.product_id ? (
              <ButtonLink href={`/products/${job.product_id}`} variant="primary">
                {t("studio.openProduct")}
              </ButtonLink>
            ) : (
              <ButtonLink href="/products">{t("studio.backToProducts")}</ButtonLink>
            )
          }
        />
      </>
    );
  }
  return <Review job={job} onDiscarded={() => router.push("/products")} />;
}
