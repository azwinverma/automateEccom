/**
 * Types for the Phase 0 API contract (docs/api/phase-0-contract.md).
 * Fields the contract does not pin down are typed as optional and documented
 * where we made an assumption.
 */

export type Locale = "en" | "ne";
export type Role = "owner" | "admin" | "manager" | "staff" | "viewer";
export const ROLES: readonly Role[] = ["owner", "admin", "manager", "staff", "viewer"] as const;

export interface Money {
  amount_minor: number;
  currency: string;
}

export interface Page<T> {
  items: T[];
  next_cursor: string | null;
}

/* ---------- Auth ---------- */

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  session_id: string;
}

export interface MfaChallenge {
  mfa_required: true;
  mfa_token: string;
}

export type LoginResponse = TokenPair | MfaChallenge;

export function isMfaChallenge(r: unknown): r is MfaChallenge {
  return typeof r === "object" && r !== null && (r as { mfa_required?: unknown }).mfa_required === true;
}

export interface RegisterInput {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
  locale?: Locale;
}

export interface LoginInput {
  email: string;
  password: string;
  device_name?: string;
}

export interface MfaVerifyInput {
  mfa_token: string;
  code: string;
}

export interface Session {
  id: string;
  device_name: string | null;
  ip: string | null;
  user_agent: string | null;
  created_at: string;
  last_used_at: string | null;
  current: boolean;
}

export interface TotpSetup {
  secret: string;
  otpauth_uri: string;
}

export interface RecoveryCodes {
  recovery_codes: string[];
}

/* ---------- Me ---------- */

export interface User {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  locale: Locale;
  email_verified: boolean;
  mfa_enabled: boolean;
  /** Platform staff may open the Nivaro Console (it also needs an MFA-verified session). */
  is_platform_staff?: boolean;
}

export interface MerchantRef {
  id: string;
  name: string;
  slug: string;
}

export type MembershipStatus = "active" | "invited" | "suspended" | (string & {});

export interface Membership {
  merchant: MerchantRef;
  role: Role;
  status: MembershipStatus;
}

export interface Me {
  user: User;
  memberships: Membership[];
  /** The current sign-in; `mfa` = it passed two-step verification. */
  session?: { mfa: boolean } | null;
}

export interface UpdateMeInput {
  full_name?: string;
  phone?: string;
  locale?: Locale;
}

/* ---------- Merchants / stores ---------- */

export interface CreateMerchantInput {
  name: string;
  slug?: string;
  country: "NP";
  currency: string;
  timezone: string;
  default_locale: Locale;
}

export interface Merchant extends MerchantRef {
  country?: string;
  currency?: string;
  timezone?: string;
  default_locale?: Locale;
  created_at?: string;
}

export interface Store {
  id: string;
  name: string;
  slug: string;
  status: "active" | "archived";
  default_currency: string;
  created_at: string;
}

/* ---------- Team ---------- */

export interface Member {
  id: string;
  user: { id: string; email: string; full_name: string };
  role: Role;
  status: MembershipStatus;
  joined_at: string | null;
}

/** Assumed shape — the contract only names the endpoint. */
export interface Invitation {
  id: string;
  email: string;
  role: Role;
  status?: "pending" | "accepted" | "revoked" | "expired" | (string & {});
  created_at?: string;
  expires_at?: string | null;
}

/** Assumed shape for GET /permissions/me. */
export interface EffectivePermissions {
  permissions: string[];
}

/* ---------- Billing ---------- */

export interface Subscription {
  plan: { code: string; name: string; tagline: string | null };
  plan_version: number | string;
  status: "trialing" | "active" | "past_due" | "canceled" | (string & {});
  trial_ends_at: string | null;
  current_period_start: string;
  current_period_end: string;
}

export type AlertLevel = "70" | "85" | "100";

export type OveragePolicy = "block" | "credits" | "overage";
export type UsageKind = "consumable" | "gauge";

export interface UsageLimit {
  resource: string;
  period: "month" | "day" | "lifetime" | (string & {});
  /** `null` = unlimited. */
  limit: number | null;
  /** `null` = not counted yet (gauges the backend can't count). Never treat as 0. */
  used: number | null;
  reserved: number;
  burst?: { period: string; limit: number | null; used: number } | null;
  alert_level: AlertLevel | null;
  /** false when the plan's limit is 0 (resource not part of the plan). */
  included?: boolean;
  kind?: UsageKind;
  overage_policy?: OveragePolicy;
}

export interface Entitlements {
  features: Record<string, boolean>;
  limits: UsageLimit[];
}

export type CreditTransactionKind =
  | "grant"
  | "purchase"
  | "hold"
  | "release"
  | "consume"
  | "refund"
  | "expire"
  | "adjustment";

export interface CreditTransaction {
  id: string;
  amount: number;
  balance_after?: number | null;
  kind?: CreditTransactionKind | (string & {});
  reference_type?: string | null;
  created_at?: string;
}

export interface Credits {
  balance: number;
  currency: "credits";
  transactions: CreditTransaction[];
}

/* ---------- Audit ---------- */

export type ActorType = "user" | "system" | "automation" | "ai";

export interface AuditLogEntry {
  id: string;
  occurred_at: string;
  actor: { type: ActorType; id: string | null; display: string | null };
  action: string;
  resource_type: string;
  resource_id: string | null;
  source: string | null;
  request_id: string | null;
  ip: string | null;
  /** Diff format not pinned: `{field: {old,new}}`, `{field: [old,new]}` or `{before,after}`. */
  changes: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
}

export interface AuditLogQuery {
  action?: string;
  actor_id?: string;
  resource_type?: string;
  resource_id?: string;
  limit?: number;
  cursor?: string;
}

/* ---------- Errors ---------- */

export interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown> | null;
    request_id?: string | null;
  };
}

/* ---------- Catalog (Phase 1) ---------- */

export type ProductStatus = "draft" | "active" | "archived";

export interface ProductSummary {
  id: string;
  title: string;
  handle: string;
  status: ProductStatus;
  category_id: string | null;
  version: number;
  updated_at: string;
  variant_count: number;
  price_range: { min_minor: number; max_minor: number; currency: string } | null;
}

export interface ProductListQuery {
  status?: ProductStatus;
  q?: string;
  category_id?: string;
  limit?: number;
  cursor?: string;
}

export interface ProductOption {
  id: string;
  name: string;
  values: string[];
}

