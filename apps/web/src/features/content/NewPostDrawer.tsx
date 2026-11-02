"use client";

import { isApiError, type ChannelConnection, type PostKind } from "@commerce-os/api-client";
import { useEffect, useState, type FormEvent } from "react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { Checkbox, SelectField } from "@/components/ui/Field";
import { InlineAlert, RequestId, useToast } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ChipInput } from "../products/ChipInput";
import productStyles from "../products/products.module.css";
import wf from "../shared/workflow.module.css";
import styles from "./content.module.css";
import { MediaPicker } from "./MediaPicker";

const KINDS: PostKind[] = ["post", "story", "reel"];

export function NewPostDrawer({
  open,
  onOpenChange,
  connections,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  connections: ChannelConnection[];
  onCreated: () => void;
}) {
  const { t } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const postable = connections.filter((c) => c.capabilities.includes("content_publish") && c.status === "connected");
  const [mode, setMode] = useState<"manual" | "studio">("manual");
  const [channel, setChannel] = useState("");
  const [kind, setKind] = useState<PostKind>("post");
  const [caption, setCaption] = useState("");
  const [hashtags, setHashtags] = useState<string[]>([]);
  const [assets, setAssets] = useState<string[]>([]);
  const [jobId, setJobId] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [captionErr, setCaptionErr] = useState<string | null>(null);
  const action = useAction();
  const jobs = useApiQuery((a) => (open ? a.studio.jobs({ limit: 50 }) : Promise.resolve({ items: [] })), [open]);
  const drafts = jobs.state.status === "success" ? jobs.state.data.items.filter((j) => j.status === "ready" || j.status === "applied") : [];

  useEffect(() => {
    if (!open) return;
    setMode("manual");
    setChannel(postable[0]?.id ?? "");
    setKind("post");
    setCaption("");
    setHashtags([]);
    setAssets([]);
    setJobId("");
    setPicked([]);
    setCaptionErr(null);
    action.clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (mode === "manual") {
      if (!caption.trim()) {
        setCaptionErr(t("errors.caption_required"));
        return;
      }
      setCaptionErr(null);
      const p = await action.run(() => api.content.create({ connection_id: channel, caption: caption.trim(), hashtags, asset_ids: assets, kind }));
      if (p) {
        toast(t("content.new.created"));
        onCreated();
      }
    } else {
      const r = await action.run(() => api.content.fromStudio({ job_id: jobId, connection_ids: picked, kind }));
      if (r) {
        toast(t("studio.postsCreated", { count: r.items.length }));
        onCreated();
      }
    }
  };

  const canSubmit = postable.length > 0 && (mode === "manual" ? Boolean(channel) : Boolean(jobId) && picked.length > 0);

  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={t("content.new.title")}
      wide
      footer={
        <Button variant="primary" type="submit" form="new-post-form" loading={action.pending} disabled={!canSubmit}>
          {t("content.new.create")}
        </Button>
      }
    >
      {postable.length === 0 ? (
        <div className={wf.stack}>
          <p className={wf.hint}>{t("content.new.noChannels")}</p>
          <div>
            <ButtonLink href="/settings/channels" size="sm">
              {t("listings.connectLink")}
            </ButtonLink>
          </div>
        </div>
      ) : (
        <form id="new-post-form" className={wf.stack} onSubmit={submit} noValidate>
          <div role="tablist" aria-label={t("content.new.mode")} className={styles.modeTabs}>
            {(["manual", "studio"] as const).map((m) => (
              <button
                key={m}
                type="button"
                role="tab"
                aria-selected={mode === m}
                className={productStyles.tab}
                onClick={() => setMode(m)}
              >
                {t(m === "manual" ? "content.new.manual" : "content.new.fromStudio")}
              </button>
            ))}
          </div>
          {action.error ? (
            <InlineAlert tone="danger">
              {errorMessage(t, action.error)}
              <RequestId id={isApiError(action.error) ? action.error.requestId : null} />
            </InlineAlert>
          ) : null}
          <SelectField label={t("content.new.kind")} value={kind} onChange={(e) => setKind(e.target.value as PostKind)}>
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {t(`content.kind.${k}`)}
              </option>
            ))}
          </SelectField>
          {mode === "manual" ? (
            <>
              <SelectField label={t("content.new.channel")} value={channel} onChange={(e) => setChannel(e.target.value)}>
                {postable.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.display_name}
                  </option>
                ))}
              </SelectField>
              <div>
                <label htmlFor="new-caption" className={productStyles.fieldLabel}>
                  {t("content.drawer.caption")}
                </label>
                <textarea
                  id="new-caption"
                  className={productStyles.textarea}
                  value={caption}
                  onChange={(e) => setCaption(e.target.value)}
                  maxLength={5000}
                  aria-invalid={captionErr ? true : undefined}
                  aria-describedby={captionErr ? "new-caption-err" : undefined}
                />
                {captionErr ? (
                  <p id="new-caption-err" className={productStyles.cellError} style={{ maxWidth: "none" }}>
                    {captionErr}
                  </p>
                ) : null}
              </div>
              <ChipInput label={t("content.drawer.hashtags")} values={hashtags} onChange={setHashtags} placeholder={t("content.drawer.hashtagsPlaceholder")} max={30} />
              <div>
                <span className={productStyles.fieldLabel}>{t("content.new.photos")}</span>
                <p className={wf.hint} style={{ marginBottom: "var(--space-2)" }}>
                  {t("content.new.photosHint")}
                </p>
                <MediaPicker value={assets} onChange={setAssets} max={10} />
              </div>
            </>
          ) : (
            <>
              <SelectField label={t("content.new.draft")} value={jobId} onChange={(e) => setJobId(e.target.value)}>
                <option value="">{drafts.length ? "—" : t("content.new.noDrafts")}</option>
                {drafts.map((j) => (
                  <option key={j.id} value={j.id}>
                    {(j.draft?.title_en || j.draft?.title_ne || j.id.slice(0, 8)) + ` · ${t(`studio.status.${j.status}`)}`}
                  </option>
                ))}
              </SelectField>
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
            </>
          )}
        </form>
      )}
    </Drawer>
  );
}
