import type { AutomationCatalog, ControlCenter as CC, Workflow } from "@commerce-os/api-client";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { ne } from "@/i18n/messages/ne";
import { exceptionSummaryKey, exceptionTarget } from "@/lib/exceptions";
import { renderWithI18n } from "@/test/render";
import { ControlCenter } from "./ControlCenter";
import { WorkflowBuilder } from "./WorkflowBuilder";

vi.mock("next/navigation", async (orig) => ({ ...(await orig<typeof import("next/navigation")>()), useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }), useSearchParams: () => new URLSearchParams() }));

const cc = (over: Partial<CC> = {}): CC => ({
  period_days: 7, mode: "smart", state: "running", currency: "NPR",
  metrics: { orders: 12, revenue_minor: 3200000, ai_messages: 40, messages_sent: 55, delivered: 9, in_transit: 2, returns: 1 },
  automation: { done_automatically: 30, done_by_team: 10, share_automatic: 0.75 },
  needs_attention: { approvals: 1, exceptions: 0, urgent: 0 },
  feed: [{ id: "d1", source: "workflow", action: "book_courier", risk_class: "R1", decision: "AUTO_EXECUTE", rule: "smart_r1", mode: "smart", confidence: 1, impact: null, inputs: {}, explanation: { rule: "smart_r1", vars: {} }, outcome: "executed", created_at: new Date().toISOString(), resolved_at: null }],
  ...over,
});
const approval = { id: "a1", run_id: "r1", workflow_id: "w1", workflow_name: "Packed → courier", step_id: "book", kind: "action", action: "book_courier" as const, note: null, subject_type: "order", subject_id: "o1", order_id: "o1", order_number: 1001, decision: { ...cc().feed[0]!, decision: "REQUIRE_APPROVAL" as const, rule: "assisted_mode" }, requested_at: new Date().toISOString() };
const catalog: AutomationCatalog = {
  triggers: [{ code: "order.created", subject: "order", filter_values: [], fields: { "order.total_minor": "int", "customer.first_order": "bool", "order.payment_method": "str" } }],
  ops: ["eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "is_true", "is_false"],
  actions: [
    { code: "notify_seller", risk_class: "R0", subjects: ["order"], params: ["message"], required_params: [] },
    { code: "send_customer_message", risk_class: "R1", subjects: ["order"], params: ["text_en", "text_ne"], required_params: ["text_en"] },
  ],
  templates: [],
};
const workflow: Workflow = {
  id: "w1", name: "Welcome", description: null, status: "draft", paused_reason: null, template_code: null, trigger_event: "order.created", version: 1, runs: {},
  created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
  definition: { trigger: { event: "order.created" }, steps: [{ id: "s1", type: "action", action: "notify_seller", params: { message: "" } }] },
};

const api = {
  controlCenter: vi.fn(),
  orders: { list: vi.fn(async () => ({ items: [], next_cursor: null })) },
  automation: { approvals: vi.fn(), approve: vi.fn(), reject: vi.fn(), workflow: vi.fn(), catalog: vi.fn(), runs: vi.fn(async () => ({ items: [] })), update: vi.fn(), setStatus: vi.fn(), dryRun: vi.fn() },
};
let perms = new Set<string>();
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ api, merchantId: "m1", can: (p: string) => perms.has(p) }) }));

beforeEach(() => {
  vi.clearAllMocks();
  perms = new Set(["automation.read", "automation.write", "automation.approve", "orders.read"]);
  api.controlCenter.mockResolvedValue(cc());
  api.automation.approvals.mockResolvedValue({ items: [approval] });
  api.automation.workflow.mockResolvedValue(workflow);
  api.automation.catalog.mockResolvedValue(catalog);
});