export interface VariantDetail {
  id: string;
  title: string;
  sku: string;
  barcode: string | null;
  options: Record<string, string>;
  price: Money;
  compare_at: Money | null;
  cost: Money | null;
  weight_grams: number | null;
  /** [length, width, height] in mm; entries may be null. */
  dimensions_mm: (number | null)[];
  status: "active" | "archived";
  suppliers: unknown[];
}

export type AttributeSource = "seller" | "ai" | "import" | "channel";

export interface ProductAttribute {
  key: string;
  value: string;
  locale: "en" | "ne";
  source: AttributeSource;
  confidence: number | null;
  confirmed: boolean;
}

export interface ProductDetail {
  id: string;
  title: string;
  title_ne: string | null;
  handle: string;
  description: string | null;
  description_ne: string | null;
  status: ProductStatus;
  kind?: string;
  category_id: string | null;
  brand: string | null;
  product_type: string | null;
  tags: string[];
  /** Final-sale items fail the return eligibility check (soft: a manager can override). */
  final_sale?: boolean;
  seo_title: string | null;
  seo_description: string | null;
  version: number;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  options: ProductOption[];
  variants: VariantDetail[];
  attributes: ProductAttribute[];
  collection_ids: string[];
  needs_review: boolean;
}

export interface VariantInput {
  options: Record<string, string>;
  price_minor: number;
  sku?: string;
  barcode?: string;
  compare_at_minor?: number;
  cost_minor?: number;
  weight_grams?: number;
  length_mm?: number;
  width_mm?: number;
  height_mm?: number;
}

export interface ProductCreateInput {
  title: string;
  handle?: string;
  description?: string;
  title_ne?: string;
  description_ne?: string;
  category_id?: string;
  brand?: string;
  product_type?: string;
  tags: string[];
  seo_title?: string;
  seo_description?: string;
  options: { name: string; values: string[] }[];
  variants: VariantInput[];
}

export type ProductPatchInput = Partial<
  Pick<
    ProductCreateInput,
    "title" | "handle" | "description" | "title_ne" | "description_ne" | "brand" | "product_type" | "tags" | "seo_title" | "seo_description"
  >
> & { category_id?: string | null; final_sale?: boolean };

export interface VariantPatchInput {
  price_minor?: number;
  compare_at_minor?: number | null;
  cost_minor?: number | null;
  sku?: string;
  barcode?: string | null;
  weight_grams?: number | null;
  length_mm?: number | null;
  width_mm?: number | null;
  height_mm?: number | null;
}

export type PublishProblem = "title_required" | "active_variant_required" | "price_required" | "unconfirmed_ai_attributes";

export interface Category {
  id: string;
  name: string;
  name_ne: string | null;
  parent_id: string | null;
  /** Slug path, e.g. `clothing/women/kurta`. Items come sorted by path. */
  path: string;
  depth: number;
}

export interface Collection {
  id: string;
  title: string;
  handle: string;
  description: string | null;
}

export type ImportStatus = "queued" | "processing" | "completed" | "completed_with_errors" | "failed";

