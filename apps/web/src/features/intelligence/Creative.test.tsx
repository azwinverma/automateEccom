import {
  ApiError,
  type CreativeExperiment,
  type CreativeGenome,
  type CreativePostRow,
  type CreativeSuggestions,
  type RecommendationView,
} from "@commerce-os/api-client";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { renderWithI18n } from "@/test/render";
import { ReelBestSettings, SuggestedTime } from "./CreativeSuggest";
import { CreativeView } from "./CreativeView";
import { paceFor } from "./creativeLabels";
import { Recommendations } from "./Recommendations";

vi.mock("next/navigation", async (orig) => ({
  ...(await orig<typeof import("next/navigation")>()),
  usePathname: () => "/content/insights",
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }),
}));

const pref = (over: Partial<CreativeGenome["preferences"][number]> = {}): CreativeGenome["preferences"][number] => ({
  attribute: "language_mix", value: "ne_en_mixed", n: 12, mean: 2.5, shrunk: 2.2, lift: 0.69, z: 4.1, confidence: "high",
  engagement_rate: 0.12, engagement_lift: 0.1, engagement_only: false, recommended: true, ...over,
});
const impact = { genome_posts: 0, other_posts: 0, genome_mean_orders: null, other_mean_orders: null, method: "observational" as const, note: "" };
const genome = (over: Partial<CreativeGenome> = {}): CreativeGenome => ({
  version: 3, status: "ready", posts: 24, measured_posts: 24, min_posts: 20,
  baseline: { outcome: "orders", mean: 1.3, orders: 31, engagement_rate: 0.12, min_posts: 20, min_per_value: 5, window_days: 7, lookback_days: 180 },
  preferences: [pref(), pref({ attribute: "posting_window", value: "evening", lift: 0.02, confidence: "low", engagement_lift: 0.6, engagement_only: true, recommended: false })],
  method_version: "cgn-1.0", computed_at: new Date().toISOString(), impact, ...over,
});
const row = (over: Partial<CreativePostRow> = {}): CreativePostRow => ({
  post_id: "p1", kind: "post", caption: "Dashain collection is here", product_id: "prod1", published_at: new Date().toISOString(), genome_version: null, features: {},
  metrics: {
    window_days: 7, window_complete: false, views: 1500, engagements: 90, clicks: null, source: "manual", inquiries: 1, orders: 1.3, revenue_minor: 318500, contribution_minor: null,
    attribution: { method: "mixed", explicit_orders: 1, window_orders: 0.3, explicit_inquiries: 1, window_inquiries: 0, decay_days: 3 },
  },
  ...over,
});
const experiment = (over: Partial<CreativeExperiment> = {}): CreativeExperiment => ({
  id: "e1", name: "Price first?", hypothesis: "Showing the price first brings more orders", attribute: "hook_type", variant_a: "price_first", variant_b: "product_closeup",
  metric: "orders", min_posts: 3, max_days: 30, status: "running", started_at: new Date().toISOString(), ends_by: new Date(Date.now() + 86400000 * 20).toISOString(), ended_at: null,
  result: { a: { n: 3, mean: 3.1 }, b: { n: 1, mean: 0.5 }, status: "collecting" }, ...over,
});

const api = {
  intelligence: {
    creativeGenome: vi.fn(), refreshCreative: vi.fn(), creativePosts: vi.fn(), addPostMetrics: vi.fn(), experiments: vi.fn(), createExperiment: vi.fn(), stopExperiment: vi.fn(),
    recommendations: vi.fn(), accept: vi.fn(), reject: vi.fn(),
  },
};
let perms = new Set<string>();
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ feature: () => "yes", api, merchantId: "m1", can: (p: string) => perms.has(p) }) }));

beforeEach(() => {
  vi.clearAllMocks();
  perms = new Set(["content.read", "content.write", "content.publish", "analytics.read"]);
  api.intelligence.creativeGenome.mockResolvedValue(genome());
  api.intelligence.creativePosts.mockResolvedValue({ items: [row()], window_days: 7, currency: "NPR" });
  api.intelligence.experiments.mockResolvedValue({ items: [experiment()], attributes: [] });
});

