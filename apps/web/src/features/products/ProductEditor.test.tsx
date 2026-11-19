import { ApiError, type Category, type Collection, type ProductDetail } from "@commerce-os/api-client";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/messages/en";
import { renderWithI18n } from "@/test/render";
import { EditorForm } from "./ProductEditor";
import { StatusControl } from "./StatusControl";

const ed = en.products.editor;

function detail(over: Partial<ProductDetail> = {}): ProductDetail {
  return {
    id: "p1",
    title: "Cotton Kurta",
    title_ne: null,
    handle: "cotton-kurta",
    description: null,
    description_ne: null,
    status: "draft",
    category_id: null,
    brand: null,
    product_type: null,
    tags: [],
    seo_title: null,
    seo_description: null,
    version: 3,
    published_at: null,
    created_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-01T00:00:00Z",
    options: [{ id: "o1", name: "Size", values: ["M", "L"] }],
    variants: ["M", "L"].map((s) => ({
      id: `v-${s}`,
      title: s,
      sku: `COTTON-KURTA-${s}`,
      barcode: null,
      options: { Size: s },
      price: { amount_minor: 125000, currency: "NPR" },
      compare_at: null,
      cost: null,
      weight_grams: 300,
      dimensions_mm: [null, null, null],
      status: "active" as const,
      suppliers: [],
    })),
    attributes: [],
    collection_ids: [],
    needs_review: false,
    ...over,
  };
}

const catalog = {
  categories: vi.fn(async () => ({ items: [] as Category[] })),
  collections: vi.fn(async () => ({ items: [] as Collection[] })),
  product: vi.fn(),
  createProduct: vi.fn(),
  updateProduct: vi.fn(),
  updateVariant: vi.fn(),
  archiveVariant: vi.fn(),
  setStatus: vi.fn(),
  confirmAttributes: vi.fn(),
  setAttributes: vi.fn(),
  listings: vi.fn(async () => ({ items: [] })),
  publish: vi.fn(),
  unpublish: vi.fn(),
  addVariant: vi.fn(),
  addToCollection: vi.fn(async () => undefined),
  removeFromCollection: vi.fn(async () => undefined),
  createCollection: vi.fn(),
};
const channels = { list: vi.fn(async () => ({ items: [] })) };
let permissions = new Set(["catalog.read", "catalog.write", "catalog.publish"]);
// Stable references: useApiQuery refetches when `api` identity changes.
const api = { catalog, channels };
const can = (p: string) => permissions.has(p);

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({ feature: () => "yes", api, merchantId: "m1", can }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  catalog.categories.mockResolvedValue({ items: [] });
  catalog.collections.mockResolvedValue({ items: [] });
  catalog.listings.mockResolvedValue({ items: [] });
  channels.list.mockResolvedValue({ items: [] });
  permissions = new Set(["catalog.read", "catalog.write", "catalog.publish"]);
});

describe("StatusControl transition rules", () => {
  const noop = () => {};
  it("draft offers Publish and Archive only", () => {
    renderWithI18n(<StatusControl status="draft" canPublish dirty={false} pending={null} onChange={noop} />);
    const group = screen.getByTestId("status-control");
    expect(within(group).getAllByRole("button").map((b) => b.textContent)).toEqual([ed.statusAction.publish, ed.statusAction.archive]);
  });
  it("active offers Move to draft and Archive", () => {
    renderWithI18n(<StatusControl status="active" canPublish dirty={false} pending={null} onChange={noop} />);
    expect(screen.getAllByRole("button").map((b) => b.textContent)).toEqual([ed.statusAction.unpublish, ed.statusAction.archive]);
  });
  it("archived offers Restore as draft only", () => {
    renderWithI18n(<StatusControl status="archived" canPublish dirty={false} pending={null} onChange={noop} />);
    expect(screen.getAllByRole("button").map((b) => b.textContent)).toEqual([ed.statusAction.restore]);
  });
  it("is disabled with a reason for staff without catalog.publish", () => {
    renderWithI18n(<StatusControl status="draft" canPublish={false} dirty={false} pending={null} onChange={noop} />);
    for (const b of screen.getAllByRole("button")) expect(b).toBeDisabled();
    expect(screen.getByText(ed.noPublishPermission)).toBeInTheDocument();
  });
  it("asks to save first when there are unsaved edits", () => {
    renderWithI18n(<StatusControl status="draft" canPublish dirty pending={null} onChange={noop} />);
    expect(screen.getByRole("button", { name: ed.statusAction.publish })).toBeDisabled();
    expect(screen.getByText(ed.saveFirst)).toBeInTheDocument();
  });
});

