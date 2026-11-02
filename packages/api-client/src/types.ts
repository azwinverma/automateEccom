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