describe("What sells", () => {
  it("shows what sells with the lift, and likes-only patterns separately", async () => {
    renderWithI18n(<CreativeView />);
    const panel = await screen.findByTestId("creative-genome");
    expect(panel).toHaveAttribute("data-status", "ready");
    const p = within(panel).getByTestId("genome-pattern");
    expect(p).toHaveTextContent(en.intel.creative.v.language_mix_ne_en_mixed);
    expect(p).toHaveTextContent("1.7× the orders of your average post");
    expect(p).toHaveTextContent(en.intel.creative.conf_high);
    const likes = within(panel).getByTestId("genome-likes");
    expect(likes).toHaveTextContent("Posting in the evening (5–8 PM): 60% more engagement");
    expect(within(panel).getByTestId("genome-impact")).toHaveTextContent(en.intel.creative.impactTitle);
  });

  it("shows the learning state with how many posts are measured", async () => {
    api.intelligence.creativeGenome.mockResolvedValue(genome({ version: null, status: "learning", posts: 6, measured_posts: 6, preferences: [], baseline: null }));
    renderWithI18n(<CreativeView />);
    expect(await screen.findByTestId("genome-progress")).toHaveTextContent("6 of 20 posts measured");
    expect(screen.getByRole("meter")).toHaveAttribute("aria-valuenow", "6");
  });

  it("shows the upsell without the plan but keeps post results", async () => {
    api.intelligence.creativeGenome.mockRejectedValue(new ApiError({ status: 403, code: "feature_not_in_plan", message: "x", requestId: "q" }));
    api.intelligence.experiments.mockRejectedValue(new ApiError({ status: 403, code: "feature_not_in_plan", message: "x", requestId: "q" }));
    renderWithI18n(<CreativeView />);
    expect(await screen.findByText(en.intel.creative.upsell)).toBeInTheDocument();
    expect(await screen.findByTestId("post-result")).toBeInTheDocument();
    expect(screen.queryByTestId("creative-experiments")).toBeNull();
  });

  it("lists post results with their source and saves typed-in numbers", async () => {
    api.intelligence.addPostMetrics.mockResolvedValue(row());
    renderWithI18n(<CreativeView />);
    const r = await screen.findByTestId("post-result");
    expect(r).toHaveTextContent(en.intel.creative.source_manual);
    expect(r).toHaveTextContent("1.3");
    expect(r).toHaveTextContent(en.intel.creative.costNotSet);
    expect(r).toHaveTextContent(en.intel.creative.method_mixed);
    await userEvent.click(within(r).getByRole("button", { name: en.intel.creative.addResults }));
    const form = await screen.findByTestId("post-metrics-form");
    await userEvent.click(screen.getByRole("button", { name: en.intel.creative.saveResults }));
    expect(within(form).getByRole("alert")).toHaveTextContent(en.intel.creative.needOne);
    await userEvent.type(within(form).getByLabelText(en.intel.creative.views), "1800");
    await userEvent.type(within(form).getByLabelText(en.intel.creative.likes), "120");
    await userEvent.click(screen.getByRole("button", { name: en.intel.creative.saveResults }));
    await waitFor(() => expect(api.intelligence.addPostMetrics).toHaveBeenCalledWith("p1", { views: 1800, likes: 120 }));
  });

  it("rejects negative or fractional numbers before sending", async () => {
    renderWithI18n(<CreativeView />);
    const r = await screen.findByTestId("post-result");
    await userEvent.click(within(r).getByRole("button", { name: en.intel.creative.addResults }));
    const form = await screen.findByTestId("post-metrics-form");
    await userEvent.type(within(form).getByLabelText(en.intel.creative.views), "1.5");
    await userEvent.click(screen.getByRole("button", { name: en.intel.creative.saveResults }));
    expect(within(form).getByRole("alert")).toHaveTextContent(en.intel.creative.wholeNumber);
    expect(api.intelligence.addPostMetrics).not.toHaveBeenCalled();
  });
});

