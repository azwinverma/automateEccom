import type {
  ProductCreateInput,
  ProductDetail,
  ProductPatchInput,
  VariantInput,
  VariantPatchInput,
} from "@commerce-os/api-client";
import { minorToRupeesInput, parseRupees, type MoneyError } from "../money";
import { HANDLE_RE, SKU_RE, barcodeProblem, normalizeSku } from "./codes";
import { MAX_OPTIONS, MAX_VALUES_PER_OPTION, MAX_VARIANTS, cleanOptions, combinationCount, comboKey, type OptionDraft } from "./variants";

export interface VariantRow {
  /** Server id for saved variants, combination key for new rows. */
  key: string;
  id?: string;
  options: Record<string, string>;
  price: string;
  compareAt: string;
  cost: string;
  sku: string;
  barcode: string;
  status: "active" | "archived";
  /** Saved variant marked for archiving on the next save. */
  remove: boolean;
}

export interface ProductForm {
  title: string;
  title_ne: string;
  description: string;
  description_ne: string;
  handle: string;
  category_id: string;
  brand: string;
  product_type: string;
  tags: string[];
  options: OptionDraft[];
  variants: VariantRow[];
  /** Combination keys the seller removed from the grid (create mode). */
  excluded: string[];
  weight: string;
  length: string;
  width: string;
  height: string;
}

export function newRow(combo: Record<string, string>, key: string): VariantRow {
  return { key, options: combo, price: "", compareAt: "", cost: "", sku: "", barcode: "", status: "active", remove: false };
}

export function emptyForm(): ProductForm {
  return {
    title: "",
    title_ne: "",
    description: "",
    description_ne: "",
    handle: "",
    category_id: "",
    brand: "",
    product_type: "",
    tags: [],
    options: [],
    variants: [newRow({}, "default")],
    excluded: [],
    weight: "",
    length: "",
    width: "",
    height: "",
  };
}

const str = (v: string | null | undefined) => v ?? "";
const intStr = (v: number | null | undefined) => (v === null || v === undefined ? "" : String(v));

export function formFromDetail(d: ProductDetail): ProductForm {
  const firstActive = d.variants.find((v) => v.status === "active") ?? d.variants[0];
  const [length, width, height] = firstActive?.dimensions_mm ?? [];
  return {
    title: d.title,
    title_ne: str(d.title_ne),
    description: str(d.description),
    description_ne: str(d.description_ne),
    handle: d.handle,
    category_id: str(d.category_id),
    brand: str(d.brand),
    product_type: str(d.product_type),
    tags: [...(d.tags ?? [])],
    options: d.options.map((o) => ({ name: o.name, values: [...o.values] })),
    variants: d.variants.map((v) => ({
      key: v.id,
      id: v.id,
      options: { ...v.options },
      price: minorToRupeesInput(v.price.amount_minor),
      compareAt: minorToRupeesInput(v.compare_at?.amount_minor),
      cost: minorToRupeesInput(v.cost?.amount_minor),
      sku: v.sku ?? "",
      barcode: v.barcode ?? "",
      status: v.status,
      remove: false,
    })),
    excluded: [],
    weight: intStr(firstActive?.weight_grams),
    length: intStr(length),
    width: intStr(width),
    height: intStr(height),
  };
}

/* ---------- Validation ---------- */

export type FormErrorKind =
  | "required"
  | MoneyError
  | "compare_at_not_higher"
  | "invalid_sku"
  | "duplicate_sku"
  | "barcode_checksum"
  | "barcode_format"
  | "handle_format"
  | "option_name_required"
  | "option_duplicate"
  | "option_values_required"
  | "too_many_values"
  | "too_many_options"
  | "too_many_variants"
  | "no_variants"
  | "whole_number";

/** Keys: `title`, `handle`, `options.<i>.name`, `variants.<rowKey>.<field>`, `variants`, `weight`… */
export type FormErrors = Record<string, FormErrorKind>;

const WHOLE = /^\d{1,7}$/;

export function validateForm(form: ProductForm, mode: "create" | "edit"): FormErrors {
  const e: FormErrors = {};
  if (!form.title.trim()) e.title = "required";
  if (form.handle.trim() && !HANDLE_RE.test(form.handle.trim())) e.handle = "handle_format";

  if (mode === "create") {
    if (form.options.length > MAX_OPTIONS) e.options = "too_many_options";
    const names = new Set<string>();
    form.options.forEach((o, i) => {
      const name = o.name.trim().toLowerCase();
      if (!name) e[`options.${i}.name`] = "option_name_required";
      else if (names.has(name)) e[`options.${i}.name`] = "option_duplicate";
      names.add(name);
      if (cleanOptions([o]).length === 0 && o.name.trim()) e[`options.${i}.values`] = "option_values_required";
      if (o.values.length > MAX_VALUES_PER_OPTION) e[`options.${i}.values`] = "too_many_values";
    });
  }

  const live = form.variants.filter((v) => v.status === "active" && !v.remove);
  if (live.length === 0) e.variants = "no_variants";
  const planned = mode === "create" ? combinationCount(form.options) - form.excluded.length : form.variants.length;
  if (planned > MAX_VARIANTS || form.variants.length > MAX_VARIANTS) e.variants = "too_many_variants";

  const skus = new Map<string, string>();
  for (const v of live) {
    const k = `variants.${v.key}`;
    const price = parseRupees(v.price);
    if (!price.ok) e[`${k}.price`] = price.error;
    else if (price.minor === null) e[`${k}.price`] = "required";
    const compare = parseRupees(v.compareAt);
    if (!compare.ok) e[`${k}.compareAt`] = compare.error;
    else if (compare.minor !== null && price.ok && price.minor !== null && compare.minor <= price.minor)
      e[`${k}.compareAt`] = "compare_at_not_higher";
    const cost = parseRupees(v.cost);
    if (!cost.ok) e[`${k}.cost`] = cost.error;
    if (v.sku.trim()) {
      const sku = normalizeSku(v.sku);
      if (!SKU_RE.test(sku)) e[`${k}.sku`] = "invalid_sku";
      else if (skus.has(sku)) e[`${k}.sku`] = "duplicate_sku";
      skus.set(sku, v.key);
    }
    const bp = barcodeProblem(v.barcode);
    if (bp) e[`${k}.barcode`] = bp === "checksum" ? "barcode_checksum" : "barcode_format";
  }

  for (const f of ["weight", "length", "width", "height"] as const) {
    if (form[f].trim() && !WHOLE.test(form[f].trim())) e[f] = "whole_number";
  }
  return e;
}

