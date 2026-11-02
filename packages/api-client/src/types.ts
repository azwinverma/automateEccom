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
