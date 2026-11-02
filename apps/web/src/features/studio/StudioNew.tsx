"use client";

import { isApiError } from "@commerce-os/api-client";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { LimitActions } from "@/components/commerce/UsageMeter";
import { PermissionDenied } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { SelectField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { InlineAlert, PageHeader, RequestId, SectionHeader } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useIdempotencyKey } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ALLOWED_PHOTO_TYPES, initialUpload, runUpload, uploadReducer, UPLOAD_TERMINAL, type UploadState } from "@/lib/media/upload";
import { parseLimitOptions } from "@/lib/usage";
import productStyles from "../products/products.module.css";
import wf from "../shared/workflow.module.css";
import { PhotoTile } from "./PhotoTile";

export const MAX_STUDIO_PHOTOS = 6;

interface Item {
  id: string;
  name: string;
  preview: string | null;
  state: UploadState;
}

export function StudioNew() {
  const { t, locale } = useI18n();
  const { api, can } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<Item[]>([]);
  const [notes, setNotes] = useState("");
  const [draftLocale, setDraftLocale] = useState<"en" | "ne">(locale);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const { keyFor } = useIdempotencyKey();
  const inputRef = useRef<HTMLInputElement>(null);
  const alive = useRef({ aborted: false });

  useEffect(() => {
    const signal = alive.current;
    return () => {
      signal.aborted = true;
    };
  }, []);
  useEffect(
    () => () => items.forEach((i) => i.preview && URL.revokeObjectURL(i.preview)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  if (!can("ai.use") || !can("media.write")) return <PermissionDenied permission="ai.use" />;

  const addFiles = (files: FileList | null) => {
    if (!files) return;
    const room = MAX_STUDIO_PHOTOS - items.length;
    for (const file of Array.from(files).slice(0, Math.max(0, room))) {
      const id = crypto.randomUUID();
      const preview = file.type.startsWith("image/") && !/hei[cf]/.test(file.type) ? URL.createObjectURL(file) : null;
      setItems((list) => [...list, { id, name: file.name, preview, state: initialUpload }]);
      void runUpload(
        api,
        file,
        file.name,
        (e) => setItems((list) => list.map((i) => (i.id === id ? { ...i, state: uploadReducer(i.state, e) } : i))),
        { signal: alive.current },
      );
    }
    if (inputRef.current) inputRef.current.value = "";
  };

  const ready = items.filter((i) => i.state.phase === "ready" && i.state.assetId);
  const working = items.some((i) => !UPLOAD_TERMINAL.has(i.state.phase));

  const create = async () => {
    setCreating(true);
    setError(null);
    const body = { asset_ids: ready.map((i) => i.state.assetId!), locale: draftLocale, seller_notes: notes.trim() || null };
    try {
      const job = await api.studio.create(body, { idempotencyKey: keyFor(body) });
      router.push(`/products/studio/${job.id}`);
    } catch (e) {
      setError(e);
      setCreating(false);
    }
  };

  const limited = isApiError(error) && (error.code === "usage_limit_reached" || error.code === "feature_not_in_plan");

  return (
    <>
      <PageHeader title={t("studio.title")} subtitle={t("studio.subtitle")} />
      <div className={wf.stack} style={{ maxWidth: 880 }}>
        {limited && isApiError(error) ? (
          <InlineAlert tone="warning" title={errorMessage(t, error)}>
            <LimitActions
              buyCredits={parseLimitOptions(error.details.options ?? error.details.upgrade_options).includes("buy_credits")}
              upgrade
            />
            <RequestId id={error.requestId} />
          </InlineAlert>
        ) : error ? (
          <InlineAlert tone="danger">
            {errorMessage(t, error)}
            <RequestId id={isApiError(error) ? error.requestId : null} />
          </InlineAlert>
        ) : null}

        <SectionHeader title={t("studio.photos")} />
        <div className={wf.filePicker}>
          <label htmlFor="studio-files" className="srOnly">
            {t("studio.choose")}
          </label>
          <input
            ref={inputRef}
            id="studio-files"
            type="file"
            accept={ALLOWED_PHOTO_TYPES.join(",")}
            multiple
            onChange={(e) => addFiles(e.target.files)}
            disabled={items.length >= MAX_STUDIO_PHOTOS}
          />
          <span className={wf.hint}>{t("studio.fileHint")}</span>
        </div>
        {items.length ? (
          <ul className={wf.photoGrid} aria-live="polite" data-testid="studio-photos">
            {items.map((i) => (
              <PhotoTile
                key={i.id}
                name={i.name}
                preview={i.preview}
                state={i.state}
                onRemove={() => setItems((list) => list.filter((x) => x.id !== i.id))}
              />
            ))}
          </ul>
        ) : null}

        <div>
          <label htmlFor="studio-notes" className={productStyles.fieldLabel}>
            {t("studio.notes")}
          </label>
          <textarea
            id="studio-notes"
            className={productStyles.textarea}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder={t("studio.notesPlaceholder")}
            maxLength={2000}
            aria-describedby="studio-notes-hint"
          />
          <p id="studio-notes-hint" className={wf.hint}>
            {t("studio.notesHint")}
          </p>
        </div>
        <div style={{ maxWidth: 260 }}>
          <SelectField label={t("studio.draftLanguage")} value={draftLocale} onChange={(e) => setDraftLocale(e.target.value as "en" | "ne")}>
            <option value="ne">{t("language.ne")}</option>
            <option value="en">{t("language.en")}</option>
          </SelectField>
        </div>
        <div className={wf.footerBar} style={{ justifyContent: "flex-start", alignItems: "center" }}>
          <Button variant="primary" onClick={create} loading={creating} disabled={!ready.length || working}>
            <Icon name="automation" />
            {creating ? t("studio.creating") : t("studio.create")}
          </Button>
          {working ? <span className={wf.hint}>{t("studio.waitPhotos")}</span> : null}
        </div>
      </div>
    </>
  );
}
