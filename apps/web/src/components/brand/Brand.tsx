/**
 * Nivaro brand primitives. Geometry comes from @commerce-os/design-system/brand/geometry (the same source
 * that renders assets/brand/**), colours from semantic tokens. Rules: specs/26_NIVARO_BRAND_SYSTEM.md.
 *
 * - NivaroMark / NivaroLogo: the approved logo artwork (public/brand). Never recolour, stretch or add effects.
 * - NTrail: the ribbon motif. Decorative only (aria-hidden). Expressive surfaces only (26 §29 matrix).
 * - CommerceLoop: Create → Sell → Fulfill → Learn, the trail with labelled stages.
 * - HandUnderline: the one hand-drawn accent allowed in product UI (onboarding, milestones).
 */
import { FLOW, trailSegments, type Seg } from "@commerce-os/design-system/brand/geometry";
import { useId, type CSSProperties, type ReactNode } from "react";
import styles from "./brand.module.css";

const ln = (s: Seg) => `M${s.x1} ${s.y1} L${s.x2} ${s.y2}`;

function FoldGradient({ id, s, a = 0.34, b = 0.22 }: { id: string; s: Seg; a?: number; b?: number }) {
  return (
    <linearGradient id={id} x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2} gradientUnits="userSpaceOnUse">
      <stop offset="0.08" stopColor={FLOW.fold} stopOpacity={a} />
      <stop offset="0.34" stopColor={FLOW.fold} stopOpacity={0} />
      <stop offset="0.66" stopColor={FLOW.fold} stopOpacity={0} />
      <stop offset="0.92" stopColor={FLOW.fold} stopOpacity={b} />
    </linearGradient>
  );
}

/** Logo artwork (owner-approved concept, ADR-032), served from /public/brand; regenerate with render.mjs. */
export const MARK_SRC = "/brand/nivaro-mark.png";
const MARK_RATIO = 384 / 263;
const WORD_RATIO = 724 / 201;

/** The N-loop mark. `size` is the height in px. `title` makes it a labelled image. */
export function NivaroMark({ size = 24, title }: { size?: number; title?: string }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element -- tiny static brand asset; next/image adds nothing here
    <img
      className={styles.mark}
      src={MARK_SRC}
      width={Math.round(size * MARK_RATIO)}
      height={size}
      alt={title ?? ""}
      aria-hidden={title ? undefined : true}
      decoding="async"
    />
  );
}

/** Wordmark: the artwork's alpha used as a mask filled with currentColor, so it follows light/dark. */
function Wordmark({ height }: { height: number }) {
  return <span className={styles.wordmark} style={{ height, width: height * WORD_RATIO }} aria-hidden="true" />;
}

/**
 * Mark + wordmark. The wordmark follows `--color-brand-ink` (ink on light, white on dark/navy).
 * `product` adds a module name (e.g. Console) in UI type, never baked into the logo artwork.
 */
export function NivaroLogo({ height = 24, product, label = "Nivaro" }: { height?: number; product?: string; label?: string }) {
  return (
    <span className={styles.logo} style={{ gap: Math.round(height * 0.3) }} role="img" aria-label={product ? `${label} ${product}` : label}>
      <NivaroMark size={height} />
      <Wordmark height={height * 0.6} />
      {product ? <span className={styles.product}>{product}</span> : null}
    </span>
  );
}

