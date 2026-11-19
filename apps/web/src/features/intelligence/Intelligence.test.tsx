import { ApiError, type AutopilotScore, type CodRiskAssessment, type OrderDetail, type RecommendationView } from "@commerce-os/api-client";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { ne } from "@/i18n/messages/ne";
import { renderWithI18n } from "@/test/render";
import { AutopilotScoreCard } from "./AutopilotScoreCard";
import { CodRiskCard } from "./CodRiskCard";
import { Recommendations } from "./Recommendations";

vi.mock("next/navigation", async (orig) => ({ ...(await orig<typeof import("next/navigation")>()), useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }) }));

const cap = (A: number, F: number, M: number, score: number | null, extra = {}) => ({ A, F, M, X: 0, excluded: {}, eligible: A + F + M, score, status: score === null ? "not_enough_activity" : "ok", steps_saved: A * 2, ...extra }) as AutopilotScore["capabilities"][string];
const score = (over: Partial<AutopilotScore> = {}): AutopilotScore => ({
  window_days: 30, overall: 0.75, eligible: 40, min_eligible: 10, method_version: "aps-1.0", hours_saved_estimate: 1.5, levers: [], history: [],
  capabilities: { customer_replies: cap(30, 0, 10, 0.75), returns: cap(1, 0, 2, null, { X: 4, excluded: { above_threshold: 4 } }) },
  ...over,
});
const rec = (over: Partial<RecommendationView> = {}): RecommendationView => ({
  id: "r1", type: "autopilot_improvement", status: "open", subject_type: "capability", subject_id: "customer_replies",
  explanation: { what: "lever.set_mode", why: "manual_gap", vars: { capability: "customer_replies", manual: 15, eligible: 15, mode: "smart" } },
  evidence: [], confidence: 0.9, estimated_impact: { capability: "customer_replies", score_from: 0, score_to: 1 }, action: { type: "set_mode", params: { mode: "smart" } },
  method_version: "rec-1.0", created_at: new Date().toISOString(), expires_at: null, resolved_at: null, reason: null, outcome: null, outcome_measured_at: null,
  ...over,
});
const assessment: CodRiskAssessment = {
  order_id: "o1", level: "HIGHER", model_level: "HIGHER", score: 0.75, recommended_action: "manual_review", model_version: "codi-1.0", data_completeness: 0.75,
  factors: [{ code: "delivery_history", contribution: 0.55, evidence: { delivered: 0, failed: 2 } }, { code: "route_failures", contribution: 0.15, evidence: { failed_rate: 0.3, n: 20, district: "kaski" } }],
  overridden: false, override_reason: null, disputed: false, dispute_note: null, outcome: null, created_at: new Date().toISOString(),
};
const order = { id: "o1", payment_method: "cod", version: 2 } as unknown as OrderDetail;

const api = { intelligence: { autopilotScore: vi.fn(), recommendations: vi.fn(), accept: vi.fn(), reject: vi.fn(), codAssessment: vi.fn(), codOverride: vi.fn(), codDispute: vi.fn() } };
let perms = new Set<string>();
let featuresOff = new Set<string>();
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ feature: (c: string) => (featuresOff.has(c) ? "no" : "yes"), api, merchantId: "m1", can: (p: string) => perms.has(p) }) }));

beforeEach(() => {
  vi.clearAllMocks();
  featuresOff = new Set();
  perms = new Set(["analytics.read", "orders.write", "automation.approve"]);
  api.intelligence.autopilotScore.mockResolvedValue(score());
  api.intelligence.recommendations.mockResolvedValue({ items: [rec()] });
  api.intelligence.codAssessment.mockResolvedValue(assessment);
});

describe("AutopilotScoreCard", () => {
  it("shows the score, thin capabilities as not enough activity, and what wasn't counted", async () => {
    renderWithI18n(<AutopilotScoreCard />);
    expect(await screen.findByTestId("aps-overall")).toHaveTextContent("75%");
    const returns = screen.getByRole("img", { name: `${en.intel.aps.capability.returns}: ${en.intel.aps.notEnough}` });
    expect(returns).toBeInTheDocument();
    expect(screen.getByText(/needed approval by your rules \(4\)/)).toBeInTheDocument();
    expect(screen.getByText(/estimated/)).toBeInTheDocument();
  });

  it("says when there isn't enough activity overall", async () => {
    api.intelligence.autopilotScore.mockResolvedValue(score({ overall: null }));
    renderWithI18n(<AutopilotScoreCard />, { locale: "ne" });
    expect(await screen.findByTestId("aps-overall")).toHaveTextContent(ne.intel.aps.notEnough);
  });
});

