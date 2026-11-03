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
> & { category_id?: string | null };

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
