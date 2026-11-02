// Nivaro ribbon-motif geometry (N-trail, commerce loop, empty-state trail), derived from the logo's
// rise/cross angles. Used by apps/web/src/components/brand and assets/brand/scripts/render.mjs.
// Rules: specs/26_NIVARO_BRAND_SYSTEM.md §8.

/** Ribbon width in motif units (a rise is 34 units tall): matches the logo ribbon's proportion. */
export const RIBBON = 12;

/** Ribbon gradient (Nivaro Blue → Teal) for motifs. The logo itself is the approved artwork in
 * assets/brand/logo/source (ADR-032); it is not redrawn here. */
export const FLOW = { start: "#2563EB", mid1: "#2F7BEF", mid2: "#16A9B8", end: "#14B8A6", fold: "#0F172A" };

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