describe("Tests (experiments)", () => {
  it("shows progress and verdicts, and stops a running test", async () => {
    api.intelligence.stopExperiment.mockResolvedValue(experiment({ status: "stopped" }));
    api.intelligence.experiments.mockResolvedValue({
      items: [
        experiment(),
        experiment({ id: "e2", name: "CTA", status: "concluded", result: { a: { n: 5, mean: 3 }, b: { n: 5, mean: 1 }, z: 3.1, winner: "a", verdict: "clear" } }),
      ],
      attributes: [],
    });
    renderWithI18n(<CreativeView />);
    const [running, done] = await screen.findAllByTestId("experiment");
    expect(running).toHaveTextContent(en.intel.creative.verdict_collecting);
    expect(running).toHaveTextContent("Opening with the price: 3 of 3 posts · Opening on a close-up: 1 of 3 posts");
    expect(done).toHaveTextContent("Opening with the price wins: 3 against 1 orders per post.");
    await userEvent.click(within(running!).getByRole("button", { name: en.intel.creative.expStop }));
    await waitFor(() => expect(api.intelligence.stopExperiment).toHaveBeenCalledWith("e1"));
  });

  it("validates and creates a test", async () => {
    api.intelligence.createExperiment.mockResolvedValue(experiment());
    renderWithI18n(<CreativeView />);
    await userEvent.click(await screen.findByRole("button", { name: en.intel.creative.expNew }));
    const form = await screen.findByTestId("experiment-form");
    await userEvent.click(screen.getByRole("button", { name: en.intel.creative.expCreate }));
    expect(within(form).getByRole("alert")).toHaveTextContent(en.intel.creative.expRequired);
    await userEvent.type(within(form).getByLabelText(en.intel.creative.expName), "Mixed captions?");
    await userEvent.type(within(form).getByLabelText(en.intel.creative.expHypothesis), "Mixed captions sell more");
    await userEvent.selectOptions(within(form).getByLabelText(en.intel.creative.expAttribute), "language_mix");
    await userEvent.selectOptions(within(form).getByLabelText(en.intel.creative.expB), "ne");
    await userEvent.selectOptions(within(form).getByLabelText(en.intel.creative.expA), "ne");
    await userEvent.click(screen.getByRole("button", { name: en.intel.creative.expCreate }));
    expect(within(form).getByRole("alert")).toHaveTextContent(en.intel.creative.expSame);
    await userEvent.selectOptions(within(form).getByLabelText(en.intel.creative.expA), "ne_en_mixed");
    await userEvent.click(screen.getByRole("button", { name: en.intel.creative.expCreate }));
    await waitFor(() =>
      expect(api.intelligence.createExperiment).toHaveBeenCalledWith({
        name: "Mixed captions?", hypothesis: "Mixed captions sell more", attribute: "language_mix", variant_a: "ne_en_mixed", variant_b: "ne", metric: "orders", min_posts: 5, max_days: 30,
      }),
    );
  });
});

const sugg = (over: Partial<CreativeSuggestions> = {}): CreativeSuggestions => ({
  genome_version: 3, status: "ready", caption: [], studio_guidance: null,
  reel: { target_seconds: [8, 11], show_price: true }, schedule: { window: "evening", hours: [18, 21], source: "genome", lift: 0.4 }, ...over,
});

describe("Using the genome", () => {
  it("passes the genome version only for a learned posting window", async () => {
    const onUse = vi.fn();
    const first = renderWithI18n(<SuggestedTime suggestions={sugg()} onUse={onUse} />);
    expect(screen.getByTestId("suggested-time")).toHaveTextContent("Best time to post: 6 PM–9 PM");
    await userEvent.click(screen.getByRole("button", { name: en.intel.creative.useTime }));
    expect(onUse).toHaveBeenCalledWith(18, 3);
    first.unmount();
    renderWithI18n(<SuggestedTime suggestions={sugg({ schedule: { hours: [19, 22], source: "orders" } })} onUse={onUse} />);
    expect(screen.getByTestId("suggested-time")).toHaveTextContent(en.intel.creative.suggestOrders);
    await userEvent.click(screen.getByRole("button", { name: en.intel.creative.useTime }));
    expect(onUse).toHaveBeenLastCalledWith(19, null);
  });

  it("offers reel settings and picks a pace that lands in the target length", async () => {
    const onApply = vi.fn();
    renderWithI18n(<ReelBestSettings suggestions={sugg()} applied={false} onApply={onApply} />);
    expect(screen.getByTestId("reel-best")).toHaveTextContent("Your best settings: 8–11 second videos, price shown");
    await userEvent.click(screen.getByRole("button", { name: en.intel.creative.useBest }));
    expect(onApply).toHaveBeenCalled();
    expect(paceFor([8, 11], 3)).toBe(3);
    expect(paceFor([8, 11], 10)).toBe(1.5);
    expect(paceFor([21, 30], 1)).toBe(6);
  });

  it("renders nothing without suggestions", () => {
    const { container } = renderWithI18n(<SuggestedTime suggestions={null} onUse={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("creative tips on Home", () => {
  it("explains a learned pattern as a tip", async () => {
    const tip: RecommendationView = {
      id: "r9", type: "creative_tip", status: "open", subject_type: "creative_attribute", subject_id: "language_mix:ne_en_mixed",
      explanation: { what: "creative_language_mix", why: "creative_pattern", vars: { value: "ne_en_mixed", lift_pct: 69, n: 12, outcome: "orders" } },
      evidence: [], confidence: 0.8, estimated_impact: { lift: 0.69 }, action: { type: "none", params: { attribute: "language_mix", value: "ne_en_mixed" } },
      method_version: "rec-1.0", created_at: new Date().toISOString(), expires_at: null, resolved_at: null, reason: null, outcome: null, outcome_measured_at: null,
    };
    api.intelligence.recommendations.mockResolvedValue({ items: [tip] });
    renderWithI18n(<Recommendations />);
    const li = await screen.findByText("Post more: Nepali-English mixed captions");
    expect(li.closest("li")).toHaveTextContent("Posts like this got 69% more orders than your average post (12 posts).");
  });
});
