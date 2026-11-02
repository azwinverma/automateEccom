import type { ProductDetail } from "@commerce-os/api-client";
import { describe, expect, it } from "vitest";
import { minorToRupeesInput, parseRupees } from "../money";
import { barcodeProblem, gtinValid, normalizeSku } from "./codes";
import { csvCell, errorsCsv, IMPORT_HEADERS, templateCsv } from "./csv";
import { buildCreateBody, diffProduct, diffVariants, emptyForm, formFromDetail, newRow, validateForm } from "./editor";
import { allowedTransitions, parseProblems, PROBLEM_SECTION, transitionAction } from "./status";
import { combinationCount, combinations, comboKey, syncRows, variantTitle } from "./variants";

describe("rupees ↔ paisa", () => {
  it.each([
    ["1250", 125000],
    ["1,250.50", 125050],
    ["1250.5", 125050],
    ["19.99", 1999], // 19.99 * 100 === 1998.9999999999998 in floats
    ["0.07", 7],
    [".5", 50],
    ["Rs 1,250", 125000],
    ["Rs. 99", 9900],
    ["रू 1,250", 125000],
    ["रू १२५०", 125000],
    ["NPR 10", 1000],
    ["0", 0],
    ["007", 700],
    ["100000000", 10_000_000_000],
  ])("%s → %i paisa", (input, minor) => {
    expect(parseRupees(input)).toEqual({ ok: true, minor });
  });

  it("treats blank as no value", () => {
    expect(parseRupees("  ")).toEqual({ ok: true, minor: null });
  });

  it.each([
    ["12.345", "decimals"],
    ["-5", "negative"],
    ["12abc", "invalid"],
    ["1.2.3", "invalid"],
    ["1e5", "invalid"],
    ["100000000.01", "too_large"],
    ["99999999999999999", "too_large"],
  ])("rejects %s (%s)", (input, error) => {
    expect(parseRupees(input)).toEqual({ ok: false, error });
  });

  it.each([
    [125000, "1250"],
    [125050, "1250.50"],
    [125005, "1250.05"],
    [7, "0.07"],
    [0, "0"],
    [null, ""],
  ])("%s paisa → %s", (minor, text) => {
    expect(minorToRupeesInput(minor)).toBe(text);
  });

  it("round-trips without drift", () => {
    for (const minor of [1, 99, 1999, 125050, 9_999_999_999]) {
      expect(parseRupees(minorToRupeesInput(minor))).toEqual({ ok: true, minor });
    }
  });
});

describe("variant combinations", () => {
  const size = { name: "Size", values: ["M", "L"] };
  const colour = { name: "Colour", values: ["Maroon", "Black"] };

  it("builds the cartesian product in option order", () => {
    expect(combinations([size, colour])).toEqual([
      { Size: "M", Colour: "Maroon" },
      { Size: "M", Colour: "Black" },
      { Size: "L", Colour: "Maroon" },
      { Size: "L", Colour: "Black" },
    ]);
    expect(combinationCount([size, colour, { name: "Fabric", values: ["Cotton", "Silk", "Linen"] }])).toBe(12);
  });

  it("returns one default combination without options and ignores empty/duplicate values", () => {
    expect(combinations([])).toEqual([{}]);
    expect(combinations([{ name: "Size", values: [" M ", "m", ""] }, { name: "", values: ["x"] }])).toEqual([{ Size: "M" }]);
  });

  it("titles and keys combinations", () => {
    expect(variantTitle({ Size: "M", Colour: "Maroon" }, ["Size", "Colour"])).toBe("M / Maroon");
    expect(comboKey({ Size: "M", Colour: "Maroon" }, ["Size", "Colour"])).toBe("m / maroon");
    expect(comboKey({}, [])).toBe("default");
  });

  it("keeps typed prices when options change, drops vanished combos, respects exclusions", () => {
    let rows = syncRows([], [size], [], newRow);
    rows = rows.map((r) => (r.options.Size === "M" ? { ...r, price: "1250" } : r));
    // Add a second option: M rows split; typed price is not invented for new combos.
    const withColour = syncRows(rows, [size, colour], [], newRow);
    expect(withColour).toHaveLength(4);
    // Rename an option: rows keyed by values survive.
    const renamed = syncRows(rows, [{ name: "Sizes", values: ["M", "L"] }], [], newRow);
    expect(renamed.find((r) => r.options.Sizes === "M")?.price).toBe("1250");
    // Remove value L and exclude nothing: only M stays, with its price.
    expect(syncRows(rows, [{ name: "Size", values: ["M"] }], [], newRow).map((r) => r.price)).toEqual(["1250"]);
    // Excluded combinations are not regenerated.
    expect(syncRows(rows, [size], ["l"], newRow).map((r) => r.options.Size)).toEqual(["M"]);
  });
});

