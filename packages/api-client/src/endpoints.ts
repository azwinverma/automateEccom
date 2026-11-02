import type { ApiClient } from "./client";
import type {
  Category,
  Collection,
  ImportJob,
  ProductAttribute,
  ProductCreateInput,
  ProductDetail,
  ProductListQuery,
  ProductPatchInput,
  ProductStatus,
  ProductSummary,
  VariantPatchInput,
  AuditLogEntry,
  AuditLogQuery,
  CreateMerchantInput,
  Credits,
  EffectivePermissions,
  Entitlements,
  Invitation,
  LoginInput,
  LoginResponse,
  Me,
  Member,
  Merchant,
  MfaVerifyInput,
  Page,
  RecoveryCodes,
  RegisterInput,
  Role,
  Session,
  Store,
  Subscription,
  TokenPair,
  TotpSetup,
  UpdateMeInput,
  User,
} from "./types";

/** Options for idem endpoints: pass a stable key to make retries safe. */
export interface IdemOptions {
  idempotencyKey?: string;
}

const idem = (o?: IdemOptions): string | true => o?.idempotencyKey ?? true;

/** Typed endpoint map over an ApiClient. */
export function createApi(client: ApiClient) {
  return {
    auth: {
      register: (body: RegisterInput) =>
        client.request<{ user: User } | User>("/auth/register", { method: "POST", body, auth: false }),
      login: (body: LoginInput, headers?: Record<string, string>) =>
        client.request<LoginResponse>("/auth/login", { method: "POST", body, auth: false, headers }),
      mfaVerify: (body: MfaVerifyInput, headers?: Record<string, string>) =>
        client.request<TokenPair>("/auth/mfa/verify", { method: "POST", body, auth: false, headers }),
      refresh: (refresh_token: string, headers?: Record<string, string>) =>
        client.request<TokenPair>("/auth/refresh", { method: "POST", body: { refresh_token }, auth: false, headers }),
      logout: (refresh_token: string, headers?: Record<string, string>) =>
        client.request<void>("/auth/logout", { method: "POST", body: { refresh_token }, auth: false, headers }),
      sessions: () => client.request<{ items: Session[] }>("/auth/sessions"),
      revokeSession: (id: string) =>
        client.request<void>(`/auth/sessions/${encodeURIComponent(id)}`, { method: "DELETE" }),
      revokeOtherSessions: () => client.request<void>("/auth/sessions/revoke-all", { method: "POST" }),
      totpSetup: () => client.request<TotpSetup>("/auth/mfa/totp/setup", { method: "POST" }),
      totpEnable: (code: string) =>
        client.request<RecoveryCodes>("/auth/mfa/totp/enable", { method: "POST", body: { code } }),
      totpDisable: (code: string, password: string) =>
        client.request<void>("/auth/mfa/totp/disable", { method: "POST", body: { code, password } }),
      requestEmailVerification: () => client.request<void>("/auth/verify-email/request", { method: "POST" }),
      confirmEmailVerification: (token: string) =>
        client.request<void>("/auth/verify-email/confirm", { method: "POST", body: { token } }),
    },
    me: {
      get: () => client.request<Me>("/me"),
      update: (body: UpdateMeInput) => client.request<Me["user"] | Me>("/me", { method: "PATCH", body }),
      permissions: () => client.request<EffectivePermissions>("/permissions/me", { tenant: true }),
    },
    merchants: {
      create: (body: CreateMerchantInput, o?: IdemOptions) =>
        client.request<{ merchant: Merchant } | Merchant>("/merchants", {
          method: "POST",
          body,
          idempotent: idem(o),
        }),
      current: () => client.request<Merchant>("/merchant", { tenant: true }),
    },
    stores: {
      list: (q?: { limit?: number; cursor?: string }) => client.request<Page<Store>>("/stores", { tenant: true, query: q }),
    },
    team: {
      members: () => client.request<{ items: Member[] }>("/members", { tenant: true }),
      changeRole: (id: string, role: Role) =>
        client.request<Member>(`/members/${encodeURIComponent(id)}`, { method: "PATCH", body: { role }, tenant: true }),
      removeMember: (id: string) =>
        client.request<void>(`/members/${encodeURIComponent(id)}`, { method: "DELETE", tenant: true }),
      invitations: () => client.request<{ items: Invitation[] }>("/invitations", { tenant: true }),
      invite: (body: { email: string; role: Role }, o?: IdemOptions) =>
        client.request<{ invitation: Invitation } | Invitation>("/invitations", {
          method: "POST",
          body,
          tenant: true,
          idempotent: idem(o),
        }),
      revokeInvitation: (id: string) =>
        client.request<void>(`/invitations/${encodeURIComponent(id)}`, { method: "DELETE", tenant: true }),
      acceptInvitation: (token: string) =>
        client.request<unknown>("/invitations/accept", { method: "POST", body: { token } }),
    },
    billing: {
      subscription: () => client.request<Subscription>("/billing/subscription", { tenant: true }),
      entitlements: () => client.request<Entitlements>("/billing/entitlements", { tenant: true }),
      credits: () => client.request<Credits>("/billing/credits", { tenant: true }),
    },
    audit: {
      list: (q: AuditLogQuery = {}) =>
        client.request<Page<AuditLogEntry>>("/audit-logs", { tenant: true, query: { ...q } }),
    },
    catalog: {
      products: (q: ProductListQuery = {}) =>
        client.request<Page<ProductSummary>>("/catalog/products", { tenant: true, query: { ...q } }),
      product: (id: string) => client.request<ProductDetail>(`/catalog/products/${encodeURIComponent(id)}`, { tenant: true }),
      createProduct: (body: ProductCreateInput, o?: IdemOptions) =>
        client.request<ProductDetail>("/catalog/products", { method: "POST", body, tenant: true, idempotent: idem(o) }),
      /** Send the `version` you last read; `409 version_conflict` if someone else saved first. */
      updateProduct: (id: string, version: number, fields: ProductPatchInput) =>
        client.request<ProductDetail>(`/catalog/products/${encodeURIComponent(id)}`, {
          method: "PATCH",
          body: { version, ...fields },
          tenant: true,
        }),
      setStatus: (id: string, status: ProductStatus, version: number) =>
        client.request<ProductDetail>(`/catalog/products/${encodeURIComponent(id)}/status`, {
          method: "POST",
          body: { status, version },
          tenant: true,
        }),
      updateVariant: (id: string, variantId: string, body: VariantPatchInput) =>
        client.request<ProductDetail>(`/catalog/products/${encodeURIComponent(id)}/variants/${encodeURIComponent(variantId)}`, {
          method: "PATCH",
          body,
          tenant: true,
        }),
      archiveVariant: (id: string, variantId: string) =>
        client.request<void>(`/catalog/products/${encodeURIComponent(id)}/variants/${encodeURIComponent(variantId)}`, {
          method: "DELETE",
          tenant: true,
        }),
      setAttributes: (id: string, items: Pick<ProductAttribute, "key" | "value" | "locale">[]) =>
        client.request<ProductDetail>(`/catalog/products/${encodeURIComponent(id)}/attributes`, {
          method: "PUT",
          body: { items },
          tenant: true,
        }),
      confirmAttributes: (id: string, keys: string[]) =>
        client.request<ProductDetail>(`/catalog/products/${encodeURIComponent(id)}/attributes/confirm`, {
          method: "POST",
          body: { keys },
          tenant: true,
        }),
      categories: () => client.request<{ items: Category[] }>("/catalog/categories", { tenant: true }),
      createCategory: (body: { name: string; name_ne?: string; parent_id?: string | null }) =>
        client.request<Category>("/catalog/categories", { method: "POST", body, tenant: true }),
      collections: () => client.request<{ items: Collection[] }>("/catalog/collections", { tenant: true }),
      uploadImport: (file: File | Blob, fileName = "import.csv") => {
        const form = new FormData();
        form.append("file", file, fileName);
        return client.request<ImportJob>("/catalog/imports", { method: "POST", body: form, tenant: true });
      },
      importJob: (id: string) => client.request<ImportJob>(`/catalog/imports/${encodeURIComponent(id)}`, { tenant: true }),
    },
    featureFlags: {
      get: () => client.request<{ flags: Record<string, boolean> }>("/feature-flags", { tenant: true }),
    },
  };
}

export type Api = ReturnType<typeof createApi>;

/** Responses that may or may not be wrapped (`{merchant}` vs bare object). */
export function unwrap<T>(value: T | Record<string, T>, key: string): T {
  if (value && typeof value === "object" && key in (value as Record<string, unknown>)) {
    return (value as Record<string, T>)[key] as T;
  }
  return value as T;
}
