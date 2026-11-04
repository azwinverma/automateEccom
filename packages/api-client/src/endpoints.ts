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
  AdminAuditEntry,
  AdminFeatureFlag,
  AdminMerchantDetail,
  AdminMerchantSummary,
  AdminOutboxEvent,
  AdminOverride,
  AdminOverrideInput,
  AdminProviderHealth,
  AdminWebhookEvent,
  AddressInput,
  CodSummary,
  BookShipmentInput,
  CodAwaiting,
  CodOverview,
  CodSettlement,
  CourierAccount,
  CourierOptions,
  CourierProvider,
  DeliveryFeeQuote,
  DeliveryFeeRule,
  FailureReason,
  FulfillmentSettings,
  PickupAddress,
  Shipment,
  ShipmentBucket,
  ShipmentLabel,
  ShipmentStatus,
  ConversationDetail,
  ConversationSummary,
  Customer,
  CustomerAddress,
  CustomerDetail,
  CustomerSegment,
  InboxMessage,
  InventoryLocation,
  LedgerEntry,
  LowStockItem,
  ManualPaymentMethod,
  NepalReference,
  OrderDetail,
  OrderEvent,
  OrderInput,
  OrderStatus,
  OrderSummary,
  Payment,
  ProductStock,
  StockLevel,
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
    reference: {
      nepal: () => client.request<NepalReference>("/reference/nepal", { auth: false }),
    },
    customers: {
      list: (q: { q?: string; segment?: CustomerSegment; limit?: number; cursor?: string } = {}) =>
        client.request<Page<Customer>>("/customers", { tenant: true, query: { ...q } }),
      get: (id: string) => client.request<CustomerDetail>(`/customers/${encodeURIComponent(id)}`, { tenant: true }),
      create: (body: { display_name: string; phone?: string | null; email?: string | null; notes?: string | null }) =>
        client.request<CustomerDetail>("/customers", { method: "POST", body, tenant: true }),
      update: (id: string, body: { display_name?: string; phone?: string | null; email?: string | null; notes?: string | null; tags?: string[] }) =>
        client.request<CustomerDetail>(`/customers/${encodeURIComponent(id)}`, { method: "PATCH", body, tenant: true }),
      addAddress: (id: string, body: AddressInput) =>
        client.request<CustomerAddress>(`/customers/${encodeURIComponent(id)}/addresses`, { method: "POST", body, tenant: true }),
      removeAddress: (id: string, addressId: string) =>
        client.request<void>(`/customers/${encodeURIComponent(id)}/addresses/${encodeURIComponent(addressId)}`, { method: "DELETE", tenant: true }),
      /** Merge `sourceId` into `id` (identities, addresses, orders and chats move to `id`). */
      merge: (id: string, sourceId: string) =>
        client.request<CustomerDetail>(`/customers/${encodeURIComponent(id)}/merge`, { method: "POST", body: { source_id: sourceId }, tenant: true }),
    },
    inventory: {
      locations: () => client.request<{ items: InventoryLocation[] }>("/inventory/locations", { tenant: true }),
      createLocation: (body: { name: string; district?: string | null }) =>
        client.request<InventoryLocation>("/inventory/locations", { method: "POST", body, tenant: true }),
      productStock: (productId: string) =>
        client.request<ProductStock>(`/catalog/products/${encodeURIComponent(productId)}/stock`, { tenant: true }),
      receive: (variantId: string, body: { quantity: number; location_id?: string | null; reason?: string | null }, o?: IdemOptions) =>
        client.request<StockLevel>(`/inventory/variants/${encodeURIComponent(variantId)}/receive`, { method: "POST", body, tenant: true, idempotent: idem(o) }),
      adjust: (variantId: string, body: { delta: number; reason: string; location_id?: string | null }, o?: IdemOptions) =>
        client.request<StockLevel>(`/inventory/variants/${encodeURIComponent(variantId)}/adjust`, { method: "POST", body, tenant: true, idempotent: idem(o) }),
      count: (variantId: string, body: { counted: number; location_id?: string | null }) =>
        client.request<StockLevel>(`/inventory/variants/${encodeURIComponent(variantId)}/count`, { method: "POST", body, tenant: true }),
      setThreshold: (variantId: string, threshold: number | null, locationId?: string | null) =>
        client.request<StockLevel>(`/inventory/variants/${encodeURIComponent(variantId)}/threshold`, { method: "PUT", body: { threshold, location_id: locationId ?? null }, tenant: true }),
      ledger: (variantId: string, q: { limit?: number; cursor?: string } = {}) =>
        client.request<Page<LedgerEntry>>(`/inventory/variants/${encodeURIComponent(variantId)}/ledger`, { tenant: true, query: { ...q } }),
      lowStock: () => client.request<{ items: LowStockItem[] }>("/inventory/low-stock", { tenant: true }),
    },
    orders: {
      list: (q: { status?: string; q?: string; customer_id?: string; needs_review?: boolean; limit?: number; cursor?: string } = {}) =>
        client.request<Page<OrderSummary>>("/orders", { tenant: true, query: { ...q } }),
      get: (id: string) => client.request<OrderDetail>(`/orders/${encodeURIComponent(id)}`, { tenant: true }),
      create: (body: OrderInput, o?: IdemOptions) =>
        client.request<OrderDetail>("/orders", { method: "POST", body, tenant: true, idempotent: idem(o) }),
      transition: (id: string, to: OrderStatus, opts: { reason?: string; expected_version?: number } = {}) =>
        client.request<OrderDetail>(`/orders/${encodeURIComponent(id)}/transition`, { method: "POST", body: { to, ...opts }, tenant: true }),
      cancelLines: (id: string, items: { line_id: string; quantity: number }[], reason: string) =>
        client.request<OrderDetail>(`/orders/${encodeURIComponent(id)}/cancel-lines`, { method: "POST", body: { items, reason }, tenant: true }),
      addNote: (id: string, note: string) =>
        client.request<{ id: string }>(`/orders/${encodeURIComponent(id)}/notes`, { method: "POST", body: { note }, tenant: true }),
      timeline: (id: string) => client.request<{ items: OrderEvent[] }>(`/orders/${encodeURIComponent(id)}/timeline`, { tenant: true }),
      payments: (id: string) => client.request<{ items: Payment[] }>(`/orders/${encodeURIComponent(id)}/payments`, { tenant: true }),
      startOnlinePayment: (id: string) =>
        client.request<Payment>(`/orders/${encodeURIComponent(id)}/payments/online`, { method: "POST", body: {}, tenant: true }),
      /** Payment made outside Nivaro (bank transfer, eSewa/Khalti to the shop's own account). Needs the exact total. */
      recordPayment: (id: string, body: { amount_minor: number; method: ManualPaymentMethod; reference?: string | null }, o?: IdemOptions) =>
        client.request<Payment>(`/orders/${encodeURIComponent(id)}/payments/manual`, { method: "POST", body, tenant: true, idempotent: idem(o) }),
      switchToCod: (id: string) => client.request<OrderDetail>(`/orders/${encodeURIComponent(id)}/switch-to-cod`, { method: "POST", tenant: true }),
      verifyPayment: (paymentId: string) =>
        client.request<Payment>(`/payments/${encodeURIComponent(paymentId)}/verify`, { method: "POST", tenant: true }),
      codSummary: () => client.request<CodSummary>("/payments/cod/summary", { tenant: true }),
    },
    inbox: {
      conversations: (q: { status?: "open" | "snoozed" | "closed" | "all"; assigned?: "me" | "unassigned"; escalated?: boolean; limit?: number; cursor?: string } = {}) =>
        client.request<Page<ConversationSummary>>("/conversations", { tenant: true, query: { ...q } }),
      conversation: (id: string) => client.request<ConversationDetail>(`/conversations/${encodeURIComponent(id)}`, { tenant: true }),
      messages: (id: string, q: { limit?: number; cursor?: string } = {}) =>
        client.request<Page<InboxMessage>>(`/conversations/${encodeURIComponent(id)}/messages`, { tenant: true, query: { ...q } }),
      reply: (id: string, text: string) =>
        client.request<InboxMessage>(`/conversations/${encodeURIComponent(id)}/messages`, { method: "POST", body: { text }, tenant: true }),
      approve: (messageId: string, text?: string | null) =>
        client.request<InboxMessage>(`/messages/${encodeURIComponent(messageId)}/approve`, { method: "POST", body: { text: text ?? null }, tenant: true }),
      discard: (messageId: string) => client.request<void>(`/messages/${encodeURIComponent(messageId)}/discard`, { method: "POST", tenant: true }),
      retry: (messageId: string) => client.request<InboxMessage>(`/messages/${encodeURIComponent(messageId)}/retry`, { method: "POST", tenant: true }),
      assign: (id: string, userId: string | null) =>
        client.request<ConversationDetail>(`/conversations/${encodeURIComponent(id)}/assign`, { method: "POST", body: { user_id: userId }, tenant: true }),
      update: (id: string, body: { status?: "open" | "snoozed" | "closed"; labels?: string[]; human_handoff?: boolean }) =>
        client.request<ConversationDetail>(`/conversations/${encodeURIComponent(id)}`, { method: "PATCH", body, tenant: true }),
      markRead: (id: string) => client.request<ConversationSummary>(`/conversations/${encodeURIComponent(id)}/read`, { method: "POST", tenant: true }),
      summary: (id: string) => client.request<{ summary: string; at: string }>(`/conversations/${encodeURIComponent(id)}/summary`, { method: "POST", tenant: true }),
    },
    couriers: {
      providers: () => client.request<{ items: CourierProvider[] }>("/couriers/providers", { tenant: true }),
      list: () => client.request<{ items: CourierAccount[] }>("/couriers", { tenant: true }),
      connect: (body: { provider: string; display_name?: string | null; credentials?: Record<string, string>; pickup?: Partial<PickupAddress>; is_default?: boolean }) =>
        client.request<CourierAccount>("/couriers", { method: "POST", body, tenant: true }),
      update: (id: string, body: { display_name?: string; pickup?: Partial<PickupAddress>; is_default?: boolean }) =>
        client.request<CourierAccount>(`/couriers/${encodeURIComponent(id)}`, { method: "PATCH", body, tenant: true }),
      disconnect: (id: string) => client.request<void>(`/couriers/${encodeURIComponent(id)}`, { method: "DELETE", tenant: true }),
      /** Rule-based options for an order (default courier, else cheapest that can collect COD). */
      rates: (orderId: string, weightGrams?: number | null) =>
        client.request<CourierOptions>("/couriers/rates", { tenant: true, query: { order_id: orderId, weight_grams: weightGrams ?? undefined } }),
      settings: () => client.request<FulfillmentSettings>("/fulfillment/settings", { tenant: true }),
      updateSettings: (body: Partial<FulfillmentSettings>) =>
        client.request<FulfillmentSettings>("/fulfillment/settings", { method: "PATCH", body, tenant: true }),
      feeRules: () => client.request<{ items: DeliveryFeeRule[] }>("/fulfillment/delivery-fees", { tenant: true }),
      saveFeeRules: (rules: DeliveryFeeRule[]) =>
        client.request<{ items: DeliveryFeeRule[] }>("/fulfillment/delivery-fees", { method: "PUT", body: { rules }, tenant: true }),
      quoteFee: (district: string, subtotalMinor = 0) =>
        client.request<{ quote: DeliveryFeeQuote | null }>("/fulfillment/delivery-fee", { tenant: true, query: { district, subtotal_minor: subtotalMinor } }),
    },
    shipments: {
      list: (q: { bucket?: ShipmentBucket; courier_account_id?: string; q?: string; limit?: number; cursor?: string } = {}) =>
        client.request<Page<Shipment> & { counts: Record<ShipmentBucket, number> }>("/shipments", { tenant: true, query: { ...q } }),
      get: (id: string) => client.request<Shipment>(`/shipments/${encodeURIComponent(id)}`, { tenant: true }),
      forOrder: (orderId: string) => client.request<{ items: Shipment[] }>(`/orders/${encodeURIComponent(orderId)}/shipments`, { tenant: true }),
      book: (orderId: string, body: BookShipmentInput, o?: IdemOptions) =>
        client.request<Shipment>(`/orders/${encodeURIComponent(orderId)}/shipments`, { method: "POST", body, tenant: true, idempotent: idem(o) }),
      label: (id: string) => client.request<ShipmentLabel>(`/shipments/${encodeURIComponent(id)}/label`, { tenant: true }),
      requestPickup: (shipmentIds: string[]) =>
        client.request<{ items: Shipment[] }>("/shipments/pickup", { method: "POST", body: { shipment_ids: shipmentIds }, tenant: true }),
      cancel: (id: string, reason?: string | null) =>
        client.request<Shipment>(`/shipments/${encodeURIComponent(id)}/cancel`, { method: "POST", body: { reason: reason ?? null }, tenant: true }),
      refresh: (id: string) => client.request<Shipment>(`/shipments/${encodeURIComponent(id)}/refresh`, { method: "POST", tenant: true }),
      setStatus: (id: string, body: { status: ShipmentStatus; failure_reason?: FailureReason | null; note?: string | null }) =>
        client.request<Shipment>(`/shipments/${encodeURIComponent(id)}/status`, { method: "POST", body, tenant: true }),
      setTracking: (id: string, body: { tracking_number: string; courier_name?: string | null }) =>
        client.request<Shipment>(`/shipments/${encodeURIComponent(id)}/tracking`, { method: "POST", body, tenant: true }),
      reattempt: (id: string, body: { note?: string | null; address?: AddressInput | null }) =>
        client.request<Shipment>(`/shipments/${encodeURIComponent(id)}/reattempt`, { method: "POST", body, tenant: true }),
      returnToSender: (id: string, reason?: string | null) =>
        client.request<Shipment>(`/shipments/${encodeURIComponent(id)}/return`, { method: "POST", body: { reason: reason ?? null }, tenant: true }),
      receivedBack: (id: string) => client.request<Shipment>(`/shipments/${encodeURIComponent(id)}/received-back`, { method: "POST", tenant: true }),
    },
    cod: {
      overview: () => client.request<CodOverview>("/cod/overview", { tenant: true }),
      awaiting: (courierAccountId?: string) =>
        client.request<{ items: CodAwaiting[] }>("/cod/awaiting", { tenant: true, query: { courier_account_id: courierAccountId } }),
      settlements: (status?: CodSettlement["status"]) =>
        client.request<{ items: CodSettlement[] }>("/cod/settlements", { tenant: true, query: { status } }),
      settlement: (id: string) => client.request<CodSettlement>(`/cod/settlements/${encodeURIComponent(id)}`, { tenant: true }),
      /** A courier statement saved as CSV (amounts in rupees). Same reference twice returns the first import. */
      importFile: (courierAccountId: string, reference: string, file: Blob, fileName = "statement.csv") => {
        const form = new FormData();
        form.append("courier_account_id", courierAccountId);
        form.append("reference", reference);
        form.append("file", file, fileName);
        return client.request<CodSettlement>("/cod/settlements/import", { method: "POST", body: form, tenant: true });
      },
      recordCash: (body: { courier_account_id: string; shipment_ids: string[]; reference?: string | null }) =>
        client.request<CodSettlement>("/cod/settlements/cash", { method: "POST", body, tenant: true }),
      recheck: (id: string) => client.request<CodSettlement>(`/cod/settlements/${encodeURIComponent(id)}/recheck`, { method: "POST", tenant: true }),
      acceptLine: (lineId: string, reason: string) =>
        client.request<CodSettlement>(`/cod/settlement-lines/${encodeURIComponent(lineId)}/accept`, { method: "POST", body: { reason }, tenant: true }),
      confirm: (id: string, bankReference?: string | null) =>
        client.request<CodSettlement>(`/cod/settlements/${encodeURIComponent(id)}/confirm`, { method: "POST", body: { bank_reference: bankReference ?? null }, tenant: true }),
    },
    /** Development only (404 in staging/production): drive the sandbox courier. */
    devCourier: {
      simulate: (accountId: string, body: { tracking_number: string; status: ShipmentStatus; failure_reason?: FailureReason | null }) =>
        client.request<{ accepted: number }>(`/_dev/couriers/sandbox/${encodeURIComponent(accountId)}/simulate`, { method: "POST", body, tenant: true }),
      settlement: (accountId: string, body: { fee_minor?: number; short_minor?: number; extra_unknown?: boolean } = {}) =>
        client.request<{ imported: number; settlement: CodSettlement | null }>(`/_dev/couriers/sandbox/${encodeURIComponent(accountId)}/settlement`, { method: "POST", body, tenant: true }),
    },
    /** Nivaro Console. Staff + MFA-verified session only; never tenant-scoped; every write is audited. */
    admin: {
      merchants: (q: { q?: string; limit?: number } = {}) =>
        client.request<{ items: AdminMerchantSummary[] }>("/admin/merchants", { query: { ...q } }),
      merchant: (id: string) => client.request<AdminMerchantDetail>(`/admin/merchants/${encodeURIComponent(id)}`),
      setStatus: (id: string, status: "active" | "suspended", reason: string) =>
        client.request<{ id: string; status: string }>(`/admin/merchants/${encodeURIComponent(id)}/status`, {
          method: "POST",
          body: { status, reason },
        }),
      createOverride: (id: string, body: AdminOverrideInput) =>
        client.request<AdminOverride>(`/admin/merchants/${encodeURIComponent(id)}/overrides`, { method: "POST", body }),
      endOverride: (id: string, overrideId: string) =>
        client.request<void>(`/admin/merchants/${encodeURIComponent(id)}/overrides/${encodeURIComponent(overrideId)}`, {
          method: "DELETE",
        }),
      grantCredits: (id: string, body: { amount: number; reason: string; idempotency_key: string }) =>
        client.request<{ transaction_id: string; balance: number }>(`/admin/merchants/${encodeURIComponent(id)}/credits`, {
          method: "POST",
          body,
        }),
      audit: (q: { merchant_id?: string; actor_type?: string; action?: string; limit?: number; cursor?: string } = {}) =>
        client.request<{ items: AdminAuditEntry[]; next_cursor: string | null }>("/admin/audit-logs", { query: { ...q } }),
      webhooks: (q: { status?: string; provider?: string; limit?: number } = {}) =>
        client.request<{ items: AdminWebhookEvent[] }>("/admin/webhooks", { query: { ...q } }),
      replayWebhook: (id: string) =>
        client.request<{ id: string; status: string }>(`/admin/webhooks/${encodeURIComponent(id)}/replay`, { method: "POST" }),
      outbox: (status: "pending" | "dispatched" | "dead" = "dead") =>
        client.request<{ items: AdminOutboxEvent[] }>("/admin/outbox", { query: { status } }),
      retryOutbox: (id: string) =>
        client.request<{ id: string; status: string }>(`/admin/outbox/${encodeURIComponent(id)}/retry`, { method: "POST" }),
      providers: () => client.request<{ items: AdminProviderHealth[] }>("/admin/ai/providers"),
      flags: () => client.request<{ items: AdminFeatureFlag[] }>("/admin/feature-flags"),
      upsertFlag: (key: string, body: Omit<AdminFeatureFlag, "key">) =>
        client.request<AdminFeatureFlag>(`/admin/feature-flags/${encodeURIComponent(key)}`, { method: "PUT", body }),
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
