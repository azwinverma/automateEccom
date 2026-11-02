import { ApiError } from "./errors";
import type { UploadTicket } from "./types";

/**
 * PUT a file to a signed upload URL. Deliberately uses a bare fetch: no Authorization,
 * no X-Merchant-Id — the signature in the URL is the credential, and storage hosts
 * (S3/R2 or the dev object store) must never receive the user's access token.
 */
export async function putToSignedUrl(
  ticket: UploadTicket,
  body: Blob,
  fetchImpl: typeof fetch = (...a) => globalThis.fetch(...a),
): Promise<void> {
  let res: Response;
  try {
    res = await fetchImpl(ticket.url, {
      method: ticket.method,
      headers: { ...ticket.headers },
      body,
      credentials: "omit",
      mode: "cors",
    });
  } catch (e) {
    throw new ApiError({ status: 0, code: "upload_failed", message: e instanceof Error ? e.message : "Upload failed" });
  }
  if (!res.ok) {
    const code = res.status === 403 ? "upload_url_expired" : res.status === 413 ? "file_too_large" : "upload_failed";
    throw new ApiError({ status: res.status, code, message: `Upload failed (${res.status})` });
  }
}
