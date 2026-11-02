"use client";

import { isApiError, type ProductDetail, type ProductStatus, type PublishProblem } from "@commerce-os/api-client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useId, useMemo, useState, type ReactNode, type TextareaHTMLAttributes } from "react";
import { LimitActions } from "@/components/commerce/UsageMeter";
import { PermissionDenied, QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/Drawer";
import { SelectField, TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { InlineAlert, RequestId, Skeleton, useToast } from "@/components/ui/misc";
import { errorMessage, fieldErrorMessages } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery, useIdempotencyKey } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { normalizeSku } from "@/lib/catalog/codes";
import {
  buildCreateBody,
  diffProduct,
  diffVariants,
  emptyForm,
  formFromDetail,
  sameForm,
  validateForm,
  type ProductForm,
} from "@/lib/catalog/editor";
import { parseProblems } from "@/lib/catalog/status";
import { useUnsavedChangesGuard } from "@/lib/navigationGuard";
import { parseLimitOptions } from "@/lib/usage";
import { AddVariantDrawer } from "./AddVariantDrawer";
import { AttributesSection } from "./AttributesSection";
import { CategoriesDrawer, categoryOptionLabel } from "./CategoriesDrawer";
import { ChipInput } from "./ChipInput";
import { CollectionsPicker } from "./CollectionsPicker";
import { ListingsPanel } from "./ListingsPanel";
import { PublishChecklist, StatusControl } from "./StatusControl";
import { VariantGrid } from "./VariantGrid";
import styles from "./products.module.css";

/** Backend error code → grid cell for a failed variant PATCH. */
const VARIANT_ERROR_FIELD: Record<string, "price" | "compareAt" | "sku" | "barcode"> = {
  invalid_barcode: "barcode",
  invalid_compare_at: "compareAt",
  sku_or_barcode_taken: "sku",
  invalid_sku: "sku",
  price_required: "price",
  invalid_amount: "price",
};

/** Backend error code → product field. */
const PRODUCT_ERROR_FIELD: Record<string, string> = {
  handle_taken: "handle",
  invalid_handle: "handle",
  title_required: "title",
  category_not_found: "category_id",
  too_many_tags: "tags",
};

function TextArea({ label, id, ...rest }: { label: string } & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const auto = useId();
  const fieldId = id ?? auto;
  return (
    <div>
      <label htmlFor={fieldId} className={styles.fieldLabel}>
        {label}
      </label>
      <textarea id={fieldId} className={styles.textarea} {...rest} />
    </div>
  );
}

function Section({ id, title, hint, children }: { id: string; title: string; hint?: string; children: ReactNode }) {
  return (
    <section id={id} className={styles.section} aria-labelledby={`${id}-heading`} tabIndex={-1}>
      <h2 id={`${id}-heading`}>{title}</h2>
      {hint ? <p className={styles.sectionHint}>{hint}</p> : null}
      {children}
    </section>
  );
}

/** Keep the user's unsaved values, but take the server's word for variants that were archived. */
function reconcile(form: ProductForm, saved: ProductForm): ProductForm {
  const savedByKey = new Map(saved.variants.map((v) => [v.key, v]));
  return {
    ...form,
    variants: form.variants.map((v) => {
      const s = savedByKey.get(v.key);
      return s && s.status === "archived" ? s : v;
    }),
  };
}

export function EditorForm({ initial }: { initial: ProductDetail | null }) {
  const mode = initial ? "edit" : "create";
  const { t, locale } = useI18n();
  const { api, can } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const canWrite = can("catalog.write");
  const canPublish = can("catalog.publish");

  const [server, setServer] = useState<ProductDetail | null>(initial);
  const [base, setBase] = useState<ProductForm>(() => (initial ? formFromDetail(initial) : emptyForm()));
  const [form, setFormState] = useState<ProductForm>(base);
  const setForm = useCallback((u: (f: ProductForm) => ProductForm) => setFormState(u), []);
  const [attempted, setAttempted] = useState(false);
  const [serverFieldErrors, setServerFieldErrors] = useState<Record<string, string>>({});
  const [bannerError, setBannerError] = useState<unknown>(null);
  const [limitError, setLimitError] = useState<unknown>(null);
  const [conflict, setConflict] = useState(false);
  const [reloading, setReloading] = useState(false);
  const [problems, setProblems] = useState<PublishProblem[]>([]);
  const [partial, setPartial] = useState(false);
  const [saving, setSaving] = useState(false);
  const [statusPending, setStatusPending] = useState<ProductStatus | null>(null);
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [categoriesOpen, setCategoriesOpen] = useState(false);
  const [addVariantOpen, setAddVariantOpen] = useState(false);
  const categories = useApiQuery((a) => a.catalog.categories());
  const { keyFor, reset: resetKey } = useIdempotencyKey();

  const dirty = !sameForm(base, form);
  useUnsavedChangesGuard(dirty && !saving, t("products.editor.leaveConfirm"));

  const clientErrors = useMemo(() => (attempted ? validateForm(form, mode) : {}), [attempted, form, mode]);
  const errorText = useCallback(
    (key: string): string | undefined => {
      const kind = clientErrors[key];
      if (kind) return t.dynamic(`products.editor.err.${kind}`) ?? t("errors.field.invalid");
      return serverFieldErrors[key];
    },
    [clientErrors, serverFieldErrors, t],
  );
  const errorCount = Object.keys(clientErrors).length + Object.keys(serverFieldErrors).length;

  // Once AI suggestions are confirmed, drop that item from a shown publish checklist.
  useEffect(() => {
    if (server && !server.attributes.some((a) => !a.confirmed)) {
      setProblems((p) => p.filter((x) => x !== "unconfirmed_ai_attributes"));
    }
  }, [server]);

  const set = <K extends keyof ProductForm>(k: K, v: ProductForm[K]) => setFormState((f) => ({ ...f, [k]: v }));

  const adopt = (d: ProductDetail) => {
    const b = formFromDetail(d);
    setServer(d);
    setBase(b);
    setFormState(b);
    setAttempted(false);
    setServerFieldErrors({});
  };

  const focusFirstInvalid = () =>
    requestAnimationFrame(() => (document.querySelector('[aria-invalid="true"]') as HTMLElement | null)?.focus());

  const mapProductError = (e: unknown): boolean => {
    if (!isApiError(e)) return false;
    if (e.code === "usage_limit_reached") {
      setLimitError(e);
      return true;
    }
    if (e.code === "validation_error") {
      const mapped = fieldErrorMessages(t, e.fieldErrors());
      if (Object.keys(mapped).length) {
        setServerFieldErrors(mapped);
        return true;
      }
    }
    const field = PRODUCT_ERROR_FIELD[e.code];
    if (field) {
      setServerFieldErrors({ [field]: errorMessage(t, e) });
      return true;
    }
    if (e.code === "sku_taken" && typeof e.details.sku === "string") {
      const row = form.variants.find((v) => normalizeSku(v.sku) === e.details.sku);
      if (row) {
        setServerFieldErrors({ [`variants.${row.key}.sku`]: errorMessage(t, e) });
        return true;
      }
    }
    return false;
  };

  const save = async () => {
    setAttempted(true);
    setBannerError(null);
    setLimitError(null);
    setPartial(false);
    setServerFieldErrors({});
    if (Object.keys(validateForm(form, mode)).length) {
      focusFirstInvalid();
      return;
    }
    setSaving(true);
    try {
      if (mode === "create") {
        const body = buildCreateBody(form);
        try {
          const created = await api.catalog.createProduct(body, { idempotencyKey: keyFor(body) });
          resetKey();
          setBase(form); // clean before navigating so the unsaved-changes guard stays quiet
          toast(t("products.editor.created"));
          router.replace(`/products/${created.id}`);
        } catch (e) {
          if (!mapProductError(e)) setBannerError(e);
          else focusFirstInvalid();
        }
        return;
      }

      const current = server!;
      let latest = current;
      try {
        // Always send `version`: an empty patch still checks for concurrent edits before variant changes.
        latest = await api.catalog.updateProduct(current.id, current.version, diffProduct(base, form));
      } catch (e) {
        if (isApiError(e) && e.code === "version_conflict") setConflict(true);
        else if (!mapProductError(e)) setBannerError(e);
        return;
      }

      const { patches, archives } = diffVariants(base, form);
      const rowErrors: Record<string, string> = {};
      let failure: unknown = null;
      const isConflict = (e: unknown) => isApiError(e) && e.code === "version_conflict";
      // Every variant write carries the latest product version; a conflict stops the run.
      for (const p of patches) {
        try {
          latest = await api.catalog.updateVariant(current.id, p.id, p.body, latest.version);
        } catch (e) {
          failure = e;
          if (isConflict(e)) break;
          const field = isApiError(e) ? VARIANT_ERROR_FIELD[e.code] : undefined;
          if (field) rowErrors[`variants.${p.key}.${field}`] = errorMessage(t, e);
        }
      }
      if (!isConflict(failure)) {
        for (const a of archives) {
          try {
            await api.catalog.archiveVariant(current.id, a.id, latest.version);
            latest = await api.catalog.product(current.id); // DELETE returns 204: re-read the new version
          } catch (e) {
            failure = e;
            if (isConflict(e)) break;
          }
        }
      }
      if (isConflict(failure)) setConflict(true);

      const saved = formFromDetail(latest);
      setServer(latest);
      setBase(saved);
      if (!failure) {
        setFormState(saved);
        setAttempted(false);
        toast(t("products.editor.saved"));
      } else {
        setFormState((f) => reconcile(f, saved));
        setPartial(true);
        setServerFieldErrors(rowErrors);
        if (!Object.keys(rowErrors).length && !isConflict(failure)) setBannerError(failure);
        focusFirstInvalid();
      }
    } finally {
      setSaving(false);
    }
  };

  const reloadLatest = async () => {
    if (!server) return;
    setReloading(true);
    try {
      adopt(await api.catalog.product(server.id));
      setConflict(false);
      setPartial(false);
      setBannerError(null);
    } catch (e) {
      setBannerError(e);
    } finally {
      setReloading(false);
    }
  };

  const changeStatus = async (to: ProductStatus) => {
    if (!server) return;
    setStatusPending(to);
    setProblems([]);
    setBannerError(null);
    setLimitError(null);
    try {
      const d = await api.catalog.setStatus(server.id, to, server.version);
      adopt(d);
      toast(t("products.editor.statusChanged", { status: t(`products.status.${d.status}`) }));
    } catch (e) {
      if (isApiError(e) && e.code === "not_publishable") setProblems(parseProblems(e.details));
      else if (isApiError(e) && e.code === "version_conflict") setConflict(true);
      else if (isApiError(e) && e.code === "usage_limit_reached") setLimitError(e);
      else setBannerError(e);
    } finally {
      setStatusPending(null);
      setConfirmArchive(false);
    }
  };

  if (mode === "create" && !canWrite) return <PermissionDenied permission="catalog.write" />;

  const readOnly = !canWrite;
  const heading = form.title.trim() || server?.title || t("products.editor.newTitle");
  const sections = [
    { id: "basics", label: t("products.editor.basics") },
    { id: "variants", label: t("products.editor.variants") },
    { id: "organization", label: t("products.editor.organization") },
    { id: "shipping", label: t("products.editor.shipping") },
    { id: "attributes", label: t("products.editor.attributes") },
    ...(server ? [{ id: "channels", label: t("listings.title") }] : []),
  ];

  return (
    <>
      <header className={styles.editorHeader}>
        <div className={styles.editorTitle}>
          <Link href="/products" className={styles.backLink}>
            <Icon name="chevronRight" style={{ transform: "rotate(180deg)" }} />
            {t("products.editor.back")}
          </Link>
          <h1>{heading}</h1>
        </div>
        <div className={styles.editorActions}>
          {server ? (
            <StatusControl
              status={server.status}
              canPublish={canPublish}
              dirty={dirty}
              pending={statusPending}
              onChange={(to) => (to === "archived" ? setConfirmArchive(true) : void changeStatus(to))}
            />
          ) : null}
          {dirty ? <span className={styles.dirtyNote}>{t("products.editor.unsaved")}</span> : null}
          {dirty && mode === "edit" ? (
            <Button variant="ghost" onClick={() => setFormState(base)}>
              {t("products.editor.discard")}
            </Button>
          ) : null}
          {canWrite ? (
            <Button variant="primary" onClick={save} loading={saving} disabled={mode === "edit" && !dirty}>
              {saving ? t("products.editor.saving") : mode === "create" ? t("products.editor.create") : t("products.editor.save")}
            </Button>
          ) : null}
        </div>
      </header>

      <div className={styles.fields} style={{ marginTop: 0, marginBottom: "var(--space-4)" }}>
        {conflict ? (
          <InlineAlert
            tone="warning"
            title={t("products.editor.conflictTitle")}
            action={
              <Button size="sm" onClick={reloadLatest} loading={reloading}>
                {t("products.editor.reload")}
              </Button>
            }
          >
            {t("products.editor.conflictBody")}
          </InlineAlert>
        ) : null}
        {limitError && isApiError(limitError) ? (
          <InlineAlert tone="warning" title={t("products.editor.planLimitTitle")}>
            <span>{t("products.editor.planLimitBody")}</span>
            <LimitActions
              buyCredits={parseLimitOptions(limitError.details.options).includes("buy_credits")}
              upgrade={parseLimitOptions(limitError.details.options).includes("upgrade")}
            />
            <RequestId id={limitError.requestId} />
          </InlineAlert>
        ) : null}
        <PublishChecklist problems={problems} />
        {bannerError ? (
          <InlineAlert tone="danger">
            {errorMessage(t, bannerError)}
            <RequestId id={isApiError(bannerError) ? bannerError.requestId : null} />
          </InlineAlert>
        ) : null}
        {partial ? <InlineAlert tone="warning">{t("products.editor.partialSave")}</InlineAlert> : null}
        {attempted && errorCount > 0 && !partial ? (
          <InlineAlert tone="danger">{t("products.editor.fixFields", { count: errorCount })}</InlineAlert>
        ) : null}
        {readOnly ? <InlineAlert tone="info" live={false}>{t("products.readOnly")}</InlineAlert> : null}
      </div>

      <div className={styles.editorBody}>
        <nav className={styles.sectionNav} aria-label={t("products.editor.sections")}>
          <ul>
            {sections.map((s) => (
              <li key={s.id}>
                <a href={`#${s.id}`}>{s.label}</a>
              </li>
            ))}
          </ul>
        </nav>

        <fieldset className={styles.sections} disabled={readOnly} style={{ border: 0, margin: 0, padding: 0, minWidth: 0 }}>
          <Section id="basics" title={t("products.editor.basics")}>
            <div className={styles.fields}>
              <TextField
                label={t("products.editor.titleLabel")}
                value={form.title}
                onChange={(e) => set("title", e.target.value)}
                placeholder={t("products.editor.titlePlaceholder")}
                error={errorText("title")}
                maxLength={255}
                required
              />
              <TextField
                label={t("products.editor.handle")}
                value={form.handle}
                onChange={(e) => set("handle", e.target.value.toLowerCase())}
                hint={t("products.editor.handleHint")}
                error={errorText("handle")}
                maxLength={120}
                spellCheck={false}
                autoCapitalize="none"
                mono
              />
              <TextArea label={t("products.editor.description")} value={form.description} onChange={(e) => set("description", e.target.value)} maxLength={20000} />
              <div className={styles.row2}>
                <TextField label={t("products.editor.brand")} value={form.brand} onChange={(e) => set("brand", e.target.value)} maxLength={120} />
                <TextField label={t("products.editor.productType")} value={form.product_type} onChange={(e) => set("product_type", e.target.value)} maxLength={120} />
              </div>
              <fieldset className={styles.nepaliGroup} lang="ne">
                <legend>
                  {t("products.editor.nepali")}
                  <span lang={locale}>{t("products.editor.nepaliHint")}</span>
                </legend>
                <TextField label={t("products.editor.titleNe")} value={form.title_ne} onChange={(e) => set("title_ne", e.target.value)} maxLength={255} />
                <TextArea label={t("products.editor.descriptionNe")} value={form.description_ne} onChange={(e) => set("description_ne", e.target.value)} maxLength={20000} />
              </fieldset>
            </div>
          </Section>

          <Section id="variants" title={t("products.editor.variants")} hint={mode === "create" ? t("products.editor.optionsHint") : undefined}>
            <VariantGrid mode={mode} form={form} setForm={setForm} errorText={errorText} readOnly={readOnly} />
            {server && canWrite ? (
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "var(--space-3)", paddingTop: "var(--space-3)" }}>
                <Button size="sm" onClick={() => setAddVariantOpen(true)} disabled={dirty}>
                  <Icon name="plus" />
                  {t("products.editor.addVariant")}
                </Button>
                {dirty ? <span className={styles.statusHint} style={{ width: "auto", textAlign: "left" }}>{t("products.editor.addVariantSaveFirst")}</span> : null}
              </div>
            ) : null}
          </Section>

          <Section id="organization" title={t("products.editor.organization")}>
            <div className={styles.fields}>
              <div className={styles.row2}>
                <SelectField label={t("products.editor.category")} value={form.category_id} onChange={(e) => set("category_id", e.target.value)} error={errorText("category_id")}>
                  <option value="">{t("products.editor.noCategory")}</option>
                  {categories.state.status === "success"
                    ? categories.state.data.items.map((c) => (
                        <option key={c.id} value={c.id}>
                          {categoryOptionLabel(c, locale)}
                        </option>
                      ))
                    : null}
                </SelectField>
                <div style={{ alignSelf: "end", paddingBottom: 2 }}>
                  <Button size="sm" variant="ghost" onClick={() => setCategoriesOpen(true)}>
                    {t("products.editor.manageCategories")}
                  </Button>
                </div>
              </div>
              <ChipInput
                label={t("products.editor.tags")}
                values={form.tags}
                onChange={(tags) => set("tags", tags)}
                placeholder={t("products.editor.tagsPlaceholder")}
                error={errorText("tags")}
                max={30}
              />
              {server ? (
                <CollectionsPicker
                  productId={server.id}
                  memberOf={server.collection_ids}
                  canWrite={canWrite}
                  onChange={(ids) => setServer((sv) => (sv ? { ...sv, collection_ids: ids } : sv))}
                />
              ) : null}
            </div>
          </Section>

          <Section id="shipping" title={t("products.editor.shipping")} hint={t("products.editor.shippingHint")}>
            <div className={styles.row4}>
              {(["weight", "length", "width", "height"] as const).map((f) => (
                <TextField
                  key={f}
                  label={t(`products.editor.${f}`)}
                  value={form[f]}
                  onChange={(e) => set(f, e.target.value)}
                  inputMode="numeric"
                  error={errorText(f)}
                />
              ))}
            </div>
          </Section>

          <Section id="attributes" title={t("products.editor.attributes")}>
            {server ? (
              <AttributesSection
                product={server}
                canWrite={canWrite}
                onAttributes={(next) => setServer((s) => (s ? { ...s, ...next } : s))}
              />
            ) : (
              <p className={styles.sectionHint}>{t("products.editor.attributesCreate")}</p>
            )}
          </Section>
          {server ? (
            <Section id="channels" title={t("listings.title")} hint={t("listings.hint")}>
              <ListingsPanel product={server} canPublish={canPublish} />
            </Section>
          ) : null}
        </fieldset>
      </div>
      {server ? (
        <AddVariantDrawer
          open={addVariantOpen}
          onOpenChange={setAddVariantOpen}
          product={server}
          onAdded={(d) => {
            adopt(d);
            setAddVariantOpen(false);
            toast(t("products.editor.variantAdded"));
          }}
        />
      ) : null}

      <ConfirmDialog
        open={confirmArchive}
        onOpenChange={setConfirmArchive}
        title={t("products.editor.archiveTitle")}
        body={t("products.editor.archiveBody")}
        confirmLabel={t("products.editor.statusAction.archive")}
        onConfirm={() => void changeStatus("archived")}
        pending={statusPending === "archived"}
        destructive
      />
      <CategoriesDrawer
        open={categoriesOpen}
        onOpenChange={setCategoriesOpen}
        onCreated={(c) => {
          categories.setData((d) => ({ items: [...d.items, c].sort((a, b) => a.path.localeCompare(b.path)) }));
          set("category_id", c.id);
        }}
      />
    </>
  );
}

function EditLoader({ id }: { id: string }) {
  const { t } = useI18n();
  const product = useApiQuery((a) => a.catalog.product(id), [id]);
  if (product.state.status === "loading") {
    return (
      <div role="status" aria-label={t("common.loading")}>
        <div className={styles.fields} style={{ marginTop: 0, marginBottom: "var(--space-6)" }}>
          <Skeleton width={90} />
          <Skeleton width={280} height={22} />
        </div>
        <TableSkeleton columns="1.2fr 1fr 1fr 1fr 1.2fr" rows={4} label={t("common.loading")} />
      </div>
    );
  }
  if (product.state.status === "error") return <QueryError error={product.state.error} onRetry={product.reload} />;
  return <EditorForm key={product.state.data.id} initial={product.state.data} />;
}

export function ProductEditor({ productId }: { productId?: string }) {
  return productId ? <EditLoader id={productId} /> : <EditorForm initial={null} />;
}
