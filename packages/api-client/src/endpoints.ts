import type { ApiClient } from "./client";
import type {
  AutoReelInput,
  ChannelConnection,
  ChannelListing,
  ChannelProvider,
  ContentPost,
  ContentPostInput,
  ExceptionList,
  MediaAsset,
  PostKind,
  StudioApplyInput,
  StudioJob,
  StudioStatus,
  UploadTicket,
  VariantInput,
  VideoJob,
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
        client.request<void>("/auth/verify-email/confirm", { method: "POST", body: { token }, auth: false }),
      /** Always 202: the response never says whether the account exists. */
      requestPasswordReset: (email: string) =>
        client.request<void>("/auth/password/forgot", { method: "POST", body: { email }, auth: false }),
      resetPassword: (token: string, password: string) =>
        client.request<void>("/auth/password/reset", { method: "POST", body: { token, password }, auth: false }),
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
      /** Pass the product `version` you last read; `409 version_conflict` if it moved on. */
      updateVariant: (id: string, variantId: string, body: VariantPatchInput, version?: number) =>
        client.request<ProductDetail>(`/catalog/products/${encodeURIComponent(id)}/variants/${encodeURIComponent(variantId)}`, {
          method: "PATCH",
          body: version === undefined ? body : { ...body, version },
          tenant: true,
        }),
      archiveVariant: (id: string, variantId: string, version?: number) =>
        client.request<void>(`/catalog/products/${encodeURIComponent(id)}/variants/${encodeURIComponent(variantId)}`, {
          method: "DELETE",
          tenant: true,
          query: { version },
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
      updateCategory: (id: string, body: { name?: string; name_ne?: string | null; move?: boolean; parent_id?: string | null }) =>
        client.request<Category>(`/catalog/categories/${encodeURIComponent(id)}`, { method: "PATCH", body, tenant: true }),
      deleteCategory: (id: string) =>
        client.request<void>(`/catalog/categories/${encodeURIComponent(id)}`, { method: "DELETE", tenant: true }),
      collections: () => client.request<{ items: Collection[] }>("/catalog/collections", { tenant: true }),
      createCollection: (body: { title: string; description?: string | null }) =>
        client.request<Collection>("/catalog/collections", { method: "POST", body, tenant: true }),
      collectionProducts: (collectionId: string) =>
        client.request<{ items: { product_id: string; title: string; status: ProductStatus; position: number }[] }>(
          `/catalog/collections/${encodeURIComponent(collectionId)}/products`,
          { tenant: true },
        ),
      addToCollection: (collectionId: string, productId: string) =>
        client.request<void>(`/catalog/collections/${encodeURIComponent(collectionId)}/products/${encodeURIComponent(productId)}`, {
          method: "PUT",
          tenant: true,
        }),
      removeFromCollection: (collectionId: string, productId: string) =>
        client.request<void>(`/catalog/collections/${encodeURIComponent(collectionId)}/products/${encodeURIComponent(productId)}`, {
          method: "DELETE",
          tenant: true,
        }),
      uploadImport: (file: File | Blob, fileName = "import.csv") => {
        const form = new FormData();
        form.append("file", file, fileName);
        return client.request<ImportJob>("/catalog/imports", { method: "POST", body: form, tenant: true });
      },
      /** Add one variant to a saved product (optimistic lock on `version`). */
      addVariant: (id: string, version: number, body: VariantInput) =>
        client.request<ProductDetail>(`/catalog/products/${encodeURIComponent(id)}/variants`, {
          method: "POST",
          body: { version, ...body },
          tenant: true,
        }),
      publish: (id: string, connectionIds: string[]) =>
        client.request<{ items: ChannelListing[] }>(`/catalog/products/${encodeURIComponent(id)}/publish`, {
          method: "POST",
          body: { connection_ids: connectionIds },
          tenant: true,
        }),
      listings: (id: string) =>
        client.request<{ items: ChannelListing[] }>(`/catalog/products/${encodeURIComponent(id)}/listings`, { tenant: true }),
      unpublish: (id: string, connectionId: string) =>
        client.request<ChannelListing>(
          `/catalog/products/${encodeURIComponent(id)}/listings/${encodeURIComponent(connectionId)}`,
          { method: "DELETE", tenant: true },
        ),
      /** push = overwrite the channel with Nivaro's version; accept = keep the channel's version. */
      resolveDrift: (id: string, connectionId: string, action: "push" | "accept") =>
        client.request<ChannelListing>(
          `/catalog/products/${encodeURIComponent(id)}/listings/${encodeURIComponent(connectionId)}/resolve-drift`,
          { method: "POST", body: { action }, tenant: true },
        ),
      importJob: (id: string) => client.request<ImportJob>(`/catalog/imports/${encodeURIComponent(id)}`, { tenant: true }),
    },
    exceptions: {
      list: () => client.request<ExceptionList>("/exceptions", { tenant: true }),
    },
    media: {
      createUpload: (body: { file_name: string; content_type: string; size_bytes: number; purpose?: "product" | "content" | "brand" | "other" }) =>
        client.request<{ asset_id: string; upload: UploadTicket }>("/media/uploads", { method: "POST", body, tenant: true }),
      complete: (id: string) =>
        client.request<MediaAsset>(`/media/${encodeURIComponent(id)}/complete`, { method: "POST", tenant: true }),
      get: (id: string) => client.request<MediaAsset>(`/media/${encodeURIComponent(id)}`, { tenant: true }),
      list: (q: { status?: "ready" | "processing" | "rejected"; limit?: number; cursor?: string } = {}) =>
        client.request<Page<MediaAsset>>("/media", { tenant: true, query: { ...q } }),
      remove: (id: string) => client.request<void>(`/media/${encodeURIComponent(id)}`, { method: "DELETE", tenant: true }),
      createAutoReel: (body: AutoReelInput, o?: IdemOptions) =>
        client.request<VideoJob>("/media/videos/auto-reels", { method: "POST", body, tenant: true, idempotent: idem(o) }),
      video: (id: string) => client.request<VideoJob>(`/media/videos/${encodeURIComponent(id)}`, { tenant: true }),
      videos: () => client.request<{ items: VideoJob[] }>("/media/videos", { tenant: true }),
      cancelVideo: (id: string) =>
        client.request<VideoJob>(`/media/videos/${encodeURIComponent(id)}/cancel`, { method: "POST", tenant: true }),
    },
    studio: {
      create: (body: { asset_ids: string[]; locale: "en" | "ne"; seller_notes?: string | null }, o?: IdemOptions) =>
        client.request<StudioJob>("/studio/jobs", { method: "POST", body, tenant: true, idempotent: idem(o) }),
      job: (id: string) => client.request<StudioJob>(`/studio/jobs/${encodeURIComponent(id)}`, { tenant: true }),
      jobs: (q: { status?: StudioStatus; limit?: number } = {}) =>
        client.request<{ items: StudioJob[] }>("/studio/jobs", { tenant: true, query: { ...q } }),
      apply: (id: string, body: StudioApplyInput) =>
        client.request<ProductDetail>(`/studio/jobs/${encodeURIComponent(id)}/apply`, { method: "POST", body, tenant: true }),
      discard: (id: string) =>
        client.request<void>(`/studio/jobs/${encodeURIComponent(id)}/discard`, { method: "POST", tenant: true }),
      retry: (id: string) =>
        client.request<StudioJob>(`/studio/jobs/${encodeURIComponent(id)}/retry`, { method: "POST", tenant: true }),
    },
    channels: {
      providers: () => client.request<{ items: ChannelProvider[] }>("/channels/providers", { tenant: true }),
      list: () => client.request<{ items: ChannelConnection[] }>("/channels", { tenant: true }),
      connect: (body: { provider: string; redirect_uri: string; reconnect_connection_id?: string | null }) =>
        client.request<{ authorize_url: string }>("/channels/connect", { method: "POST", body, tenant: true }),
      /** API-key channels (WooCommerce). Re-entering keys for the same store URL reconnects it. */
      connectWithKeys: (body: { provider: string; store_url: string; consumer_key: string; consumer_secret: string }) =>
        client.request<ChannelConnection>("/channels/connect-with-keys", { method: "POST", body, tenant: true }),
      callback: (body: { provider: string; state: string; code: string }) =>
        client.request<ChannelConnection>("/channels/oauth/callback", { method: "POST", body, tenant: true }),
      health: (id: string) =>
        client.request<ChannelConnection>(`/channels/${encodeURIComponent(id)}/health`, { method: "POST", tenant: true }),
      /** Queue a check of this channel's live listings against the channel (CHN-012). */
      reconcile: (id: string) =>
        client.request<ChannelConnection>(`/channels/${encodeURIComponent(id)}/reconcile`, { method: "POST", tenant: true }),
      disconnect: (id: string) =>
        client.request<void>(`/channels/${encodeURIComponent(id)}`, { method: "DELETE", tenant: true }),
    },
    content: {
      posts: (q: { from?: string; to?: string; status?: string } = {}) =>
        client.request<{ items: ContentPost[] }>("/content/posts", { tenant: true, query: { ...q } }),
      create: (body: ContentPostInput) => client.request<ContentPost>("/content/posts", { method: "POST", body, tenant: true }),
      fromStudio: (body: { job_id: string; connection_ids: string[]; kind?: PostKind }) =>
        client.request<{ items: ContentPost[] }>("/content/posts/from-studio", { method: "POST", body, tenant: true }),
      update: (id: string, version: number, fields: { caption?: string; hashtags?: string[] }) =>
        client.request<ContentPost>(`/content/posts/${encodeURIComponent(id)}`, {
          method: "PATCH",
          body: { version, ...fields },
          tenant: true,
        }),
      submit: (id: string) => client.request<ContentPost>(`/content/posts/${encodeURIComponent(id)}/submit`, { method: "POST", tenant: true }),
      approve: (id: string) => client.request<ContentPost>(`/content/posts/${encodeURIComponent(id)}/approve`, { method: "POST", tenant: true }),
      reject: (id: string, note?: string) =>
        client.request<ContentPost>(`/content/posts/${encodeURIComponent(id)}/reject`, { method: "POST", body: { note: note ?? null }, tenant: true }),
      /** `at` is a UTC ISO string; omit to publish now. */
      schedule: (id: string, at?: string | null) =>
        client.request<ContentPost>(`/content/posts/${encodeURIComponent(id)}/schedule`, {
          method: "POST",
          body: at ? { at } : {},
          tenant: true,
        }),
      unschedule: (id: string) => client.request<ContentPost>(`/content/posts/${encodeURIComponent(id)}/unschedule`, { method: "POST", tenant: true }),
      cancel: (id: string) => client.request<ContentPost>(`/content/posts/${encodeURIComponent(id)}/cancel`, { method: "POST", tenant: true }),
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
