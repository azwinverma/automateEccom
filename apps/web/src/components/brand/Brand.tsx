/**
 * Nivaro brand primitives. Geometry comes from @commerce-os/design-system/brand/geometry (the same source
 * that renders assets/brand/**), colours from semantic tokens. Rules: specs/26_NIVARO_BRAND_SYSTEM.md.
 *
 * - NivaroMark / NivaroLogo: the N-loop and the lockup. Never recolour, stretch or add effects.
 * - NTrail: the ribbon motif. Decorative only (aria-hidden). Expressive surfaces only (26 §29 matrix).
 * - CommerceLoop: Create → Sell → Fulfill → Learn, the trail with labelled stages.
 * - HandUnderline: the one hand-drawn accent allowed in product UI (onboarding, milestones).
 */
import { FLOW, MARK, WORDMARK, trailSegments, type Seg } from "@commerce-os/design-system/brand/geometry";
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

function MarkPaths({ tone }: { tone: "color" | "mono" }) {
  const id = useId().replace(/:/g, "");
  const r = { strokeWidth: 12, strokeLinecap: "round" as const, fill: "none" };
  if (tone === "mono") {
    return (
      <>
        <defs>
          <mask id={`${id}m`} maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">
            <rect width="64" height="64" fill="#fff" />
            <path d={MARK.monoFolds} stroke="#000" strokeWidth={2.2} strokeLinecap="round" />
          </mask>
        </defs>
        <g stroke="currentColor" {...r}>
          <path d={ln(MARK.diagonal)} mask={`url(#${id}m)`} />
          <path d={ln(MARK.left)} />
          <path d={ln(MARK.right)} />
        </g>
      </>
    );
  }
  const grad = (n: string, s: Seg, a: string, b: string) => (
    <linearGradient id={`${id}${n}`} x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2} gradientUnits="userSpaceOnUse">
      <stop offset="0" stopColor={a} />
      <stop offset="1" stopColor={b} />
    </linearGradient>
  );
  return (
    <>
      <defs>
        {grad("a", MARK.left, FLOW.start, FLOW.mid1)}
        {grad("b", MARK.diagonal, FLOW.mid1, FLOW.mid2)}
        {grad("c", MARK.right, FLOW.mid2, FLOW.end)}
        <FoldGradient id={`${id}f`} s={MARK.diagonal} />
      </defs>
      <path d={ln(MARK.diagonal)} stroke={`url(#${id}b)`} {...r} />
      <path d={ln(MARK.diagonal)} stroke={`url(#${id}f)`} {...r} />
      <path d={ln(MARK.left)} stroke={`url(#${id}a)`} {...r} />
      <path d={ln(MARK.right)} stroke={`url(#${id}c)`} {...r} />
    </>
  );
}

/** The N-loop. `title` makes it a labelled image; omit it when a visible name sits next to it. */
export function NivaroMark({ size = 24, tone = "color", title }: { size?: number; tone?: "color" | "mono"; title?: string }) {
  return (
    <svg
      className={styles.mark}
      width={size}
      height={size}
      viewBox={MARK.viewBox}
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      <MarkPaths tone={tone} />
    </svg>
  );
}

function Wordmark({ height }: { height: number }) {
  return (
    <svg className={styles.wordmark} height={height} width={(height * 150) / 46} viewBox={WORDMARK.viewBox} aria-hidden="true">
      <g stroke="currentColor" fill="none" strokeWidth={WORDMARK.stroke} strokeLinecap="round" strokeLinejoin="round">
        {WORDMARK.paths.map((d) => (
          <path key={d} d={d} />
        ))}
        {WORDMARK.circles.map((c) => (
          <circle key={c.cx} cx={c.cx} cy={c.cy} r={c.r} />
        ))}
      </g>
      <circle cx={WORDMARK.dot.cx} cy={WORDMARK.dot.cy} r={WORDMARK.dot.r} fill="currentColor" />
    </svg>
  );
}

/**
 * Mark + wordmark. The wordmark takes `currentColor` (ink on light, white on navy) so it follows the
 * surface; the mark keeps the brand gradient unless `tone="mono"`. `product` adds a module name
 * (e.g. Console) in the UI type, never in the wordmark geometry.
 */
export function NivaroLogo({
  height = 24,
  tone = "color",
  product,
  label = "Nivaro",
}: {
  height?: number;
  tone?: "color" | "mono";
  product?: string;
  label?: string;
}) {
  return (
    <span className={styles.logo} role="img" aria-label={product ? `${label} ${product}` : label}>
      <NivaroMark size={height} tone={tone} />
      <Wordmark height={height * 0.72} />
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