describe("Recommendations", () => {
  it("explains what, why and impact, and applies", async () => {
    const u = userEvent.setup();
    api.intelligence.accept.mockResolvedValue(rec({ status: "executed" }));
    renderWithI18n(<Recommendations />);
    const card = await screen.findByTestId("recommendations");
    expect(within(card).getByText(en.intel.rec.what.lever_set_mode)).toBeInTheDocument();
    expect(within(card).getByText(/Your team did 15 of 15 by hand/)).toBeInTheDocument();
    expect(within(card).getByText(/from 0% to 100% automatic/)).toBeInTheDocument();
    api.intelligence.recommendations.mockResolvedValue({ items: [] });
    await u.click(within(card).getByRole("button", { name: en.intel.rec.apply }));
    await waitFor(() => expect(api.intelligence.accept).toHaveBeenCalledWith("r1"));
  });

  it("explains who can apply when not allowed", async () => {
    const u = userEvent.setup();
    api.intelligence.accept.mockRejectedValue(new ApiError({ status: 403, code: "permission_denied", message: "x", requestId: "q" }));
    renderWithI18n(<Recommendations />);
    await u.click(await screen.findByRole("button", { name: en.intel.rec.apply }));
    expect(await screen.findByText(en.intel.rec.managerOnly)).toBeInTheDocument();
  });

  it("restock suggestions are acknowledged, not applied", async () => {
    api.intelligence.recommendations.mockResolvedValue({
      items: [rec({ type: "restock", explanation: { what: "restock", why: "selling_low_stock", vars: { title: "Kurta", variant: "M", available: 1, sold_30d: 2, cover_days: 15 } }, action: { type: "none" }, estimated_impact: { cover_days: 15 } })],
    });
    renderWithI18n(<Recommendations />);
    expect(await screen.findByText("Restock Kurta (M)")).toBeInTheDocument();
    expect(screen.getByText(/about 15 days of stock/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: en.intel.rec.apply })).toBeNull();
    expect(screen.getByRole("button", { name: en.intel.rec.acknowledge })).toBeInTheDocument();
  });
});

describe("CodRiskCard", () => {
  it("shows the level, the reasons and the fairness note; override needs a reason", async () => {
    const u = userEvent.setup();
    api.intelligence.codOverride.mockResolvedValue({ ...assessment, level: "LOW", overridden: true, override_reason: "Called them" });
    renderWithI18n(<CodRiskCard order={order} onChanged={vi.fn()} />);
    const card = await screen.findByTestId("cod-risk");
    expect(within(card).getByText(en.intel.cod.level.HIGHER)).toBeInTheDocument();
    expect(within(card).getByText(en.intel.cod.action.manual_review)).toBeInTheDocument();
    expect(within(card).getByText("Delivered 0, failed 2 before with you")).toBeInTheDocument();
    expect(within(card).getByText("30% of your deliveries to kaski failed (20)")).toBeInTheDocument();
    expect(within(card).getByText(en.intel.cod.fairness)).toBeInTheDocument();
    await u.click(within(card).getByRole("button", { name: en.intel.cod.override }));
    const dialog = await screen.findByRole("dialog");
    await u.selectOptions(within(dialog).getByLabelText(en.intel.cod.overrideLevel), "LOW");
    const save = within(dialog).getByRole("button", { name: en.couriers.save });
    expect(save).toBeDisabled();
    await u.type(within(dialog).getByLabelText(en.intel.cod.reason), "Called them");
    await u.click(save);
    await waitFor(() => expect(api.intelligence.codOverride).toHaveBeenCalledWith("o1", "LOW", "Called them"));
  });

  it("is hidden when the plan doesn't include it", async () => {
    api.intelligence.codAssessment.mockRejectedValue(new ApiError({ status: 403, code: "feature_not_in_plan", message: "x", requestId: "q" }));
    renderWithI18n(<CodRiskCard order={order} onChanged={vi.fn()} />);
    await waitFor(() => expect(api.intelligence.codAssessment).toHaveBeenCalled());
    expect(screen.queryByTestId("cod-risk")).toBeNull();
  });

  it("doesn't ask the API when the plan's features say no", async () => {
    featuresOff = new Set(["intelligence.cod"]);
    renderWithI18n(<CodRiskCard order={order} onChanged={vi.fn()} />);
    await new Promise((r) => setTimeout(r, 20));
    expect(api.intelligence.codAssessment).not.toHaveBeenCalled();
    expect(screen.queryByTestId("cod-risk")).toBeNull();
  });
});