describe("status transitions", () => {
  it("offers only the backend's allowed moves", () => {
    expect(allowedTransitions("draft")).toEqual(["active", "archived"]);
    expect(allowedTransitions("active")).toEqual(["draft", "archived"]);
    expect(allowedTransitions("archived")).toEqual(["draft"]);
  });
  it("names each move", () => {
    expect(transitionAction("draft", "active")).toBe("publish");
    expect(transitionAction("active", "draft")).toBe("unpublish");
    expect(transitionAction("active", "archived")).toBe("archive");
    expect(transitionAction("archived", "draft")).toBe("restore");
  });
  it("parses not_publishable problems and links them to sections", () => {
    expect(parseProblems({ problems: ["price_required", "nope", "unconfirmed_ai_attributes"] })).toEqual([
      "price_required",
      "unconfirmed_ai_attributes",
    ]);
    expect(PROBLEM_SECTION.price_required).toBe("variants");
    expect(PROBLEM_SECTION.unconfirmed_ai_attributes).toBe("attributes");
  });
});

describe("SKU and barcode rules", () => {
  it("validates GTIN check digits like the backend", () => {
    expect(gtinValid("4006381333931")).toBe(true);
    expect(gtinValid("4006381333932")).toBe(false);
    expect(gtinValid("96385074")).toBe(true);
    expect(barcodeProblem("4006381333932")).toBe("checksum");
    expect(barcodeProblem("SHOP-0042")).toBeNull();
    expect(barcodeProblem("ab")).toBe("format");
    expect(barcodeProblem("")).toBeNull();
  });
  it("normalises SKUs", () => {
    expect(normalizeSku(" red kurta m ")).toBe("RED-KURTA-M");
  });
});

describe("editor form", () => {
  it("validates prices, compare-at, SKUs and barcodes per row", () => {
    const f = emptyForm();
    f.title = "Kurta";
    f.variants = [
      { ...newRow({ Size: "M" }, "m"), price: "", sku: "A 1" },
      { ...newRow({ Size: "L" }, "l"), price: "1250", compareAt: "1000", sku: "a-1", barcode: "4006381333932" },
    ];
    const e = validateForm(f, "create");
    expect(e["variants.m.price"]).toBe("required");
    expect(e["variants.l.compareAt"]).toBe("compare_at_not_higher");
    expect(e["variants.l.sku"]).toBe("duplicate_sku");
    expect(e["variants.l.barcode"]).toBe("barcode_checksum");
  });

  it("builds an exact create body", () => {
    const f = emptyForm();
    f.title = " Cotton Kurta ";
    f.title_ne = "सुती कुर्ता";
    f.options = [{ name: "Size", values: ["M"] }];
    f.variants = [{ ...newRow({ Size: "M" }, "m"), price: "1,250.50", cost: "700", sku: "kurta m" }];
    f.weight = "300";
    expect(validateForm(f, "create")).toEqual({});
    expect(buildCreateBody(f)).toEqual({
      title: "Cotton Kurta",
      title_ne: "सुती कुर्ता",
      tags: [],
      options: [{ name: "Size", values: ["M"] }],
      variants: [{ options: { Size: "M" }, price_minor: 125050, cost_minor: 70000, sku: "KURTA-M", weight_grams: 300 }],
      handle: undefined,
      description: undefined,
      description_ne: undefined,
      category_id: undefined,
      brand: undefined,
      product_type: undefined,
    });
  });

  it("diffs only changed fields and stages variant archives", () => {
    const detail: ProductDetail = {
      id: "p1",
      title: "Kurta",
      title_ne: null,
      handle: "kurta",
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
      created_at: "",
      updated_at: "",
      options: [{ id: "o1", name: "Size", values: ["M", "L"] }],
      variants: ["M", "L"].map((s, i) => ({
        id: `v${i}`,
        title: s,
        sku: `KURTA-${s}`,
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
    };
    const base = formFromDetail(detail);
    const form = structuredClone(base);
    form.title_ne = "कुर्ता";
    form.variants[0]!.price = "1300";
    form.variants[1]!.remove = true;
    expect(diffProduct(base, form)).toEqual({ title_ne: "कुर्ता" });
    expect(diffVariants(base, form)).toEqual({
      patches: [{ id: "v0", key: "v0", body: { price_minor: 130000 } }],
      archives: [{ id: "v1", key: "v1" }],
    });
  });
});

describe("CSV helpers", () => {
  it("has the backend's import headers and a parseable template", () => {
    const [header] = templateCsv().split("\r\n");
    expect(header).toBe(IMPORT_HEADERS.join(","));
    expect(IMPORT_HEADERS).toContain("price");
  });
  it("escapes cells and neutralises formulas in exported errors", () => {
    expect(csvCell('say "hi", ok')).toBe('"say ""hi"", ok"');
    expect(csvCell("=HYPERLINK(1)")).toBe("'=HYPERLINK(1)");
    expect(errorsCsv([{ row: 4, handle: "kurta", code: "invalid_row", message: "price: 'x' is not a number" }], ["Row", "Handle", "Code", "Message"]))
      .toBe("Row,Handle,Code,Message\r\n4,kurta,invalid_row,price: 'x' is not a number\r\n");
  });
});