describe("ProductEditor (edit)", () => {
  it("on version_conflict keeps the user's edits and offers a reload", async () => {
    const user = userEvent.setup();
    catalog.updateProduct.mockRejectedValueOnce(
      new ApiError({ status: 409, code: "version_conflict", message: "", details: { current_version: 4 }, requestId: "r1" }),
    );
    catalog.product.mockResolvedValueOnce(detail({ title: "Cotton Kurta (new stock)", version: 4 }));
    renderWithI18n(<EditorForm initial={detail()} />);

    const title = screen.getByLabelText(ed.titleLabel);
    await user.clear(title);
    await user.type(title, "Handloom Kurta");
    await user.click(screen.getByRole("button", { name: ed.save }));

    expect(await screen.findByText(ed.conflictTitle)).toBeInTheDocument();
    expect(catalog.updateProduct).toHaveBeenCalledWith("p1", 3, { title: "Handloom Kurta" });
    expect(screen.getByLabelText(ed.titleLabel)).toHaveValue("Handloom Kurta");
    expect(catalog.updateVariant).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: ed.reload }));
    await waitFor(() => expect(screen.getByLabelText(ed.titleLabel)).toHaveValue("Cotton Kurta (new stock)"));
    expect(screen.queryByText(ed.conflictTitle)).not.toBeInTheDocument();
  });

  it("checks the version even when only a variant changed, then patches it in paisa", async () => {
    const user = userEvent.setup();
    catalog.updateProduct.mockResolvedValueOnce(detail({ version: 3 }));
    catalog.updateVariant.mockResolvedValueOnce(detail({ version: 4 }));
    renderWithI18n(<EditorForm initial={detail()} />);
    const price = screen.getByLabelText(`${ed.colPrice} · M`);
    await user.clear(price);
    await user.type(price, "1,299.99");
    await user.click(screen.getByRole("button", { name: ed.save }));
    await waitFor(() => expect(catalog.updateVariant).toHaveBeenCalledWith("p1", "v-M", { price_minor: 129999 }, 3));
    expect(catalog.updateProduct).toHaveBeenCalledWith("p1", 3, {});
  });

  it("stops and shows the conflict banner when a variant write hits a newer version", async () => {
    const user = userEvent.setup();
    catalog.updateProduct.mockResolvedValueOnce(detail({ version: 3 }));
    catalog.updateVariant.mockRejectedValueOnce(new ApiError({ status: 409, code: "version_conflict", message: "", details: { current_version: 5 } }));
    renderWithI18n(<EditorForm initial={detail()} />);
    await user.clear(screen.getByLabelText(`${ed.colPrice} · M`));
    await user.type(screen.getByLabelText(`${ed.colPrice} · M`), "1300");
    await user.clear(screen.getByLabelText(`${ed.colPrice} · L`));
    await user.type(screen.getByLabelText(`${ed.colPrice} · L`), "1400");
    await user.click(screen.getByRole("button", { name: ed.save }));
    expect(await screen.findByText(ed.conflictTitle)).toBeInTheDocument();
    expect(catalog.updateVariant).toHaveBeenCalledTimes(1); // stopped at the conflict
    expect(screen.getByLabelText(`${ed.colPrice} · L`)).toHaveValue("1400");
  });

  it("adds and removes collection membership immediately", async () => {
    const user = userEvent.setup();
    catalog.collections.mockResolvedValue({ items: [{ id: "col1", title: "Dashain sale", handle: "dashain-sale", description: null }] });
    renderWithI18n(<EditorForm initial={detail()} />);
    const box = await screen.findByRole("checkbox", { name: "Dashain sale" });
    await user.click(box);
    await waitFor(() => expect(catalog.addToCollection).toHaveBeenCalledWith("col1", "p1"));
    await user.click(screen.getByRole("checkbox", { name: "Dashain sale" }));
    await waitFor(() => expect(catalog.removeFromCollection).toHaveBeenCalledWith("col1", "p1"));
  });

  it("shows variant errors in the right cell and keeps unsaved edits after a partial save", async () => {
    const user = userEvent.setup();
    catalog.updateProduct.mockResolvedValueOnce(detail());
    catalog.updateVariant.mockRejectedValueOnce(new ApiError({ status: 400, code: "invalid_barcode", message: "" }));
    renderWithI18n(<EditorForm initial={detail()} />);
    const barcode = screen.getByLabelText(`${ed.colBarcode} · L`);
    await user.type(barcode, "SHOP-0042");
    await user.click(screen.getByRole("button", { name: ed.save }));
    expect(await screen.findByText(en.errors.invalid_barcode)).toBeInTheDocument();
    expect(screen.getByText(ed.partialSave)).toBeInTheDocument();
    expect(screen.getByLabelText(`${ed.colBarcode} · L`)).toHaveValue("SHOP-0042");
  });

  it("blocks saving with a bad GTIN check digit before calling the API", async () => {
    const user = userEvent.setup();
    renderWithI18n(<EditorForm initial={detail()} />);
    await user.type(screen.getByLabelText(`${ed.colBarcode} · M`), "4006381333932");
    await user.click(screen.getByRole("button", { name: ed.save }));
    expect(await screen.findByText(ed.err.barcode_checksum)).toBeInTheDocument();
    expect(catalog.updateProduct).not.toHaveBeenCalled();
  });

  it("turns not_publishable into a checklist linking to each section", async () => {
    const user = userEvent.setup();
    catalog.setStatus.mockRejectedValueOnce(
      new ApiError({ status: 400, code: "not_publishable", message: "", details: { problems: ["price_required", "unconfirmed_ai_attributes"] } }),
    );
    renderWithI18n(<EditorForm initial={detail()} />);
    await user.click(screen.getByRole("button", { name: ed.statusAction.publish }));
    const list = await screen.findByTestId("publish-checklist");
    expect(within(list).getByRole("link", { name: ed.problem.price_required })).toHaveAttribute("href", "#variants");
    expect(within(list).getByRole("link", { name: ed.problem.unconfirmed_ai_attributes })).toHaveAttribute("href", "#attributes");
    expect(catalog.setStatus).toHaveBeenCalledWith("p1", "active", 3);
  });

  it("marks unconfirmed AI attributes and confirms them", async () => {
    const user = userEvent.setup();
    const withAi = detail({
      needs_review: true,
      attributes: [
        { key: "material", value: "Cotton", locale: "en", source: "ai", confidence: 0.62, confirmed: false },
        { key: "fit", value: "Regular", locale: "en", source: "seller", confidence: null, confirmed: true },
      ],
    });
    catalog.confirmAttributes.mockResolvedValueOnce({
      ...withAi,
      needs_review: false,
      attributes: withAi.attributes.map((a) => ({ ...a, confirmed: true })),
    });
    renderWithI18n(<EditorForm initial={withAi} />);
    expect(screen.getByText("Suggested by AI · 62% sure")).toBeInTheDocument();
    expect(screen.getByText(ed.source.seller)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: ed.confirm }));
    expect(catalog.confirmAttributes).toHaveBeenCalledWith("p1", ["material"]);
    await waitFor(() => expect(screen.queryByText("Suggested by AI · 62% sure")).not.toBeInTheDocument());
  });
});

