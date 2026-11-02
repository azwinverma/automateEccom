"use client";

import type { MediaAsset } from "@commerce-os/api-client";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { UPLOAD_TERMINAL, type UploadState } from "@/lib/media/upload";
import wf from "../shared/workflow.module.css";

/** Retake tips for quality flags and plain copy for rejections. */
export function PhotoFeedback({ asset }: { asset: MediaAsset | null }) {
  const { t } = useI18n();
  if (!asset) return null;
  if (asset.status === "rejected") {
    return (
      <span className={[wf.photoStatus, wf.photoStatusBad].join(" ")}>
        {t.dynamic(`studio.rejected.${asset.rejection_reason ?? "generic"}`) ?? t("studio.rejected.generic")}
      </span>
    );
  }
  return (
    <>
      {asset.quality_flags.map((f) => {
        const tip = t.dynamic(`studio.tip.${f}`);
        return tip ? (
          <span key={f} className={wf.photoTip}>
            {tip}
          </span>
        ) : null;
      })}
      {asset.stripped_location_metadata ? <span className={wf.photoStatus}>{t("studio.locationStripped")}</span> : null}
    </>
  );
}

export function PhotoTile({
  name,
  preview,
  state,
  onRemove,
}: {
  name: string;
  preview: string | null;
  state: UploadState;
  onRemove?: () => void;
}) {
  const { t } = useI18n();
  const busy = !UPLOAD_TERMINAL.has(state.phase);
  const bad = state.phase === "rejected" || state.phase === "failed";
  return (
    <li className={wf.photo} data-phase={state.phase}>
      <div className={wf.photoFrame}>
        {preview ? (
          // eslint-disable-next-line @next/next/no-img-element -- local object URL preview
          <img src={preview} alt="" />
        ) : null}
        {busy ? (
          <div className={wf.photoBar} aria-hidden="true">
            <span />
          </div>
        ) : null}
        {onRemove ? (
          <span className={wf.photoRemove}>
            <Button size="sm" iconOnly variant="secondary" aria-label={t("studio.removePhoto", { name })} onClick={onRemove}>
              <Icon name="close" size={12} />
            </Button>
          </span>
        ) : null}
      </div>
      <span className={wf.photoName} title={name}>
        {name}
      </span>
      <span className={[wf.photoStatus, bad && wf.photoStatusBad].filter(Boolean).join(" ")} role={bad ? "alert" : undefined}>
        {t(`studio.phase.${state.phase}`)}
      </span>
      {state.phase === "failed" && state.error ? <span className={wf.photoTip}>{errorMessage(t, state.error)}</span> : null}
      <PhotoFeedback asset={state.asset} />
    </li>
  );
}