describe("ControlCenter", () => {
  it("says the store is running with real numbers, the automatic share and why things ran", async () => {
    renderWithI18n(<ControlCenter />);
    const board = await screen.findByTestId("control-center");
    expect(within(board).getByRole("heading", { name: en.control.state.running })).toBeInTheDocument();
    expect(within(board).getByText("Rs 32,000")).toBeInTheDocument();
    expect(within(board).getByRole("img", { name: "75% automatic" })).toBeInTheDocument();
    expect(within(screen.getByTestId("autopilot-feed")).getByText(new RegExp(en.automation.rule.smart_r1.replace(/[()]/g, ".")))).toBeInTheDocument();
  });

  it("approves a waiting step and hides revenue when not allowed", async () => {
    const u = userEvent.setup();
    api.controlCenter.mockResolvedValue(cc({ state: "waiting", metrics: { ...cc().metrics, revenue_minor: null } }));
    api.automation.approve.mockResolvedValue({ id: "r1", status: "completed" });
    renderWithI18n(<ControlCenter />);
    const list = await screen.findByTestId("automation-approvals");
    expect(within(list).getByText(new RegExp(en.automation.rule.assisted_mode))).toBeInTheDocument();
    expect(screen.queryByText(en.control.revenue)).toBeNull();
    api.automation.approvals.mockResolvedValue({ items: [] });
    await u.click(within(list).getByRole("button", { name: en.automation.approvals.approve }));
    await waitFor(() => expect(api.automation.approve).toHaveBeenCalledWith("a1"));
    await waitFor(() => expect(screen.queryByTestId("automation-approvals")).toBeNull());
  });

  it("without automation.approve explains who can approve", async () => {
    perms.delete("automation.approve");
    renderWithI18n(<ControlCenter />);
    expect(await screen.findByText(en.automation.approvals.managerOnly)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: en.automation.approvals.approve })).toBeNull();
  });

  it("renders in Nepali", async () => {
    renderWithI18n(<ControlCenter />, { locale: "ne" });
    expect(await screen.findByRole("heading", { name: ne.control.state.running })).toBeInTheDocument();
  });
});

describe("WorkflowBuilder", () => {
  it("builds a condition + message and saves it as a new version", async () => {
    const u = userEvent.setup();
    api.automation.update.mockResolvedValue({ ...workflow, version: 2 });
    renderWithI18n(<WorkflowBuilder id="w1" />);
    await screen.findByTestId("workflow-builder");
    await u.selectOptions(screen.getByLabelText(en.automation.builder.addStep), "condition");
    await u.click(screen.getByRole("button", { name: en.automation.builder.addStep }));
    const field = screen.getByLabelText(`${en.automation.builder.conditionField.replace("{n}", "1")} (${en.automation.builder.stepN.replace("{n}", "2")})`);
    await u.selectOptions(field, "customer.first_order");
    await u.selectOptions(screen.getByLabelText(en.automation.builder.addStep), "action");
    await u.click(screen.getByRole("button", { name: en.automation.builder.addStep }));
    const actionSelects = screen.getAllByLabelText(en.automation.builder.action);
    await u.selectOptions(actionSelects[1]!, "send_customer_message");
    await u.type(screen.getByLabelText(en.automation.builder.param.text_en), "Thanks {{name}!");
    await u.click(screen.getByRole("button", { name: en.automation.builder.save }));
    await waitFor(() => expect(api.automation.update).toHaveBeenCalled());
    const def = api.automation.update.mock.calls[0]![1].definition;
    expect(def.steps).toEqual([
      { id: "s1", type: "action", action: "notify_seller", params: { message: "" } },
      { id: "s2", type: "condition", when: { all: [{ field: "customer.first_order", op: "is_true" }] }, else: "stop" },
      { id: "s3", type: "action", action: "send_customer_message", params: { text_en: "Thanks {name}!" } },
    ]);
  });

  it("turning on needs automation.approve", async () => {
    perms.delete("automation.approve");
    renderWithI18n(<WorkflowBuilder id="w1" />);
    await screen.findByTestId("workflow-builder");
    expect(screen.queryByTestId("toggle-workflow")).toBeNull();
  });
});

describe("automation exceptions", () => {
  it("link to automation", () => {
    const rec = (type: string, action: string, details: Record<string, unknown>) => ({ id: "x", type, severity: "high", resource: { type: "workflow", id: "w1" }, occurred_at: null, action, details }) as never;
    expect(exceptionTarget(rec("automation_paused", "open_workflow", {}))).toEqual({ kind: "link", href: "/automation/w1", label: "open_workflow" });
    expect(exceptionSummaryKey(rec("automation_approval", "review_automation", { name: "Flow", step_action: "book_courier" }))).toEqual({ key: "automationApproval", vars: { name: "Flow", action: "book_courier" } });
  });
});
