"use client";

import { isApiError, type ChannelConnection, type ContentPost } from "@commerce-os/api-client";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog, Drawer } from "@/components/ui/Drawer";
import { TextField } from "@/components/ui/Field";
import { Badge, InlineAlert, RequestId, useToast, type Tone } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { canEditPost, editResetsApproval, postActions, type PostAction } from "@/lib/content/actions";
import { addDays, dayKey, zonedToUtcIso } from "@/lib/content/calendar";
import { ChipInput } from "../products/ChipInput";
import productStyles from "../products/products.module.css";
import wf from "../shared/workflow.module.css";
import { issueText } from "../studio/StudioJob";
import styles from "./content.module.css";

export const POST_TONE: Record<string, Tone> = {
  draft: "neutral",
  pending_approval: "warning",
  approved: "info",
  scheduled: "automated",
  publishing: "info",
  published: "success",
  failed: "danger",
  cancelled: "neutral",
};

export function SourceTag({ source }: { source: string }) {
  const { t } = useI18n();
  const label = t.dynamic(`content.source.${source}`) ?? source;
  return source.startsWith("ai") ? <span className={wf.aiTag}>{label}</span> : <span className={wf.muted}>{label}</span>;
}

export function PostDrawer({
  post,
  connection,
  tz,
  onClose,
  onChanged,
}: {
  post: ContentPost | null;
  connection: ChannelConnection | undefined;
  tz: string;
  onClose: () => void;
  onChanged: (p: ContentPost) => void;
}) {
  const { t, dateTime } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const [caption, setCaption] = useState("");
  const [hashtags, setHashtags] = useState<string[]>([]);
  const [day, setDay] = useState("");
  const [time, setTime] = useState("10:00");
  const [note, setNote] = useState("");
  const [confirmCancel, setConfirmCancel] = useState(false);
  const action = useAction();

  useEffect(() => {
    if (!post) return;
    setCaption(post.caption);
    setHashtags(post.hashtags);
    setDay(addDays(dayKey(new Date(), tz), 1));
    setTime("10:00");
    setNote("");
    action.clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [post?.id, post?.version, tz]);

  if (!post) return null;
  const perms = { write: can("content.write"), approve: can("content.approve"), publish: can("content.publish") };
  const actions = postActions(post.status, perms);
  const editable = canEditPost(post.status) && perms.write;
  const dirty = caption !== post.caption || JSON.stringify(hashtags) !== JSON.stringify(post.hashtags);

  const run = async (fn: () => Promise<ContentPost>, message: string) => {
    const p = await action.run(fn);
    if (p) {
      toast(message);
      onChanged(p);
    }
    return p;
  };

  const doAction = (a: PostAction) => {
    const updated = t("content.drawer.updated");
    if (a === "submit") return run(() => api.content.submit(post.id), updated);
    if (a === "approve") return run(() => api.content.approve(post.id), updated);
    if (a === "reject") return run(() => api.content.reject(post.id, note.trim() || undefined), updated);
    if (a === "publishNow") return run(() => api.content.schedule(post.id, null), updated);
    if (a === "schedule") return run(() => api.content.schedule(post.id, zonedToUtcIso(day, time, tz)), updated);
    if (a === "unschedule") return run(() => api.content.unschedule(post.id), updated);
    setConfirmCancel(true);
    return Promise.resolve(undefined);
  };

  const err = action.error;
  return (
    <Drawer
      open
      onOpenChange={(o) => !o && onClose()}
      title={connection?.display_name ?? t("content.unknownChannel")}
      description={`${t(`content.kind.${post.kind}`)} · ${t(`content.status.${post.status}`)}`}
      wide
    >
      <div className={wf.stack} data-testid="post-drawer">
        <div className={styles.metaRow}>
          <Badge tone={POST_TONE[post.status] ?? "neutral"}>{t(`content.status.${post.status}`)}</Badge>
          <SourceTag source={post.source} />
          {post.scheduled_at ? <span className={wf.hint}>{t("content.drawer.scheduledFor", { when: dateTime(post.scheduled_at) })}</span> : null}
          {post.published_at ? <span className={wf.hint}>{t("content.drawer.postedAt", { when: dateTime(post.published_at) })}</span> : null}
        </div>
        {err ? (
          <InlineAlert tone="danger">
            {errorMessage(t, err)}
            <RequestId id={isApiError(err) ? err.requestId : null} />
          </InlineAlert>
        ) : null}
        {post.rejection_note ? <InlineAlert tone="info" live={false}>{t("content.drawer.rejectionNote", { note: post.rejection_note })}</InlineAlert> : null}
        {post.last_error_code ? (
          <InlineAlert tone="warning" live={false}>
            {t("content.drawer.lastError", { message: t.dynamic(`errors.${post.last_error_code}`) ?? post.last_error_code })}
          </InlineAlert>
        ) : null}
        {post.issues.length ? (
          <InlineAlert tone="warning" title={t("content.drawer.issues")} live={false}>
            <ul className={wf.issueList}>
              {post.issues.map((i, n) => (
                <li key={n}>{issueText(t, i)}</li>
              ))}
            </ul>
          </InlineAlert>
        ) : null}

        <div>
          <label htmlFor="post-caption" className={productStyles.fieldLabel}>
            {t("content.drawer.caption")}
          </label>
          <textarea
            id="post-caption"
            className={productStyles.textarea}
            style={{ minHeight: 160 }}
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            readOnly={!editable}
            maxLength={5000}
          />
        </div>
        {editable ? (
          <ChipInput label={t("content.drawer.hashtags")} values={hashtags} onChange={setHashtags} placeholder={t("content.drawer.hashtagsPlaceholder")} max={30} />
        ) : hashtags.length ? (
          <p className={wf.hint}>{hashtags.map((h) => (h.startsWith("#") ? h : `#${h}`)).join(" ")}</p>
        ) : null}
        {editable && dirty ? (
          <div className={styles.metaRow}>
            <Button
              variant="primary"
              loading={action.pending}
              onClick={() => run(() => api.content.update(post.id, post.version, { caption, hashtags }), t("content.drawer.saved"))}
            >
              {t("content.drawer.save")}
            </Button>
            {editResetsApproval(post.status) ? <span className={wf.hint}>{t("content.drawer.editResets")}</span> : null}
          </div>
        ) : !canEditPost(post.status) && post.status === "scheduled" ? (
          <p className={wf.hint}>{t("content.drawer.locked")}</p>
        ) : null}

        {actions.includes("schedule") && !dirty ? (
          <div className={styles.scheduleRow}>
            <TextField label={t("content.drawer.date")} type="date" value={day} onChange={(e) => setDay(e.target.value)} />
            <TextField label={t("content.drawer.time", { tz })} type="time" value={time} onChange={(e) => setTime(e.target.value)} />
            <Button variant="primary" loading={action.pending} onClick={() => doAction("schedule")}>
              {t("content.action.schedule")}
            </Button>
          </div>
        ) : null}
        {actions.includes("reject") ? (
          <TextField label={t("content.drawer.rejectNote")} optionalLabel={t("common.optional")} value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} />
        ) : null}
        {post.status === "pending_approval" && !perms.approve ? <p className={wf.hint}>{t("content.drawer.noApprove")}</p> : null}

        <div className={wf.footerBar} style={{ marginTop: 0 }}>
          {actions
            .filter((a) => a !== "schedule")
            .map((a) => (
              <Button
                key={a}
                variant={a === "approve" || a === "submit" ? "primary" : a === "cancel" ? "ghost" : "secondary"}
                disabled={dirty && a !== "cancel"}
                loading={action.pending}
                onClick={() => doAction(a)}
              >
                {t(`content.action.${a}`)}
              </Button>
            ))}
        </div>
      </div>
      <ConfirmDialog
        open={confirmCancel}
        onOpenChange={setConfirmCancel}
        title={t("content.drawer.cancelTitle")}
        body={t("content.drawer.cancelBody")}
        confirmLabel={t("content.action.cancel")}
        pending={action.pending}
        destructive
        onConfirm={async () => {
          await run(() => api.content.cancel(post.id), t("content.drawer.updated"));
          setConfirmCancel(false);
        }}
      />
    </Drawer>
  );
}