/** The ribbon motif. `animate` traces the ribbon once (e.g. while publishing); reduced motion shows it static. */
export function NTrail({
  count = 5,
  height = 120,
  fade = true,
  animate = false,
  className,
}: {
  count?: number;
  height?: number;
  fade?: boolean;
  animate?: boolean;
  className?: string;
}) {
  const id = useId().replace(/:/g, "");
  const t = trailSegments({ count, height });
  const pad = t.ribbon;
  const ordered = [...t.segments].sort((a, b) => (a.kind === b.kind ? 0 : a.kind === "cross" ? -1 : 1));
  const r = { strokeWidth: t.ribbon, strokeLinecap: "round" as const, fill: "none" };
  return (
    <svg
      className={[styles.trail, animate ? styles.trailAnimate : "", className ?? ""].join(" ")}
      viewBox={`0 ${-pad / 2} ${t.width} ${height + pad}`}
      preserveAspectRatio="xMinYMid meet"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={`${id}g`} x1="0" y1="0" x2={t.width} y2="0" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="var(--color-flow-start)" />
          <stop offset="1" stopColor="var(--color-flow-end)" />
        </linearGradient>
        {fade ? (
          <>
            <linearGradient id={`${id}fd`} x1="0" y1="0" x2={t.width} y2="0" gradientUnits="userSpaceOnUse">
              <stop offset="0" stopColor="#fff" stopOpacity="0" />
              <stop offset="0.2" stopColor="#fff" />
            </linearGradient>
            <mask id={`${id}mk`} maskUnits="userSpaceOnUse" x={-pad} y={-pad} width={t.width + 2 * pad} height={height + 2 * pad}>
              <rect x={-pad} y={-pad} width={t.width + 2 * pad} height={height + 2 * pad} fill={`url(#${id}fd)`} />
            </mask>
          </>
        ) : null}
        {t.segments.map((s, i) => (s.kind === "cross" ? <FoldGradient key={i} id={`${id}f${i}`} s={s} a={0.3} b={0.2} /> : null))}
      </defs>
      <g mask={fade ? `url(#${id}mk)` : undefined}>
        {ordered.map((s) => {
          const i = t.segments.indexOf(s);
          return (
            <g key={i} className={styles.seg} style={{ "--i": i } as CSSProperties}>
              <path d={ln(s)} stroke={`url(#${id}g)`} {...r} pathLength={1} />
              {s.kind === "cross" ? <path d={ln(s)} stroke={`url(#${id}f${i})`} {...r} pathLength={1} /> : null}
            </g>
          );
        })}
      </g>
    </svg>
  );
}

export interface LoopStage {
  key: string;
  label: string;
  detail?: string;
}

/** Create → Sell → Fulfill → Learn on the ribbon. Labels are real text (translatable, selectable). */
export function CommerceLoop({ stages, label, current }: { stages: LoopStage[]; label: string; current?: string }) {
  const height = 64;
  const t = trailSegments({ count: stages.length, height });
  const peaks = t.segments.filter((s) => s.kind === "rise");
  return (
    <figure className={styles.loop} aria-label={label}>
      <NTrail count={stages.length} height={height} fade={false} className={styles.loopTrail} />
      <ol className={styles.loopStages}>
        {stages.map((s, i) => (
          <li
            key={s.key}
            className={s.key === current ? styles.loopCurrent : undefined}
            aria-current={s.key === current ? "step" : undefined}
            style={{ "--x": `${((peaks[i]?.x2 ?? 0) / t.width) * 100}%` } as CSSProperties}
          >
            <span className={styles.loopName}>{s.label}</span>
            {s.detail ? <span className={styles.loopDetail}>{s.detail}</span> : null}
          </li>
        ))}
      </ol>
    </figure>
  );
}

/** Hand-drawn teal underline under one or two words. Onboarding, milestones, marketing only. */
export function HandUnderline({ children }: { children: ReactNode }) {
  return (
    <span className={styles.underline}>
      {children}
      <svg viewBox="0 0 200 20" preserveAspectRatio="none" aria-hidden="true">
        <path d="M3 13.6C42 6.4 118 3.6 195.4 8.2c2.4.2 2.6 3.2.2 3.5C131 9.2 63 11 5.2 17.4c-2.8.3-4.6-3.1-2.2-3.8Z" />
      </svg>
    </span>
  );
}

/** Hand-drawn arrow (ink). Points right by default; one per composition. Marketing/onboarding only. */
export function HandArrow({ className }: { className?: string }) {
  return (
    <svg className={[styles.handArrow, className ?? ""].join(" ")} viewBox="0 0 120 80" aria-hidden="true">
      <g fill="none" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
        <path className={styles.handDraw} pathLength={1} d="M6 70C20 34 52 14 98 18" />
        <path className={styles.handDraw} pathLength={1} d="M84 6 100 18 86 31" />
      </g>
    </svg>
  );
}

/** Hand-drawn coral ring around a word (celebration / emphasis). Marketing and milestones only. */
export function HandRing({ children }: { children: ReactNode }) {
  return (
    <span className={styles.ring}>
      {children}
      <svg viewBox="0 0 220 90" preserveAspectRatio="none" aria-hidden="true">
        <path className={styles.handDraw} pathLength={1} d="M128 8C70 2 10 18 8 46c-2 30 82 40 140 32 46-6 70-26 58-46C196 14 160 6 116 9" />
      </svg>
    </span>
  );
}

/** Hand-drawn strike-through ("not this"). Marketing only. */
export function HandStrike({ children }: { children: ReactNode }) {
  return (
    <span className={styles.strike}>
      {children}
      <svg viewBox="0 0 200 20" preserveAspectRatio="none" aria-hidden="true">
        <path className={styles.handDraw} pathLength={1} d="M2 12C50 9 120 7 198 6" />
      </svg>
    </span>
  );
}