export interface ImportRowError {
  row: number | null;
  handle?: string | null;
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ImportJob {
  id: string;
  status: ImportStatus;
  file_name: string;
  total_rows: number | null;
  products_created: number;
  products_updated: number;
  rows_failed: number;
  errors: ImportRowError[];
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

/* ---------- Exceptions (Phase 1) ---------- */

export type ExceptionSeverityApi = "urgent" | "high" | "normal";
export type ExceptionAction =
  | "reconnect"
  | "retry_publish"
  | "reschedule"
  | "review_post"
  | "review_draft"
  | "retry_draft"
  | "confirm_attributes"
  | "dismiss";

export interface ExceptionRecord {
  id: string;
  type: string;
  severity: ExceptionSeverityApi;
  resource: { type: "channel_connection" | "product" | "content_post" | "studio_job" | "media" | (string & {}); id: string };
  occurred_at: string | null;
  action: ExceptionAction | (string & {});
  details: Record<string, unknown>;
}

export interface ExceptionList {
  items: ExceptionRecord[];
  counts: Partial<Record<ExceptionSeverityApi, number>>;
  total: number;
}

/* ---------- Media ---------- */

export interface UploadTicket {
  method: "PUT";
  url: string;
  headers: Record<string, string>;
  expires_at: string;
}

export type MediaStatus = "pending_upload" | "uploaded" | "processing" | "ready" | "rejected" | "deleted";

export interface MediaDerivative {
  width: number | null;
  height: number | null;
  content_type: string;
  /** Signed, short-lived. Refetch the asset rather than caching. */
  url: string | null;
}

export interface MediaAsset {
  id: string;
  status: MediaStatus;
  kind: string;
  purpose: string;
  file_name: string;
  width: number | null;
  height: number | null;
  size_bytes: number | null;
  quality_score: number | null;
  quality_flags: string[];
  stripped_location_metadata: boolean | null;
  scan_status: string | null;
  rejection_reason: string | null;
  source: string | null;
  created_at: string;
  derivatives: Record<string, MediaDerivative>;
}

/* ---------- Studio ---------- */

export type StudioStatus = "queued" | "running" | "ready" | "failed" | "applied" | "discarded";

export interface StudioDraft {
  is_product_photo: boolean;
  category: { path: string[]; confidence: number };
  title_en: string;
  title_ne: string;
  description_en: string;
  description_ne: string;
  bullets_en: string[];
  attributes: { key: string; value: string; confidence: number }[];
  colors: string[];
  suggested_options: { name: string; values: string[] }[];
  seo: { title: string; description: string };
  hashtags: string[];
  captions: { instagram: string; facebook: string; tiktok: string };
  needs_seller_input: string[];
  confidence: number;
}

export interface StudioIssue {
  field: string;
  /** `too_long`, `not_a_product_photo`, `truncated`, or `unsupported_claim:<price|discount|stock|delivery|warranty|authenticity>` */
  kind: string;
  excerpt?: string;
}

export interface StudioJob {
  id: string;
  status: StudioStatus;
  asset_ids: string[];
  locale: Locale;
  seller_notes: string | null;
  draft: StudioDraft | null;
  confidence: number | null;
  needs_review: boolean;
  issues: StudioIssue[];
  error_code: string | null;
  attempts: number;
  product_id: string | null;
  ai: { provider: string; model: string; prompt_version: string } | null;
  created_at: string;
  finished_at: string | null;
}

export interface StudioApplyInput {
  product: ProductCreateInput;
  accepted_attribute_keys: string[];
  category_path?: string[] | null;
}

/* ---------- Channels ---------- */

export type ChannelCapability =
  | "product_listing"
  | "inventory_sync"
  | "content_publish"
  | "messages"
  | "orders"
  | "returns"
  | "refunds"
  | "fulfillment";

export interface ChannelProvider {
  code: string;
  name: string;
  sandbox: boolean;
  capabilities: (ChannelCapability | (string & {}))[];
}

export type ConnectionStatus = "connected" | "expired" | "revoked" | "error" | "disconnected";

export interface ChannelConnection {
  id: string;
  provider: string;
  display_name: string;
  status: ConnectionStatus;
  external_account_id: string | null;
  capabilities: (ChannelCapability | (string & {}))[];
  scopes: string[];
  token_expires_at: string | null;
  last_healthy_at: string | null;
  last_error_code: string | null;
  needs_reconnect: boolean;
  created_at: string;
}

export type ListingStatus = "pending" | "publishing" | "published" | "failed" | "out_of_sync" | "unpublished";

export interface ChannelListing {
  id: string;
  connection_id: string;
  product_id: string;
  provider: string | null;
  status: ListingStatus;
  desired_state: "published" | "unpublished" | (string & {});
  external_id: string | null;
  last_error_code: string | null;
  last_synced_at: string | null;
  published_product_version: number | null;
  /** CHN-012: set when the channel's copy differs from Nivaro's. The seller decides which one wins. */
  drift: ListingDrift | null;
  last_reconciled_at: string | null;
}

export type DriftCode = "missing_on_channel" | "hidden_on_channel" | "price_changed" | "variants_changed";

export interface ListingDrift {
  code: DriftCode | (string & {});
  details: {
    prices?: { sku: string; expected_minor: number; channel_minor: number }[];
    missing_skus?: string[];
    extra_skus?: string[];
  };
  detected_at: string | null;
}

/* ---------- Content ---------- */

export type PostStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "scheduled"
  | "publishing"
  | "published"
  | "failed"
  | "cancelled";
export type PostKind = "post" | "story" | "reel";

export interface ContentPost {
  id: string;
  connection_id: string;
  product_id: string | null;
  kind: PostKind;
  caption: string;
  hashtags: string[];
  asset_ids: string[];
  campaign: string | null;
  source: "seller" | "ai_studio" | "ai_schedule" | (string & {});
  status: PostStatus;
  issues: StudioIssue[];
  scheduled_at: string | null;
  published_at: string | null;
  external_id: string | null;
  attempts: number;
  last_error_code: string | null;
  approved_at: string | null;
  rejection_note: string | null;
  version: number;
  created_at: string;
}

export interface ContentPostInput {
  connection_id: string;
  caption: string;
  hashtags: string[];
  asset_ids: string[];
  kind: PostKind;
  product_id?: string | null;
  campaign?: string | null;
}

/* ---------- Auto Reels ---------- */

export type ReelAspect = "9:16" | "1:1" | "4:5" | "16:9";
export type VideoStatus = "queued" | "generating" | "post_processing" | "ready" | "failed" | "cancelled";

export interface AutoReelInput {
  asset_ids: string[];
  aspect: ReelAspect;
  locale: Locale;
  headline?: string | null;
  cta?: string | null;
  product_id?: string | null;
  show_price: boolean;
  seconds_per_slide: number;
}

export interface VideoJob {
  id: string;
  kind: string;
  status: VideoStatus;
  aspect: ReelAspect;
  asset_ids: string[];
  headline: string | null;
  cta: string | null;
  show_price: boolean;
  product_id: string | null;
  duration_s: number | null;
  credits_charged: number | null;
  error_code: string | null;
  output: MediaAsset | null;
  created_at: string;
  finished_at: string | null;
}

/* ---------- Nivaro Console (staff only) ---------- */

export interface AdminMerchantSummary {
  id: string;
  name: string;
  slug: string;
  status: "active" | "suspended" | "closed" | (string & {});
  created_at: string;
}

export interface AdminOverride {
  id: string;
  resource_code: string | null;
  feature_code: string | null;
  enabled: boolean | null;
  period: string | null;
  limit_value: number | null;
  reason: string;
  expires_at: string | null;
  created_at: string;
  active: boolean;
}

export interface AdminMerchantDetail {
  merchant: AdminMerchantSummary & { country: string; currency: string; timezone: string; default_locale: string };
  members: number;
  team: { user_id: string; email: string; full_name: string; role: string; status: string; mfa_enabled: boolean; last_login_at: string | null }[];
  plan: string | null;
  subscription_status: string | null;
  usage: UsageLimit[];
  credit_balance: number;
  connections: {
    id: string;
    provider: string;
    display_name: string;
    status: string;
    last_healthy_at: string | null;
    last_error_code: string | null;
    consecutive_failures: number;
    token_expires_at: string | null;
  }[];
  overrides: AdminOverride[];
}

export interface AdminOverrideInput {
  resource_code: string;
  period: "month" | "day" | "lifetime";
  limit_value: number;
  reason: string;
  expires_at?: string | null;
}

export interface AdminAuditEntry {
  id: string;
  merchant_id: string | null;
  occurred_at: string;
  actor: { type: string; id: string | null; display: string | null };
  action: string;
  resource_type: string;
  resource_id: string | null;
  request_id: string | null;
  changes: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
}

export interface AdminWebhookEvent {
  id: string;
  provider: string;
  event_type: string;
  status: "received" | "processed" | "ignored" | "failed" | "dead" | (string & {});
  merchant_id: string | null;
  attempts: number;
  duplicates: number;
  last_error: string | null;
  received_at: string;
}

export interface AdminOutboxEvent {
  id: string;
  event_type: string;
  merchant_id: string | null;
  status: "pending" | "dispatched" | "dead" | (string & {});
  attempts: number;
  last_error: string | null;
  created_at: string;
  available_at: string;
}

export interface AdminProviderHealth {
  provider: string;
  model: string;
  /** Has a key (or is the dev sandbox) so it can actually be called. */
  configured: boolean;
  state: "closed" | "open" | "half_open" | "unknown" | (string & {});
  success_rate_1h?: number | null;
  attempts_1h?: number;
  last_latency_ms?: number | null;
}

export interface AdminFeatureFlag {
  key: string;
  description: string;
  default_enabled: boolean;
  rollout_percentage: number;
  kill_switch: boolean;
}

/* ---------- Phase 2: customers ---------- */

export interface NepalReference {
  provinces: { code: string; name: string; name_ne: string }[];
  districts: { code: string; name: string; province: string }[];
  max_ward: number;
}

export interface AddressInput {
  recipient_name: string;
  phone: string;
  province?: string;
  district: string;
  municipality: string;
  ward: number;
  area?: string | null;
  landmark?: string | null;
  label?: string | null;
  is_default?: boolean;
}

export interface CustomerAddress extends Required<Omit<AddressInput, "label" | "is_default" | "province">> {
  id: string;
  label: string | null;
  province: string;
  district_name: string;
  completeness: number;
  is_default: boolean;
}

export interface Customer {
  id: string;
  display_name: string;
  phone: string | null;
  email: string | null;
  locale: string | null;
  tags: string[];
  last_seen_at: string | null;
  created_at: string;
}

export interface CustomerDetail extends Customer {
  notes: string | null;
  identities: { provider: string; external_id: string; display_name: string | null }[];
  addresses: CustomerAddress[];
}

export type CustomerSegment = "new" | "repeat" | "inactive";

/* ---------- Phase 2: inventory ---------- */

export interface InventoryLocation {
  id: string;
  name: string;
  code: string;
  district: string | null;
  is_default: boolean;
}

export interface StockLevel {
  variant_id: string;
  location_id: string;
  on_hand: number;
  reserved: number;
  damaged: number;
  available: number;
  low_stock_threshold: number | null;
}

export interface VariantStock {
  variant_id: string;
  title: string;
  sku: string | null;
  /** False until stock is first recorded: untracked variants never block orders. */
  tracked: boolean;
  on_hand: number;
  reserved: number;
  available: number;
  locations: (Omit<StockLevel, "variant_id"> & { location: string | null; low: boolean })[];
}

export interface ProductStock {
  product_id: string;
  variants: VariantStock[];
}

export interface LedgerEntry {
  id: string;
  kind: "receive" | "adjust" | "count" | "damage" | "reserve" | "release" | "commit" | "return_to_stock" | "transfer_out" | "transfer_in";
  location_id: string;
  on_hand_delta: number;
  reserved_delta: number;
  damaged_delta: number;
  on_hand_after: number;
  reserved_after: number;
  reason: string | null;
  reference: { type: string; id: string } | null;
  actor_type: string;
  created_at: string;
}

export interface LowStockItem extends StockLevel {
  product_id: string;
  product_title: string;
  variant_title: string;
  sku: string | null;
}

/* ---------- Phase 2: orders & payments ---------- */

export type OrderStatus =
  | "draft"
  | "pending_confirmation"
  | "confirmed"
  | "payment_pending"
  | "cod_pending"
  | "ready_to_ship"
  | "shipped"
  | "delivered"
  | "completed"
  | "cancelled"
  | "delivery_failed"
  | "returned";

export type PaymentStatusApi = "unpaid" | "pending" | "paid" | "failed" | "refunded" | "cod_pending" | "cod_collected";
export type OrderReview = "unmatched_items" | "stock_short" | "address_incomplete" | "payment_mismatch" | "paid_after_cancel";

export interface OrderSummary {
  id: string;
  number: number;
  status: OrderStatus;
  source: "chat" | "seller" | "channel" | "api";
  external_number: string | null;
  connection_id: string | null;
  customer: { id: string; display_name: string; phone: string | null } | null;
  currency: string;
  total: Money;
  payment_method: "cod" | "prepaid" | "none";
  payment_status: PaymentStatusApi;
  needs_review: OrderReview | (string & {}) | null;
  placed_at: string;
  updated_at: string;
  version: number;
  allowed_transitions: OrderStatus[];
}

export interface OrderLine {
  id: string;
  product_id: string | null;
  variant_id: string | null;
  sku: string | null;
  title: string;
  variant_title: string | null;
  unit_price: Money;
  quantity: number;
  cancelled_quantity: number;
  line_total: Money;
  matched: boolean;
}

export interface OrderDetail extends OrderSummary {
  lines: OrderLine[];
  totals: { subtotal: Money; discount: Money; delivery_fee: Money; tax: Money; total: Money };
  shipping: {
    recipient_name: string | null;
    phone: string | null;
    province: string | null;
    district: string | null;
    district_name: string | null;
    municipality: string | null;
    ward: number | null;
    area: string | null;
    landmark: string | null;
    text: string | null;
    completeness: number;
  };
  notes: string | null;
  cancel_reason: string | null;
  conversation_id: string | null;
  confirmed_at: string | null;
  cancelled_at: string | null;
}

export interface OrderEvent {
  id: string;
  kind: string;
  from_status: OrderStatus | null;
  to_status: OrderStatus | null;
  actor: { type: string; id: string | null; display: string | null };
  automated: boolean;
  source: string;
  provider: string | null;
  data: Record<string, unknown>;
  at: string;
}

export interface OrderInput {
  lines: { variant_id: string; quantity: number; unit_price_minor?: number | null }[];
  customer_id?: string | null;
  customer_name?: string | null;
  customer_phone?: string | null;
  address?: AddressInput | null;
  address_id?: string | null;
  payment_method?: "cod" | "prepaid";
  delivery_fee_minor?: number;
  discount_minor?: number;
  notes?: string | null;
  confirm?: boolean;
}

export interface Payment {
  id: string;
  order_id: string;
  kind: "online" | "manual";
  provider: string;
  method: string | null;
  status: "pending" | "paid" | "failed" | "cancelled" | "needs_review" | "refunded";
  amount: Money;
  paid_minor: number | null;
  redirect_url: string | null;
  reference: string | null;
  failure_code: string | null;
  created_at: string;
  verified_at: string | null;
}

export type ManualPaymentMethod = "bank_transfer" | "esewa" | "khalti" | "fonepay" | "cash" | "other";

export interface CodSummary {
  outstanding: { count: number; amount_minor: number };
  pending_settlement: { count: number; amount_minor: number };
  settled: { count: number; amount_minor: number };
  failed_delivery: { count: number; amount_minor: number };
  return_exposure: { count: number; amount_minor: number };
}

/* ---------- Phase 2: inbox ---------- */

export interface ConversationSummary {
  id: string;
  provider: string;
  connection_id: string | null;
  status: "open" | "snoozed" | "closed";
  customer: { id: string; display_name: string; phone: string | null } | null;
  assigned_user_id: string | null;
  labels: string[];
  last_intent: string | null;
  human_handoff: boolean;
  escalated: boolean;
  escalation_reason: string | null;
  unread_count: number;
  locale: string;
  last_message_at: string | null;
  first_response_due_at: string | null;
  last_message: { text: string; direction: "in" | "out"; status: string } | null;
}

export interface ConversationDetail extends ConversationSummary {
  ai_summary: string | null;
  ai_summary_at: string | null;
  order_draft: {
    id: string;
    status: "collecting" | "awaiting_confirmation" | "confirmed" | "abandoned";
    fields: Record<string, unknown>;
    awaiting_field: string | null;
    order_id: string | null;
  } | null;
}

export interface InboxMessage {
  id: string;
  direction: "in" | "out";
  author_type: "customer" | "seller" | "ai" | "system";
  author_user_id: string | null;
  text: string;
  status: "received" | "suggested" | "queued" | "sent" | "failed" | "discarded";
  intent: string | null;
  confidence: number | null;
  /** What the AI looked up to write this (get_price, get_inventory, get_order, create_order…). */
  grounding: Record<string, unknown>;
  error_code: string | null;
  created_at: string;
  sent_at: string | null;
}

/* ---------- Phase 3: couriers, shipments, COD settlement ---------- */

export interface CourierProvider {
  code: string;
  name: string;
  sandbox: boolean;
  capabilities: string[];
  auth_fields?: string[];
}

export interface PickupAddress {
  name: string | null;
  phone: string | null;
  district: string | null;
  municipality: string | null;
  area: string | null;
}

export interface CourierAccount {
  id: string;
  provider: string;
  display_name: string;
  status: "connected" | "error" | "disconnected";
  is_default: boolean;
  capabilities: string[];
  /** Own rider / courier without an API: the seller records tracking and statuses. */
  manual: boolean;
  pickup: PickupAddress & { district_name: string | null };
  pickup_complete: boolean;
  webhook_path: string | null;
  last_error_code: string | null;
  created_at: string;
}

export interface FulfillmentSettings {
  notify_customers: boolean;
  default_weight_grams: number;
  recovery_wait_hours: number;
  courier_selection: "rules" | "cheapest" | "fastest" | "smart" | "preferred";
}

export type FeeScope = "default" | "inside_valley" | "district";

export interface DeliveryFeeRule {
  scope: FeeScope;
  district: string | null;
  district_name?: string | null;
  fee_minor: number;
  free_over_minor: number | null;
  currency?: string;
}

export interface DeliveryFeeQuote {
  fee_minor: number;
  currency: string;
  rule: FeeScope;
  district: string | null;
  free_delivery: boolean;
  free_over_minor: number | null;
}

export interface CourierOption {
  courier_account_id: string;
  provider: string;
  display_name: string;
  is_default: boolean;
  service_code: string | null;
  price: Money | null;
  eta_days_min: number | null;
  eta_days_max: number | null;
  cod_supported: boolean;
  manual: boolean;
  recommended: boolean;
}

export interface CourierOptions {
  weight_grams: number;
  cod_amount_minor: number;
  options: CourierOption[];
  unavailable: { courier_account_id: string; display_name: string; provider: string; reason: "pickup_address_missing" | "address_incomplete" | "courier_unavailable" }[];
  recommendation: {
    courier_account_id: string;
    service_code: string | null;
    reason: "default_courier" | "cheapest" | "only_option" | "route_history" | "preferred_only";
    method: "rules" | "courier_brain" | (string & {});
    /** Courier Brain: delivery record on this route behind the pick. */
    evidence?: { success_pct: number; n: number; period_days: number; eta_p50_days: number | null; price_above_cheapest_minor: number };
    /** Cold start: not enough finished parcels on this route yet, so the rules picked. */
    note?: "not_enough_route_data";
    min_sample?: number;
  } | null;
}

export type ShipmentStatus =
  | "booked"
  | "pickup_requested"
  | "picked_up"
  | "in_transit"
  | "out_for_delivery"
  | "delivered"
  | "delivery_failed"
  | "reattempt_requested"
  | "returning"
  | "returned_to_origin"
  | "cancelled"
  | "lost";

export type FailureReason =
  | "customer_unreachable"
  | "customer_unavailable"
  | "customer_refused"
  | "address_incorrect"
  | "cod_not_ready"
  | "rescheduled_by_customer"
  | "other";

export type ShipmentAction =
  | "request_pickup"
  | "cancel"
  | "reattempt"
  | "return_to_sender"
  | "confirm_received_back"
  | "update_status"
  | "set_tracking"
  | "refresh";

export interface ShipmentEvent {
  id: string;
  status: ShipmentStatus;
  raw_status: string | null;
  description: string | null;
  location: string | null;
  failure_reason: FailureReason | null;
  source: "courier_webhook" | "courier_poll" | "seller" | "system";
  /** False when the courier's event arrived late (older than the current state): kept as history only. */
  applied: boolean;
  occurred_at: string;
}

export interface DeliveryAttempt {
  id: string;
  attempt_no: number;
  failure_reason: FailureReason;
  failed_at: string;
  recovery_status: "open" | "awaiting_customer" | "customer_replied" | "reattempt_requested" | "returning" | "resolved" | "escalated";
  customer_contacted_at: string | null;
  customer_reply: string | null;
  customer_replied_at: string | null;
  reattempt_requested_at: string | null;
  reattempt_note: string | null;
  reattempt_by: "seller" | "automation" | null;
  escalated_at: string | null;
  resolved_at: string | null;
  resolution: "delivered" | "returned" | "failed_again" | "cancelled" | null;
}

export interface Shipment {
  id: string;
  order_id: string;
  /** "return" = a pickup bringing a returned item back to the shop. */
  direction: "outbound" | "return";
  return_id: string | null;
  order_number: number | null;
  customer_name: string | null;
  destination_district: string | null;
  destination_district_name: string | null;
  courier_account_id: string;
  provider: string;
  courier_name: string;
  manual: boolean;
  service_code: string | null;
  status: ShipmentStatus;
  tracking_number: string | null;
  has_provider_label: boolean;
  weight_grams: number;
  cod_amount: Money;
  charge: Money | null;
  eta_days_min: number | null;
  eta_days_max: number | null;
  attempt_count: number;
  pickup_reference: string | null;
  created_at: string;
  pickup_requested_at: string | null;
  picked_up_at: string | null;
  delivered_at: string | null;
  returned_at: string | null;
  return_received_at: string | null;
  last_event_at: string | null;
  stuck: boolean;
  actions: ShipmentAction[];
  events?: ShipmentEvent[];
  attempts?: DeliveryAttempt[];
}

export type ShipmentBucket = "to_pickup" | "in_transit" | "attention" | "delivered" | "returned" | "cancelled";

export interface ShipmentLabel {
  shipment_id: string;
  provider_label_url: string | null;
  courier: string;
  service_code: string | null;
  tracking_number: string | null;
  order_number: number;
  shop: string;
  from: { name: string; phone: string | null; address: string };
  to: { name: string; phone: string; address: string; landmark: string | null };
  cod_amount: Money;
  weight_grams: number;
  contents: string;
  booked_at: string;
}

export interface BookShipmentInput {
  courier_account_id: string;
  weight_grams?: number | null;
  service_code?: string | null;
  tracking_number?: string | null;
  courier_name?: string | null;
  notes?: string | null;
}

export type SettlementLineMatch =
  | "matched"
  | "amount_mismatch"
  | "unknown_shipment"
  | "not_delivered"
  | "already_settled"
  | "duplicate_in_report"
  | "not_cod";

export interface CodSettlement {
  id: string;
  courier_account_id: string;
  courier_name: string;
  provider: string;
  source: "courier_api" | "file_import" | "manual";
  reference: string;
  status: "needs_review" | "reconciled" | "confirmed";
  currency: string;
  collected_minor: number;
  fees_minor: number;
  net_minor: number;
  expected_minor: number;
  line_count: number;
  issue_count: number;
  period_start: string | null;
  period_end: string | null;
  created_at: string;
  confirmed_at: string | null;
  bank_reference: string | null;
  lines?: {
    id: string;
    tracking_number: string;
    shipment_id: string | null;
    order_id: string | null;
    order_number: number | null;
    collected_minor: number;
    fee_minor: number;
    expected_minor: number | null;
    match_status: SettlementLineMatch;
    accepted: boolean;
    accept_reason: string | null;
    note: string | null;
  }[];
}

export interface CodAwaiting {
  shipment_id: string;
  order_id: string;
  order_number: number;
  customer_name: string | null;
  courier_account_id: string;
  courier_name: string;
  tracking_number: string | null;
  cod_amount: Money;
  delivered_at: string | null;
  days_waiting: number | null;
}

export interface CodOverview extends CodSummary {
  currency: string;
  awaiting_by_age: Record<"d0_7" | "d8_14" | "d15_plus", { count: number; amount_minor: number }>;
  awaiting_by_courier: { courier_account_id: string; courier_name: string; count: number; amount_minor: number }[];
  settlements_needing_review: number;
  received_last_30_days: { count: number; amount_minor: number };
}

/* ---------- Phase 4: returns, exchanges, refunds ---------- */

export type ReturnReason =
  | "size_small"
  | "size_large"
  | "colour_different"
  | "quality_defect"
  | "damaged_in_transit"
  | "not_as_described"
  | "changed_mind"
  | "late_delivery"
  | "wrong_item"
  | "other";

export type ReturnStatus = "requested" | "approved" | "rejected" | "in_transit" | "received" | "inspected" | "refunded" | "exchanged" | "closed" | "cancelled";
export type ReturnCondition = "resellable" | "damaged" | "missing" | "used";
export type RefundMethod = "original_payment" | "bank_transfer" | "esewa" | "khalti" | "fonepay" | "cash" | "other";
export type ReturnBucket = "to_decide" | "in_progress" | "to_refund" | "done";
export type ReturnAction = "approve" | "reject" | "cancel" | "book_pickup" | "mark_received" | "inspect" | "refund";

export interface ReturnPolicy {
  window_days: number;
  allow_refund: boolean;
  allow_exchange: boolean;
  evidence_reasons: ReturnReason[];
  return_shipping_fee_minor: number;
  auto_approve: boolean;
  auto_refund_max_minor: number;
  notes: string | null;
}

export interface ReturnCheck {
  code: "order_delivered" | "within_window" | "quantity_available" | "not_final_sale" | "evidence" | "resolution_allowed" | "exchange_same_product" | "exchange_in_stock" | (string & {});
  ok: boolean;
  /** Soft checks can be overridden with a reason by someone allowed to approve returns. */
  soft: boolean;
  deadline?: string;
  window_days?: number;
  items?: string[];
  status?: string;
}

export interface ReturnSignal {
  code: "frequent_returns" | "high_return_rate" | "high_value" | (string & {});
  count?: number;
  days?: number;
  returned?: number;
  orders?: number;
  amount_minor?: number;
  average_order_minor?: number;
}

export interface Returnable {
  order_id: string;
  order_status: OrderStatus;
  delivered_at: string | null;
  deadline: string | null;
  currency: string;
  refundable_minor: number;
  policy: ReturnPolicy;
  lines: {
    order_line_id: string;
    title: string;
    variant_title: string | null;
    sku: string | null;
    returnable_quantity: number;
    unit_refund_minor: number;
    final_sale: boolean;
    exchange_options: { variant_id: string; title: string; available: number | null }[];
  }[];
}

export interface ReturnLineInput {
  order_line_id: string;
  quantity: number;
  reason: ReturnReason;
  reason_note?: string | null;
  evidence_asset_ids?: string[];
  exchange_variant_id?: string | null;
}

export interface RefundRecord {
  id: string;
  order_id: string;
  return_id: string | null;
  order_number?: number | null;
  amount: Money;
  method: RefundMethod;
  provider: string | null;
  provider_refund_id: string | null;
  reference: string | null;
  status: "pending_approval" | "processing" | "succeeded" | "failed" | "rejected";
  reason: string | null;
  failure_code: string | null;
  created_at: string;
  approved_at: string | null;
  completed_at: string | null;
}

export interface ReturnSummary {
  id: string;
  number: string;
  order_id: string;
  order_number: number | null;
  customer_name: string | null;
  status: ReturnStatus;
  resolution: "refund" | "exchange";
  source: "seller" | "chat" | "customer";
  eligible: boolean;
  signals: ReturnSignal[];
  refund_due: Money;
  return_shipping_fee_minor: number;
  customer_pays_shipping: boolean;
  created_at: string;
  decided_at: string | null;
  received_at: string | null;
  closed_at: string | null;
  exchange_order_id: string | null;
}

export interface ReturnDetail extends ReturnSummary {
  lines: {
    id: string;
    order_line_id: string;
    title: string | null;
    variant_title: string | null;
    sku: string | null;
    quantity: number;
    unit_refund_minor: number;
    reason: ReturnReason;
    reason_note: string | null;
    evidence_asset_ids: string[];
    exchange: { variant_id: string; title: string | null } | null;
    condition: ReturnCondition | null;
    restocked_quantity: number;
    inspection_note: string | null;
  }[];
  eligibility: { checks: ReturnCheck[]; policy_window_days: number };
  override_reason: string | null;
  rejection_reason: string | null;
  note: string | null;
  refunds: RefundRecord[];
  pickup: Shipment | null;
  refundable_minor: number;
  actions: ReturnAction[];
}

/* ---------- Phase 5: automation, Decision Policy, Control Center ---------- */

export type RiskClass = "R0" | "R1" | "R2" | "R3" | "R4";
export type PolicyDecision = "AUTO_EXECUTE" | "REQUIRE_APPROVAL" | "BLOCK";
export type TriggerCode = "order.created" | "order.status_changed" | "shipment.status_changed" | "inventory.low_stock" | "return.status_changed" | "channel.expired";
export type ActionCode = "notify_seller" | "add_order_note" | "send_customer_message" | "send_review_request" | "book_courier" | "request_pickup" | "request_reattempt" | "approve_return";
export type ConditionOp = "eq" | "ne" | "gt" | "gte" | "lt" | "lte" | "in" | "not_in" | "is_true" | "is_false";

export type Condition =
  | { all: Condition[] }
  | { any: Condition[] }
  | { field: string; op: ConditionOp; value?: string | number | boolean | (string | number)[] };

export type WorkflowStep =
  | { id: string; type: "condition"; when: Condition; else?: string; next?: string }
  | { id: string; type: "branch"; when: Condition; then: string; else?: string; next?: string }
  | { id: string; type: "wait"; hours: number; next?: string }
  | { id: string; type: "action"; action: ActionCode; params?: Record<string, string>; next?: string }
  | { id: string; type: "approval"; note?: string; next?: string };

export interface WorkflowDefinition {
  trigger: { event: TriggerCode; filter?: string[] };
  steps: WorkflowStep[];
}

export interface AutomationCatalog {
  triggers: { code: TriggerCode; subject: string; filter_values: string[]; fields: Record<string, "str" | "int" | "bool"> }[];
  ops: ConditionOp[];
  actions: { code: ActionCode; risk_class: RiskClass; subjects: string[]; params: string[]; required_params: string[] }[];
  templates: { code: string; definition: WorkflowDefinition }[];
}

export interface Workflow {
  id: string;
  name: string;
  description: string | null;
  status: "draft" | "active" | "paused";
  paused_reason: string | null;
  template_code: string | null;
  trigger_event: TriggerCode;
  version: number | null;
  runs: Partial<Record<"running" | "waiting" | "awaiting_approval" | "completed" | "failed" | "cancelled" | "skipped", number>>;
  created_at: string;
  updated_at: string;
  definition?: WorkflowDefinition;
}

export interface DecisionRecordView {
  id: string;
  source: string;
  action: string;
  risk_class: RiskClass;
  decision: PolicyDecision;
  rule: string;
  mode: "assisted" | "smart" | "autopilot";
  confidence: number | null;
  impact: Money | null;
  inputs: Record<string, unknown>;
  explanation: { rule: string; vars: Record<string, number | string> };
  outcome: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface WorkflowRunView {
  id: string;
  workflow_id: string;
  trigger_event: TriggerCode;
  subject_type: string | null;
  subject_id: string | null;
  status: "running" | "waiting" | "awaiting_approval" | "completed" | "failed" | "cancelled" | "skipped";
  current_step: string | null;
  next_run_at: string | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
  steps?: {
    id: string;
    step_id: string;
    kind: WorkflowStep["type"];
    action: ActionCode | null;
    status: "pending" | "running" | "done" | "skipped" | "awaiting_approval" | "approved" | "rejected" | "blocked" | "failed";
    attempts: number;
    output: Record<string, unknown>;
    error: string | null;
    decision: DecisionRecordView | null;
    started_at: string;
    finished_at: string | null;
  }[];
}

export interface AutomationApproval {
  id: string;
  run_id: string;
  workflow_id: string | null;
  workflow_name: string | null;
  step_id: string;
  kind: string;
  action: ActionCode | null;
  note: string | null;
  subject_type: string | null;
  subject_id: string | null;
  order_id: string | null;
  order_number: number | null;
  decision: DecisionRecordView | null;
  requested_at: string;
}

export interface AutomationPolicy {
  confidence_threshold: number;
  thresholds: Record<string, number>;
  enabled_r2: string[];
  r2_actions: string[];
}

export interface DryRunResult {
  facts: Record<string, unknown>;
  trace: { step: string; type?: string; result?: boolean; note?: string; action?: string; decision?: PolicyDecision; rule?: string; risk_class?: RiskClass; impact_minor?: number | null }[];
}

export interface ControlCenter {
  period_days: number;
  mode: "assisted" | "smart" | "autopilot";
  state: "running" | "waiting" | "attention";
  currency: string;
  metrics: { orders: number; revenue_minor: number | null; ai_messages: number; messages_sent: number; delivered: number; in_transit: number; returns: number };
  automation: { done_automatically: number; done_by_team: number; share_automatic: number | null };
  needs_attention: { approvals: number; exceptions: number; urgent: number };
  feed: DecisionRecordView[];
}

/* ---------- Phase 6 (part A): Autopilot Score, recommendations, Courier Brain, COD Intelligence ---------- */

export type ApsCapability = "customer_replies" | "order_capture" | "shipment_creation" | "pickup_requests" | "delivery_notifications" | "delivery_recovery" | "returns" | "refunds" | "marketing";

export interface ApsCapabilityScore {
  A: number;
  F: number;
  M: number;
  X: number;
  excluded: Record<string, number>;
  eligible: number;
  /** null = fewer than min_eligible operations: "not enough activity", never 0% or 100%. */
  score: number | null;
  status: "ok" | "not_enough_activity";
  steps_saved: number;
}

export interface ApsLever {
  capability: ApsCapability | (string & {});
  gap: number;
  current_score: number | null;
  potential_score: number | null;
  eligible: number;
  lever: { type: "set_mode" | "plan_upgrade" | "activate_template" | "enable_r2" | "enable_return_auto_approve" | "enable_customer_notifications"; params: Record<string, string> };
}

export interface AutopilotScore {
  window_days: number;
  overall: number | null;
  eligible: number;
  capabilities: Record<string, ApsCapabilityScore>;
  hours_saved_estimate: number;
  method_version: string;
  min_eligible: number;
  levers: ApsLever[];
  history: { date: string; overall: number | null; anomaly: string | null }[];
}

export interface RecommendationView {
  id: string;
  type: "autopilot_improvement" | "courier_selection" | "restock" | (string & {});
  status: "open" | "accepted" | "rejected" | "expired" | "executed" | "failed";
  subject_type: string | null;
  subject_id: string | null;
  explanation: { what: string; why: string; vars: Record<string, string | number | null> };
  evidence: Record<string, unknown>[];
  confidence: number;
  estimated_impact: Record<string, number | string | null>;
  action: { type: string; params?: Record<string, string> };
  method_version: string;
  created_at: string;
  expires_at: string | null;
  resolved_at: string | null;
  reason: string | null;
  outcome: Record<string, unknown> | null;
  outcome_measured_at: string | null;
}

export interface CodRiskFactor {
  code: "delivery_history" | "new_customer" | "return_history" | "address_completeness" | "order_value" | "route_failures";
  contribution: number;
  evidence: Record<string, number | string | boolean | null>;
}

export interface CodRiskAssessment {
  order_id: string;
  level: "LOW" | "MEDIUM" | "HIGHER";
  model_level: "LOW" | "MEDIUM" | "HIGHER";
  score: number;
  factors: CodRiskFactor[];
  recommended_action: "cod_ok" | "verify_phone" | "request_partial_advance" | "manual_review";
  model_version: string;
  data_completeness: number;
  overridden: boolean;
  override_reason: string | null;
  disputed: boolean;
  dispute_note: string | null;
  outcome: "delivered" | "failed" | "returned" | "cancelled" | null;
  created_at: string;
}

export interface CourierPerformanceRow {
  courier_account_id: string;
  courier_name: string | null;
  origin: string;
  destination: string;
  weight_band: string;
  cod: boolean;
  n: number;
  delivery_success: number | null;
  first_attempt_success: number | null;
  failed_rate: number | null;
  eta_p50_days: number | null;
  eta_p90_days: number | null;
  avg_price_minor: number | null;
  cod_settlement_days: number | null;
  enough_data: boolean;
  period_days: number;
  computed_at: string;
}

// ============================================================================= Phase 6 part B
export type ProfitComponentCode =
  | "goods"
  | "delivery_fees"
  | "discounts"
  | "cogs"
  | "payment_fees"
  | "channel_fees"
  | "courier"
  | "packaging"
  | "return_shipping"
  | "refunds"
  | "failed_delivery"
  | "ads";

export interface ProfitComponent {
  code: ProfitComponentCode;
  /** Signed: income positive, costs negative. null when not included. */
  amount_minor: number | null;
  status: "included" | "partial" | "not_included";
  /** How many orders/lines had no data for this component. */
  missing: number;
  reason: "packaging_not_set" | "no_ad_account" | "channel_fees_unknown" | "provider_fees_unknown" | (string & {}) | null;
}

export interface ProfitWaterfall {
  components: ProfitComponent[];
  revenue_minor: number;
  contribution_minor: number;
  margin_pct: number | null;
  complete: boolean;
  units: number;
  orders: number;
}

export interface ProductProfitRow extends ProfitWaterfall {
  product_id: string;
  title: string | null;
  contribution_per_unit_minor: number | null;
}

export interface ProfitSettings {
  packaging_cost_minor: number | null;
  min_margin_pct: number;
  min_contribution_minor: number;
  max_return_rate_pct: number;
}

export interface ProfitSummary {
  /** The shop's ISO currency, e.g. "NPR". */
  currency: string;
  window_days: number;
  shop: ProfitWaterfall;
  products: ProductProfitRow[];
  counts: { sold: number; failed: number; open: number; cost_from_current: number };
  allocation: string;
  method_version: string;
  as_of: string;
  settings: ProfitSettings;
}

export interface ProfitSettingsUpdate {
  packaging_cost_minor?: number | null;
  clear_packaging?: boolean;
  min_margin_pct?: number;
  min_contribution_minor?: number;
  max_return_rate_pct?: number;
}

export type StockRisk = "out" | "high" | "medium" | "low";

export interface ReturnInsightCause {
  type: "variant" | "supplier" | "content_version";
  variant_id?: string;
  variant?: string | null;
  returned_share?: number;
  sold_share?: number;
  supplier?: string;
  status?: string;
}

export interface ReturnInsightView {
  id: string;
  product_id: string;
  title: string | null;
  variant_id: string | null;
  variant: string | null;
  pattern: string;
  reason: string | null;
  reason_share: number | null;
  status: "open" | "acted" | "dismissed" | "resolved";
  window_days: number;
  sold: number;
  returned: number;
  rate: number;
  baseline_rate: number | null;
  p_value: number | null;
  reasons: Record<string, number>;
  causes: ReturnInsightCause[];
  acted_at: string | null;
  post_change_rate: number | null;
  post_change_sold: number | null;
  method_version: string;
  created_at: string | null;
}

export type MemoryFactType = "fit_runs_small" | "fit_runs_large" | "repeat_cycle_days" | "peak_order_hours" | "best_courier_route";

export interface MemoryFact {
  id: string;
  subject_type: "product" | "shop" | "district" | (string & {});
  subject_id: string;
  subject_label: string | null;
  fact_type: MemoryFactType | (string & {});
  value: Record<string, string | number | null>;
  confidence: number;
  evidence: Record<string, unknown>[];
  status: "active" | "superseded" | "rejected_by_merchant";
  source: "derived" | "merchant";
  confirmed: boolean;
  version: number;
  method_version: string;
  valid_from: string;
  valid_to: string | null;
  note: string | null;
}

export interface MemoryMetricSeries {
  metric: string;
  subject: string;
  period: "day" | "week" | "month";
  definition: string;
  points: { period_start: string; value: number | null; n: number }[];
}

export interface ProductBrain {
  product_id: string;
  /** The shop's ISO currency (on the brain endpoint; may be absent on stock-risk rows). */
  currency?: string;
  units_7d: number;
  units_30d: number;
  units_90d: number;
  in_stock_days_90d: number;
  demand_per_day: number | null;
  available: number | null;
  cover_days: number | null;
  stockouts_90d: number;
  margin_pct: number | null;
  contribution_per_unit_minor: number | null;
  return_rate: number | null;
  completeness: number;
  stock_risk: StockRisk | null;
  fit: "small" | "large" | null;
  sold_90d_delivered: number;
  returned_90d: number;
  top_reasons: { reason: string; units: number }[];
  by_variant: { variant_id: string; variant: string | null; sold: number; returned: number; rate: number }[];
  contribution_basis: "complete" | "partial" | "cost_not_set" | "not_enough_sales" | (string & {});
  stock_tracked: boolean;
  /** section → reason code, e.g. { margin: "cost_not_set", seasonality: "needs_12_months" } */
  not_included: Record<string, string>;
  method_version: string;
  as_of: string;
  /** null when Return Intelligence isn't on the plan. */
  return_insights?: ReturnInsightView[] | null;
  facts?: MemoryFact[];
}

export interface StockRiskItem extends ProductBrain {
  title: string;
}
