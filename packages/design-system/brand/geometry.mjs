// Nivaro brand geometry: the single source for the N-loop mark, the wordmark and the ribbon motifs.
// Used by the web components (apps/web/src/components/brand) and by assets/brand/scripts/render.mjs,
// which writes the static SVG/PNG files. Rules: specs/26_NIVARO_BRAND_SYSTEM.md §4 and §10.

/** Ribbon width in mark units (viewBox 64). Motifs reuse the same proportion: width = 12/64 of the mark height. */
export const RIBBON = 12;

/**
 * The N-loop: one ribbon that rises (create), crosses (sell → fulfil) and rises again (learn).
 * Draw order matters: the diagonal is drawn first so both stems fold over it.
 */
export const MARK = {
  viewBox: "0 0 64 64",
  diagonal: { x1: 24, y1: 16, x2: 40, y2: 48 },
  left: { x1: 14, y1: 50, x2: 24, y2: 16 },
  right: { x1: 40, y1: 48, x2: 50, y2: 14 },
  /** Short separation strokes used by the single-colour mark to keep the fold legible (masked out of the diagonal). */
  monoFolds: "M30.4 17.2 L28.6 23.4 M33.6 46.8 L35.4 40.6",
};

/** Gradient stops along the ribbon (Nivaro Blue → Teal). Mid stops are interpolations, not new brand colours. */
export const FLOW = { start: "#2563EB", mid1: "#2F7BEF", mid2: "#16A9B8", end: "#14B8A6", fold: "#0F172A" };

/** Wordmark "nivaro": stroked geometry (no font dependency), viewBox 0 0 150 46, stroke 6.4, x-height 23. */
export const WORDMARK = {
  viewBox: "0 0 150 46",
  stroke: 6.4,
  paths: [
    "M4 17V40M4 26.5A9 9 0 0 1 22 26.5V40",
    "M32 17V40",
    "M41.5 17L51.5 40L61.5 17",
    "M92.3 17V40",
    "M103.5 17V40M103.5 29C103.5 21 108.5 17 116 17",
  ],
  circles: [
    { cx: 81, cy: 28.5, r: 11.3 },
    { cx: 134.5, cy: 28.5, r: 11.3 },
  ],
  dot: { cx: 32, cy: 6.6, r: 3.9 },
};

/**
 * N-trail motif: the mark's zig-zag continued — the commerce loop keeps going.
 * Returns ribbon segments for `count` rises, starting bottom-left. Same angles as the mark
 * (rise: dx 10 / dy 34, cross: dx 16 / dy 32) scaled to `height`.
 * @param {{count:number, height:number, x?:number, y?:number}} o
 */
export function trailSegments({ count, height, x = 0, y = 0 }) {
  const s = height / 36; // mark: a rise spans 34 units + ribbon caps
  const rise = { dx: 10 * s, dy: -34 * s };
  const cross = { dx: 16 * s, dy: 32 * s }; // +2 keeps every peak level (34 down after a 34 rise)
  const segs = [];
  let px = x + RIBBON * s * 0.5;
  let py = y + height - RIBBON * s * 0.5 + 0.0001;
  for (let i = 0; i < count; i++) {
    segs.push({ kind: "rise", x1: px, y1: py, x2: px + rise.dx, y2: py + rise.dy });
    px += rise.dx;
    py += rise.dy;
    if (i < count - 1) {
      segs.push({ kind: "cross", x1: px, y1: py, x2: px + cross.dx, y2: py + cross.dy + 2 * s });
      px += cross.dx;
      py += cross.dy + 2 * s;
    }
  }
  return { segments: segs, width: px - x + RIBBON * s * 0.5, ribbon: RIBBON * s };
}

/** The loop stages. Order is the product promise: Create → Sell → Fulfill → Learn (specs/26 §10). */
export const LOOP_STAGES = ["create", "sell", "fulfill", "learn"];
