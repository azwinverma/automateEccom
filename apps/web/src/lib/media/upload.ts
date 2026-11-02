import { ApiError, putToSignedUrl, type Api, type MediaAsset } from "@commerce-os/api-client";

/** Mirrors backend ALLOWED_UPLOAD_TYPES and media_max_upload_bytes (20 MB). */
export const ALLOWED_PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"] as const;
export const MAX_PHOTO_BYTES = 20 * 1024 * 1024;

export type UploadPhase = "queued" | "requesting" | "uploading" | "completing" | "processing" | "ready" | "rejected" | "failed";

export const UPLOAD_TERMINAL: ReadonlySet<UploadPhase> = new Set(["ready", "rejected", "failed"]);

export interface UploadState {
  phase: UploadPhase;
  assetId: string | null;
  asset: MediaAsset | null;
  error: unknown;
}

export const initialUpload: UploadState = { phase: "queued", assetId: null, asset: null, error: null };

export type UploadEvent =
  | { type: "request" }
  | { type: "ticket"; assetId: string }
  | { type: "uploaded" }
  | { type: "asset"; asset: MediaAsset }
  | { type: "error"; error: unknown };

/**
 * Upload state machine. Events arriving in an impossible state are ignored, so a late
 * poll response can't resurrect a failed upload.
 */
export function uploadReducer(state: UploadState, event: UploadEvent): UploadState {
  if (UPLOAD_TERMINAL.has(state.phase)) return state;
  switch (event.type) {
    case "request":
      return state.phase === "queued" ? { ...state, phase: "requesting" } : state;
    case "ticket":
      return state.phase === "requesting" ? { ...state, phase: "uploading", assetId: event.assetId } : state;
    case "uploaded":
      return state.phase === "uploading" ? { ...state, phase: "completing" } : state;
    case "asset": {
      if (state.phase !== "completing" && state.phase !== "processing") return state;
      const s = event.asset.status;
      const phase: UploadPhase = s === "ready" ? "ready" : s === "rejected" ? "rejected" : s === "deleted" ? "failed" : "processing";
      return { ...state, phase, asset: event.asset };
    }
    case "error":
      return { ...state, phase: "failed", error: event.error };
  }
}

/** Client-side pre-check; the server re-validates everything. */
export function precheckPhoto(file: { type: string; size: number }): "unsupported_media_type" | "file_too_large" | null {
  if (!(ALLOWED_PHOTO_TYPES as readonly string[]).includes(file.type)) return "unsupported_media_type";
  if (file.size <= 0 || file.size > MAX_PHOTO_BYTES) return "file_too_large";
  return null;
}

export interface RunUploadOptions {
  fetchImpl?: typeof fetch;
  sleep?: (ms: number) => Promise<void>;
  /** Max polls while the pipeline scans and resizes the photo. */
  maxPolls?: number;
  signal?: { aborted: boolean };
}

const defaultSleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

/**
 * signed upload → PUT (no auth) → complete → poll until ready/rejected. Calls `dispatch`
 * with each event; returns the final state.
 */
export async function runUpload(
  api: Api,
  file: File | Blob,
  fileName: string,
  dispatch: (e: UploadEvent) => void,
  opts: RunUploadOptions = {},
): Promise<UploadState> {
  let state = initialUpload;
  const emit = (e: UploadEvent) => {
    state = uploadReducer(state, e);
    dispatch(e);
  };
  const sleep = opts.sleep ?? defaultSleep;
  const maxPolls = opts.maxPolls ?? 40;
  try {
    const pre = precheckPhoto({ type: file.type, size: file.size });
    if (pre) throw new ApiError({ status: 400, code: pre, message: pre });
    emit({ type: "request" });
    const { asset_id, upload } = await api.media.createUpload({
      file_name: fileName,
      content_type: file.type,
      size_bytes: file.size,
      purpose: "product",
    });
    emit({ type: "ticket", assetId: asset_id });
    await putToSignedUrl(upload, file, opts.fetchImpl);
    emit({ type: "uploaded" });
    emit({ type: "asset", asset: await api.media.complete(asset_id) });
    for (let i = 0; i < maxPolls && state.phase === "processing"; i++) {
      if (opts.signal?.aborted) return state;
      await sleep(Math.min(4000, Math.round(800 * 1.4 ** i)));
      emit({ type: "asset", asset: await api.media.get(asset_id) });
    }
    if (state.phase === "processing") {
      emit({ type: "error", error: new ApiError({ status: 0, code: "processing_timeout", message: "Still processing" }) });
    }
  } catch (e) {
    emit({ type: "error", error: e });
  }
  return state;
}
