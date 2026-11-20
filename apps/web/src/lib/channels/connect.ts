/** Store channels connected with a URL + REST keys (WooCommerce). */
export const KEY_PROVIDERS: ReadonlySet<string> = new Set(["woocommerce"]);
/** Messaging channels connected with the seller's own bot/app credentials. */
export const MESSAGING_PROVIDERS: ReadonlySet<string> = new Set(["telegram", "whatsapp_cloud"]);

/** Facebook Page + its Instagram account, through the seller's own Meta app (one connect for both). */
export const META_PROVIDERS: ReadonlySet<string> = new Set(["facebook_page", "instagram"]);
/** Shown as "coming soon": no connect until the platform approves the app. */
export const COMING_SOON_PROVIDERS: ReadonlySet<string> = new Set(["tiktok"]);

export type ConnectFlow = "oauth" | "keys" | "messaging" | "meta";

/** How a provider connects. Uses the providers endpoint's `auth_kind` when present. */
export function connectFlow(providerCode: string, authKind?: "oauth" | "api_keys"): ConnectFlow {
  if (MESSAGING_PROVIDERS.has(providerCode)) return "messaging";
  if (META_PROVIDERS.has(providerCode)) return "meta";
  if (KEY_PROVIDERS.has(providerCode)) return "keys";
  return authKind === "api_keys" ? "keys" : "oauth";
}

/** Required fields that are still empty (trimmed). */
export function missingMessagingFields(required: readonly string[], values: Record<string, string>): string[] {
  return required.filter((f) => !(values[f] ?? "").trim());
}

export interface KeysForm {
  store_url: string;
  consumer_key: string;
  consumer_secret: string;
}

export type KeysFieldError = "required" | "https_required" | "invalid_url" | "too_short";

/** Mirrors backend checks (https store URL, 10–200 char keys); the server re-validates. */
export function validateKeys(form: KeysForm): Partial<Record<keyof KeysForm, KeysFieldError>> {
  const e: Partial<Record<keyof KeysForm, KeysFieldError>> = {};
  const url = form.store_url.trim();
  if (!url) e.store_url = "required";
  else {
    try {
      const u = new URL(url);
      if (u.protocol !== "https:") e.store_url = "https_required";
      else if (!u.hostname.includes(".")) e.store_url = "invalid_url";
    } catch {
      e.store_url = url.startsWith("http://") ? "https_required" : "invalid_url";
    }
  }
  for (const k of ["consumer_key", "consumer_secret"] as const) {
    const v = form[k].trim();
    if (!v) e[k] = "required";
    else if (v.length < 10) e[k] = "too_short";
  }
  return e;
}

/** Normalise the store URL the way sellers paste it ("https://shop.np/" → "https://shop.np"). */
export function normalizeStoreUrl(url: string): string {
  return url.trim().replace(/\/+$/, "");
}

/** Facebook Page IDs are digits (the API accepts 5 to 25). */
export function validPageId(value: string): boolean {
  return /^\d{5,25}$/.test(value.trim());
}