/* ---------- Mapping to API bodies (call only after validateForm passes) ---------- */

const minorOf = (s: string): number | null => {
  const p = parseRupees(s);
  return p.ok ? p.minor : null;
};
const intOf = (s: string): number | null => (s.trim() ? Number(s.trim()) : null);
const optStr = (s: string): string | undefined => (s.trim() ? s.trim() : undefined);

function shipping(form: ProductForm): Pick<VariantInput, "weight_grams" | "length_mm" | "width_mm" | "height_mm"> {
  const out: Pick<VariantInput, "weight_grams" | "length_mm" | "width_mm" | "height_mm"> = {};
  const w = intOf(form.weight);
  const l = intOf(form.length);
  const wd = intOf(form.width);
  const h = intOf(form.height);
  if (w !== null) out.weight_grams = w;
  if (l !== null) out.length_mm = l;
  if (wd !== null) out.width_mm = wd;
  if (h !== null) out.height_mm = h;
  return out;
}

export function buildCreateBody(form: ProductForm): ProductCreateInput {
  const options = cleanOptions(form.options);
  const ship = shipping(form);
  return {
    title: form.title.trim(),
    handle: optStr(form.handle),
    description: optStr(form.description),
    title_ne: optStr(form.title_ne),
    description_ne: optStr(form.description_ne),
    category_id: optStr(form.category_id),
    brand: optStr(form.brand),
    product_type: optStr(form.product_type),
    tags: form.tags,
    options,
    variants: form.variants
      .filter((v) => !v.remove)
      .map((v) => {
        const body: VariantInput = { options: v.options, price_minor: minorOf(v.price) ?? 0, ...ship };
        const compare = minorOf(v.compareAt);
        const cost = minorOf(v.cost);
        if (compare !== null) body.compare_at_minor = compare;
        if (cost !== null) body.cost_minor = cost;
        if (v.sku.trim()) body.sku = normalizeSku(v.sku);
        if (v.barcode.trim()) body.barcode = v.barcode.trim().replace(/ /g, "");
        return body;
      }),
  };
}

const PRODUCT_FIELDS = ["title", "title_ne", "description", "description_ne", "handle", "brand", "product_type"] as const;

/** Product-level fields that differ from the saved version. */
export function diffProduct(base: ProductForm, form: ProductForm): ProductPatchInput {
  const patch: ProductPatchInput = {};
  for (const f of PRODUCT_FIELDS) {
    if (base[f] !== form[f]) (patch as Record<string, string>)[f] = f === "title" ? form[f].trim() : form[f];
  }
  if (base.category_id !== form.category_id) patch.category_id = form.category_id || null;
  if (JSON.stringify(base.tags) !== JSON.stringify(form.tags)) patch.tags = form.tags;
  return patch;
}

export interface VariantChanges {
  patches: { id: string; key: string; body: VariantPatchInput }[];
  archives: { id: string; key: string }[];
}

/** Per-variant patches (prices, codes, shared shipping) and staged archives. */
export function diffVariants(base: ProductForm, form: ProductForm): VariantChanges {
  const baseByKey = new Map(base.variants.map((v) => [v.key, v]));
  const shipChanged = (["weight", "length", "width", "height"] as const).some((f) => base[f] !== form[f]);
  const out: VariantChanges = { patches: [], archives: [] };
  for (const v of form.variants) {
    if (!v.id || v.status !== "active") continue;
    if (v.remove) {
      out.archives.push({ id: v.id, key: v.key });
      continue;
    }
    const b = baseByKey.get(v.key);
    if (!b) continue;
    const body: VariantPatchInput = {};
    if (b.price !== v.price) body.price_minor = minorOf(v.price) ?? 0;
    if (b.compareAt !== v.compareAt) body.compare_at_minor = minorOf(v.compareAt);
    if (b.cost !== v.cost) body.cost_minor = minorOf(v.cost);
    if (b.sku !== v.sku && v.sku.trim()) body.sku = normalizeSku(v.sku);
    if (b.barcode !== v.barcode) body.barcode = v.barcode.trim() ? v.barcode.trim().replace(/ /g, "") : null;
    if (shipChanged) {
      body.weight_grams = intOf(form.weight);
      body.length_mm = intOf(form.length);
      body.width_mm = intOf(form.width);
      body.height_mm = intOf(form.height);
    }
    if (Object.keys(body).length) out.patches.push({ id: v.id, key: v.key, body });
  }
  return out;
}

export function sameForm(a: ProductForm, b: ProductForm): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export { comboKey };
