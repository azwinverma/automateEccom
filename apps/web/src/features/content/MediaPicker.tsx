"use client";

import { QueryError, TableSkeleton } from "@/components/states/States";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import wf from "../shared/workflow.module.css";

/** Pick ready photos from the media library, in click order. */
export function MediaPicker({ value, onChange, max }: { value: string[]; onChange: (ids: string[]) => void; max: number }) {
  const { t } = useI18n();
  const media = useApiQuery((a) => a.media.list({ status: "ready", limit: 60 }));
  if (media.state.status === "loading") return <TableSkeleton columns="1fr 1fr 1fr" rows={2} label={t("common.loading")} />;
  if (media.state.status === "error") return <QueryError error={media.state.error} onRetry={media.reload} />;
  const images = media.state.data.items.filter((a) => a.kind !== "video" && a.derivatives.thumb?.url);
  if (!images.length) return <p className={wf.hint}>{t("content.new.noPhotos")}</p>;
  return (
    <ul className={wf.photoGrid} data-testid="media-picker">
      {images.map((a) => {
        const idx = value.indexOf(a.id);
        const picked = idx >= 0;
        return (
          <li key={a.id} className={[wf.photo, picked && wf.photoPicked].filter(Boolean).join(" ")}>
            <button
              type="button"
              className={wf.photoPick}
              aria-pressed={picked}
              aria-label={t("content.new.selectPhoto", { name: a.file_name })}
              disabled={!picked && value.length >= max}
              onClick={() => onChange(picked ? value.filter((x) => x !== a.id) : [...value, a.id])}
            >
              <div className={wf.photoFrame}>
                {/* eslint-disable-next-line @next/next/no-img-element -- signed thumbnail URL */}
                <img src={a.derivatives.thumb!.url!} alt="" />
                {picked ? <span className={wf.photoOrder}>{idx + 1}</span> : null}
              </div>
            </button>
            <span className={wf.photoName}>{a.file_name}</span>
          </li>
        );
      })}
    </ul>
  );
}