describe("ProductEditor (create)", () => {
  it("generates a 2×2 grid and sends exact paisa with an idempotency key", async () => {
    const user = userEvent.setup();
    catalog.createProduct.mockResolvedValueOnce(detail({ id: "new1" }));
    renderWithI18n(<EditorForm initial={null} />);
    await user.type(screen.getByLabelText(ed.titleLabel), "Cotton Kurta");
    // Price typed before options carries into every generated row.
    await user.type(screen.getByLabelText(`${ed.colPrice} · ${ed.defaultVariant}`), "1250.50");

    await user.click(screen.getByRole("button", { name: ed.addOption }));
    await user.type(screen.getByLabelText(ed.optionName), "Size");
    await user.type(screen.getByLabelText(ed.optionValues), "M{Enter}L{Enter}");
    await user.click(screen.getByRole("button", { name: ed.addOption }));
    await user.type(screen.getAllByLabelText(ed.optionName)[1]!, "Colour");
    await user.type(screen.getAllByLabelText(ed.optionValues)[1]!, "Maroon{Enter}Black{Enter}");

    const grid = screen.getByTestId("variant-grid");
    expect(within(grid).getAllByRole("row")).toHaveLength(5); // header + 4
    await user.click(screen.getByRole("button", { name: ed.create }));

    await waitFor(() => expect(catalog.createProduct).toHaveBeenCalled());
    const [body, opts] = catalog.createProduct.mock.calls[0]!;
    expect(body.options).toEqual([
      { name: "Size", values: ["M", "L"] },
      { name: "Colour", values: ["Maroon", "Black"] },
    ]);
    expect(body.variants).toHaveLength(4);
    expect(body.variants.every((v: { price_minor: number }) => v.price_minor === 125050)).toBe(true);
    expect(opts.idempotencyKey).toEqual(expect.any(String));
  });

  it("shows the plan-limit panel on usage_limit_reached", async () => {
    const user = userEvent.setup();
    catalog.createProduct.mockRejectedValueOnce(
      new ApiError({ status: 402, code: "usage_limit_reached", message: "", details: { resource: "products", options: ["upgrade"] } }),
    );
    renderWithI18n(<EditorForm initial={null} />);
    await user.type(screen.getByLabelText(ed.titleLabel), "Dhaka Topi");
    await user.type(screen.getByLabelText(`${ed.colPrice} · ${ed.defaultVariant}`), "650");
    await user.click(screen.getByRole("button", { name: ed.create }));
    expect(await screen.findByText(ed.planLimitTitle)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: en.usage.upgrade })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: en.usage.buyCredits })).not.toBeInTheDocument();
  });

  it("is a permission state for users without catalog.write", () => {
    permissions = new Set(["catalog.read"]);
    renderWithI18n(<EditorForm initial={null} />);
    expect(screen.getByText(en.states.permissionTitle)).toBeInTheDocument();
  });
});
