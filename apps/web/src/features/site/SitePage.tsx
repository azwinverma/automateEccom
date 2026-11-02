import { trailSegments } from "@commerce-os/design-system/brand/geometry";
import Link from "next/link";
import type { CSSProperties } from "react";
import { CommerceLoop, HandArrow, HandRing, HandStrike, HandUnderline, NTrail, NivaroLogo, NivaroMark } from "@/components/brand/Brand";
import { Icon } from "@/components/ui/Icon";
import { CountUp, Reveal, SiteHeader } from "./client";
import type { Avail, SiteCopy } from "./copy";
import styles from "./site.module.css";

/**
 * Public website (specs/26 §14: high energy). Layout: direction A "The loop" (docs/design/LAYOUT_DIRECTIONS.md §1).
 * Every product fragment is real UI built from tokens, labelled when illustrative; capability status comes
 * from the copy (now / in development). No testimonials, logos, prices or invented metrics.
 */
export function SitePage({ copy, signedIn }: { copy: SiteCopy; signedIn: boolean }) {
  return (
    <div className={styles.site} id="top">
      <SiteHeader copy={copy.nav} signedIn={signedIn} />
      <main>
        <Hero copy={copy} />
        <Problem copy={copy.problem} />
        <Loop copy={copy} />
        <Control copy={copy} />
        <Modules copy={copy} />
        <Intelligence copy={copy} />
        <Position copy={copy.position} />
        <Trust copy={copy.trust} />
        <Audience copy={copy.audience} />
        <Plans copy={copy.plans} />
        <FinalCta copy={copy} />
      </main>
      <Footer copy={copy} />
    </div>
  );
}

function Status({ s, copy }: { s: Avail; copy: SiteCopy }) {
  return (
    <span className={styles.status} data-status={s}>
      <span aria-hidden="true" />
      {copy.status[s]}
    </span>
  );
}

/* ------------------------------------------------------------------ hero */
function Hero({ copy }: { copy: SiteCopy }) {
  const h = copy.hero;
  const m = h.morning;
  return (
    <Reveal className={styles.hero} aria-labelledby="hero-title">
      <div className={styles.heroCopy}>
        <p className={`${styles.eyebrow} rv`}>{h.eyebrow}</p>
        <h1 id="hero-title" className={`${styles.display} rv`}>
          {h.lead} <HandUnderline>{h.emphasis}</HandUnderline>
          {h.end}
        </h1>
        <p className={`${styles.lede} rv`}>{h.sub}</p>
        <p className={`${styles.support} rv`}>{h.support}</p>
        <div className={`${styles.actions} rv`}>
          <Link href="/register" className={styles.btnPrimaryLg}>
            {h.primary}
            <Icon name="arrowRight" />
          </Link>
          <a href="#how" className={styles.btnGhostLg}>
            {h.secondary}
          </a>
        </div>
        <p className={`${styles.note} rv`}>{h.note}</p>
      </div>

      <div className={styles.heroStage}>
        <NTrail count={4} height={300} fade={false} animate className={styles.heroTrail} />
        <div className={`${styles.morning} rv`} aria-label={m.label}>
          <div className={styles.fragHead}>
            <span className={styles.liveDot} aria-hidden="true" />
            <strong>{m.title}</strong>
            <span className={styles.tag}>{copy.illustrative}</span>
          </div>
          <div className={styles.morningBig}>
            <CountUp value={27} />
            <span>{m.handled}</span>
          </div>
          <div className={styles.split} aria-hidden="true">
            <span style={{ flex: 23 }} />
            <span style={{ flex: 4 }} />
          </div>
          <div className={styles.splitLegend}>
            <span>
              <i data-tone="ok" />
              23 {m.progressing}
            </span>
            <span>
              <i data-tone="attention" />4 {m.needYou}
            </span>
          </div>
          <ul className={styles.morningList}>
            {m.items.map((it) => (
              <li key={it}>
                <i data-tone="attention" aria-hidden="true" />
                {it}
              </li>
            ))}
          </ul>
          <ul className={styles.insights}>
            <li>
              <Icon name="inventory" />
              {m.insights[0]}
            </li>
            <li>
              <Icon name="content" />
              {m.insights[1]}
            </li>
          </ul>
        </div>
      </div>
    </Reveal>
  );
}

/* ------------------------------------------------------------------ problem */
function Problem({ copy }: { copy: SiteCopy["problem"] }) {
  return (
    <Reveal className={`${styles.band} ${styles.sunken}`} aria-labelledby="problem-title">
      <div className={styles.problem}>
        <div className={styles.problemHead}>
          <p className={`${styles.eyebrow} rv`}>{copy.eyebrow}</p>
          <h2 id="problem-title" className={`${styles.h2} rv`}>
            {copy.title}
          </h2>
          <p className={`${styles.body} rv`}>{copy.body}</p>
          <blockquote className={`${styles.pullQuote} rv`}>{copy.quote}</blockquote>
        </div>
        <ol className={styles.pains}>
          {copy.pains.map((p, i) => (
            <li key={p.title} className="rv" style={{ "--d": i } as CSSProperties}>
              <span className={styles.painNo}>{String(i + 1).padStart(2, "0")}</span>
              <div>
                <h3>{p.title}</h3>
                <p>{p.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </Reveal>
  );
}

/* ------------------------------------------------------------------ lifecycle on the ribbon */
function Loop({ copy }: { copy: SiteCopy }) {
  const c = copy.loop;
  const H = 150;
  const t = trailSegments({ count: 5, height: H });
  const pts = [{ x: t.segments[0]!.x1, y: t.segments[0]!.y1 }, ...t.segments.map((s) => ({ x: s.x2, y: s.y2 }))];
  const builtUntil = c.stages.filter((s) => s.status === "now").length - 1; // index of last available stage
  const seg = (i: number) => {
    const s = t.segments[i]!;
    return `M${s.x1} ${s.y1} L${s.x2} ${s.y2}`;
  };
  const order = t.segments.map((s, i) => ({ s, i })).sort((a, b) => (a.s.kind === b.s.kind ? a.i - b.i : a.s.kind === "cross" ? -1 : 1));
  return (
    <Reveal id="how" className={styles.band} aria-labelledby="loop-title">
      <div className={styles.sectionHead}>
        <p className={`${styles.eyebrow} rv`}>{c.eyebrow}</p>
        <h2 id="loop-title" className={`${styles.h2} rv`}>
          {c.title}
        </h2>
        <p className={`${styles.body} rv`}>{c.body}</p>
      </div>
      <div className={styles.loopWide}>
        <svg className={styles.loopSvg} viewBox={`0 ${-t.ribbon} ${t.width} ${H + 2 * t.ribbon}`} aria-hidden="true">
          <defs>
            <linearGradient id="loop-g" x1="0" y1="0" x2={pts[builtUntil]!.x} y2="0" gradientUnits="userSpaceOnUse">
              <stop offset="0" stopColor="var(--color-flow-start)" />
              <stop offset="1" stopColor="var(--color-flow-end)" />
            </linearGradient>
          </defs>
          {order.map(({ i }) => {
            const built = i < builtUntil;
            return (
              <g key={i} strokeLinecap="round" fill="none">
                {built ? (
                  <path d={seg(i)} stroke="url(#loop-g)" strokeWidth={t.ribbon} className={styles.loopBuilt} pathLength={1} style={{ "--i": i } as CSSProperties} />
                ) : (
                  <>
                    <path d={seg(i)} className={styles.loopEdge} strokeWidth={t.ribbon} />
                    <path d={seg(i)} className={styles.loopFill} strokeWidth={t.ribbon - 3} />
                  </>
                )}
              </g>
            );
          })}
          {pts.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r={t.ribbon * 0.16} className={i <= builtUntil ? styles.loopDotOn : styles.loopDot} />
          ))}
        </svg>
        <ol className={styles.loopStages}>
          {c.stages.map((s, i) => {
            const p = pts[i]!;
            const up = i % 2 === 1;
            return (
              <li
                key={s.name}
                data-pos={up ? "up" : "down"}
                data-status={s.status}
                className="rv"
                style={{ "--x": `${(p.x / t.width) * 100}%`, "--d": i } as CSSProperties}
              >
                <span className={styles.stageNo}>{i + 1}</span>
                <strong>{s.name}</strong>
                <span className={styles.stageText}>{s.text}</span>
                <Status s={s.status} copy={copy} />
              </li>
            );
          })}
        </ol>
      </div>
    </Reveal>
  );
}

/* ------------------------------------------------------------------ control center */
function Control({ copy }: { copy: SiteCopy }) {
  const c = copy.control;
  const f = c.fragment;
  return (
    <Reveal className={styles.band} aria-labelledby="control-title">
      <div className={styles.split2}>
        <div>
          <p className={`${styles.eyebrow} rv`}>
            {c.eyebrow} <Status s="next" copy={copy} />
          </p>
          <h2 id="control-title" className={`${styles.h2} rv`}>
            {c.title}
          </h2>
          <p className={`${styles.body} rv`}>{c.body}</p>
          <dl className={styles.points}>
            {c.points.map((p, i) => (
              <div key={p.title} className="rv" style={{ "--d": i } as CSSProperties}>
                <dt>{p.title}</dt>
                <dd>{p.text}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div className={`${styles.frame} rv`}>
          <div className={styles.frameBar}>
            <NivaroMark size={14} />
            <span>Nivaro</span>
            <span className={styles.tag}>{copy.illustrative}</span>
          </div>
          <div className={styles.cc}>
            <div className={styles.ccTop}>
              <div>
                <p className={styles.ccRunning}>
                  <span className={styles.liveDot} aria-hidden="true" />
                  {f.running}
                </p>
                <dl className={styles.ccToday}>
                  {f.today.map(([k, v]) => (
                    <div key={k}>
                      <dt>{k}</dt>
                      <dd>{v}</dd>
                    </div>
                  ))}
                </dl>
              </div>
              <div className={styles.ccScore}>
                <span>{f.score}</span>
                <strong>
                  <CountUp value={86} />%
                </strong>
                <span className={styles.ccScoreNote}>{f.scoreNote}</span>
                <div className={styles.scoreBars} aria-hidden="true">
                  {[92, 88, 74, 81, 95].map((v, i) => (
                    <span key={i} style={{ "--h": `${v}%`, "--i": i } as CSSProperties} />
                  ))}
                </div>
              </div>
            </div>
            <p className={styles.ccAttention}>{f.attention}</p>
            <ul className={styles.ccRows}>
              {f.rows.map((r) => (
                <li key={r.text} data-tone={r.tone}>
                  <span>{r.text}</span>
                  <span className={styles.ccAction}>{r.action}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </Reveal>
  );
}

/* ------------------------------------------------------------------ product modules */
/** Flat product illustration (stand-in for a seller's photo; real seller photography pending, GAP-BRAND-PHOTO). */
function Kurta({ variant = 0 }: { variant?: 0 | 1 | 2 }) {
  const t = ["translate(0 0) scale(1)", "translate(-34 -20) scale(1.6)", "translate(10 22) scale(0.82) rotate(-6 60 60)"][variant];
  return (
    <svg viewBox="0 0 120 120" className={styles.kurta} aria-hidden="true">
      <rect width="120" height="120" className={styles.kurtaBg} />
      <g transform={t}>
        <path d="M45 18 52 14h16l7 4 22 14-9 15-11-6v58H43V41l-11 6-9-15Z" fill="#7F1D3A" />
        <path d="M52 14c2 8 14 8 16 0" fill="none" stroke="#5B1229" strokeWidth="2.5" />
        <path d="M60 22v26" stroke="#E8C77A" strokeWidth="1.6" strokeDasharray="2 3" />
        <path d="M43 92h34" stroke="#E8C77A" strokeWidth="2" />
        <path d="M43 97h34" stroke="#E8C77A" strokeWidth="1" />
      </g>
    </svg>
  );
}

function Modules({ copy }: { copy: SiteCopy }) {
  const c = copy.modules;
  const [studio, video, publish, ...next] = c.items;
  return (
    <Reveal id="product" className={styles.band} aria-labelledby="modules-title">
      <div className={styles.sectionHead}>
        <p className={`${styles.eyebrow} rv`}>{c.eyebrow}</p>
        <h2 id="modules-title" className={`${styles.h2} rv`}>
          {c.title}
        </h2>
      </div>

      {/* Studio: photo → draft, with the one hand-drawn arrow of this section */}
      <div className={styles.moduleRow}>
        <div className={styles.moduleText}>
          <Status s={studio!.status} copy={copy} />
          <h3 className={`${styles.h3} rv`}>{studio!.name}</h3>
          <p className={`${styles.body} rv`}>{studio!.text}</p>
        </div>
        <div className={`${styles.studio} rv`}>
          <div className={styles.studioPhotos}>
            <span className={styles.fragLabel}>{c.studio.photos}</span>
            <div className={styles.photoStack}>
              <Kurta variant={0} />
              <Kurta variant={1} />
              <Kurta variant={2} />
            </div>
          </div>
          <HandArrow className={styles.studioArrow} />
          <div className={styles.studioDraft}>
            <span className={styles.fragLabel}>{c.studio.draft}</span>
            {c.studio.fields.map(([k, v], i) => (
              <div key={k} className={styles.draftField}>
                <span>{k}</span>
                <strong>{v}</strong>
                {i === 1 ? <em className={styles.aiTag}>{c.studio.aiTag}</em> : null}
              </div>
            ))}
            <div className={`${styles.draftField} ${styles.draftPrice}`}>
              <span>{c.studio.price}</span>
              <strong>रू —</strong>
              <em>{c.studio.priceHint}</em>
            </div>
          </div>
        </div>
      </div>

      {/* Auto Reels + publishing side by side: different shapes, same system */}
      <div className={styles.moduleDuo}>
        <div className={styles.moduleCell}>
          <div className={`${styles.reel} rv`} aria-hidden="true">
            <Kurta variant={0} />
            <span className={styles.reelPrice}>रू 1,850</span>
            <span className={styles.reelText}>नयाँ आयो · हाते तान</span>
            <span className={styles.reelBar}>
              <span />
            </span>
          </div>
          <div>
            <Status s={video!.status} copy={copy} />
            <h3 className={`${styles.h3} rv`}>{video!.name}</h3>
            <p className={`${styles.body} rv`}>{video!.text}</p>
          </div>
        </div>
        <div className={styles.moduleCell}>
          <div className={`${styles.sync} rv`}>
            <p className={styles.syncTitle}>{c.sync.title}</p>
            <ul>
              {c.sync.lanes.map(([ch, st, tone], i) => (
                <li key={ch} data-tone={tone} style={{ "--i": i } as CSSProperties}>
                  <span className={styles.syncDot} aria-hidden="true" />
                  <span>{ch}</span>
                  <span className={styles.syncState}>{st}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <Status s={publish!.status} copy={copy} />
            <h3 className={`${styles.h3} rv`}>{publish!.name}</h3>
            <p className={`${styles.body} rv`}>{publish!.text}</p>
          </div>
        </div>
      </div>

      {/* In development: smaller, honest */}
      <div className={styles.nextGrid}>
        {next.map((m) => (
          <div key={m.key} className={`${styles.nextCell} rv`}>
            {m.key === "inbox" ? (
              <div className={styles.chat} aria-hidden="true">
                <p className={styles.bubbleIn}>{c.chat.customer}</p>
                <p className={styles.bubbleOut}>
                  <span className={styles.aiTag}>AI</span> {c.chat.reply}
                </p>
                <div className={styles.orderDraft}>
                  <strong>{c.chat.order}</strong>
                  {c.chat.fields.map(([k, v]) => (
                    <span key={k}>
                      <em>{k}</em> {v}
                    </span>
                  ))}
                  <span className={styles.missing}>{c.chat.missing}</span>
                </div>
              </div>
            ) : m.key === "orders" ? (
              <ol className={styles.journey} aria-hidden="true">
                {c.journey.map((j, i) => (
                  <li key={j} data-done={i < 4 || undefined} style={{ "--i": i } as CSSProperties}>
                    {j}
                  </li>
                ))}
              </ol>
            ) : (
              <div className={styles.returnsFrag} aria-hidden="true">
                <Icon name="returns" size={22} />
                <span>Exchange · M → L</span>
                <span>Pickup booked</span>
                <span>Replacement reserved</span>
              </div>
            )}
            <Status s={m.status} copy={copy} />
            <h3 className={styles.h4}>{m.name}</h3>
            <p className={styles.small}>{m.text}</p>
          </div>
        ))}
      </div>
    </Reveal>
  );
}

/* ------------------------------------------------------------------ intelligence */
function Intelligence({ copy }: { copy: SiteCopy }) {
  const c = copy.intelligence;
  return (
    <Reveal id="intelligence" className={`${styles.band} ${styles.sunken}`} aria-labelledby="intel-title">
      <div className={styles.split2}>
        <div>
          <p className={`${styles.eyebrow} rv`}>
            {c.eyebrow} <Status s="next" copy={copy} />
          </p>
          <h2 id="intel-title" className={`${styles.h2} rv`}>
            {c.title}
          </h2>
          <p className={`${styles.body} rv`}>{c.body}</p>
        </div>
        <ul className={styles.intelGrid}>
          {c.items.map((it, i) => (
            <li key={it.name} className="rv" style={{ "--d": i } as CSSProperties}>
              <h3>{it.name}</h3>
              <p>{it.text}</p>
            </li>
          ))}
        </ul>
      </div>
      <h3 className={`${styles.examplesTitle} rv`}>{c.examplesTitle}</h3>
      <ul className={styles.examples}>
        {c.examples.map((e, i) => (
          <li key={e.what} className="rv" style={{ "--d": i } as CSSProperties}>
            <strong>{e.what}</strong>
            <span>
              <em>{c.whyLabel}</em> {e.why}
            </span>
          </li>
        ))}
      </ul>
    </Reveal>
  );
}

/* ------------------------------------------------------------------ positioning */
function Position({ copy }: { copy: SiteCopy["position"] }) {
  return (
    <Reveal className={styles.band} aria-labelledby="position-title">
      <p className={`${styles.eyebrow} rv`}>{copy.eyebrow}</p>
      <h2 id="position-title" className={`${styles.h2} rv`}>
        {copy.title}
      </h2>
      <ul className={styles.nots}>
        {copy.nots.map((n) => (
          <li key={n} className="rv">
            <HandStrike>{n}</HandStrike>
          </li>
        ))}
      </ul>
      <p className={`${styles.lede} rv`}>{copy.lead}</p>
      <ul className={styles.owns}>
        {copy.owns.map((o, i) => (
          <li key={o.title} className="rv" style={{ "--d": i } as CSSProperties}>
            <h3>{o.title}</h3>
            <p>{o.text}</p>
          </li>
        ))}
      </ul>
    </Reveal>
  );
}

/* ------------------------------------------------------------------ trust banner (navy) */
function Trust({ copy }: { copy: SiteCopy["trust"] }) {
  return (
    <Reveal className={styles.navyBand} aria-labelledby="trust-title">
      <NTrail count={6} height={260} className={styles.navyTrail} />
      <div className={styles.navyInner}>
        <p className={`${styles.eyebrowOnNavy} rv`}>{copy.eyebrow}</p>
        <h2 id="trust-title" className={`${styles.h2} ${styles.onNavy} rv`}>
          {copy.title}
        </h2>
        <p className={`${styles.bodyOnNavy} rv`}>{copy.body}</p>
        <ul className={styles.trustGrid}>
          {copy.items.map((it, i) => (
            <li key={it.title} className="rv" style={{ "--d": i } as CSSProperties}>
              <h3>{it.title}</h3>
              <p>{it.text}</p>
            </li>
          ))}
        </ul>
      </div>
    </Reveal>
  );
}

/* ------------------------------------------------------------------ audience */
function Audience({ copy }: { copy: SiteCopy["audience"] }) {
  return (
    <Reveal className={styles.band} aria-labelledby="audience-title">
      <div className={styles.audience}>
        <div>
          <p className={`${styles.eyebrow} rv`}>{copy.eyebrow}</p>
          <h2 id="audience-title" className={`${styles.h2} rv`}>
            {copy.title}
          </h2>
          <p className={`${styles.body} rv`}>{copy.body}</p>
        </div>
        <ul className={styles.audiencePoints}>
          {copy.points.map((p, i) => (
            <li key={p} className="rv" style={{ "--d": i } as CSSProperties}>
              <Icon name="check" />
              {p}
            </li>
          ))}
        </ul>
      </div>
    </Reveal>
  );
}

/* ------------------------------------------------------------------ plans (no prices until GTM decides) */
function Plans({ copy }: { copy: SiteCopy["plans"] }) {
  return (
    <Reveal id="plans" className={styles.band} aria-labelledby="plans-title">
      <div className={styles.sectionHead}>
        <p className={`${styles.eyebrow} rv`}>{copy.eyebrow}</p>
        <h2 id="plans-title" className={`${styles.h2} rv`}>
          {copy.title}
        </h2>
        <p className={`${styles.body} rv`}>{copy.note}</p>
      </div>
      <ol className={styles.tiers}>
        {copy.tiers.map((t, i) => (
          <li key={t.name} data-hero={t.hero || undefined} className="rv" style={{ "--d": i } as CSSProperties}>
            {t.hero ? <span className={styles.heroTag}>{copy.heroTag}</span> : null}
            <span className={styles.tierStep} aria-hidden="true" style={{ "--h": `${(i + 1) * 18}%` } as CSSProperties} />
            <h3>{t.name}</h3>
            <p className={styles.tierTheme}>{t.theme}</p>
            <p>{t.value}</p>
          </li>
        ))}
      </ol>
      <div className={styles.center}>
        <Link href="/register" className={styles.btnPrimaryLg}>
          {copy.cta}
          <Icon name="arrowRight" />
        </Link>
      </div>
    </Reveal>
  );
}

/* ------------------------------------------------------------------ final CTA (navy, commerce loop) */
function FinalCta({ copy }: { copy: SiteCopy }) {
  const c = copy.cta;
  const stages = (["Create", "Sell", "Fulfill", "Learn"] as const).map((s, i) => ({
    key: s.toLowerCase(),
    label: c.loop[i]!,
  }));
  return (
    <Reveal className={`${styles.navyBand} ${styles.ctaBand}`} aria-labelledby="cta-title">
      <div className={styles.ctaInner}>
        <div>
          <h2 id="cta-title" className={`${styles.h2} ${styles.onNavy} rv`}>
            {c.title} <HandRing>{c.emphasis}</HandRing>
            {c.end}
          </h2>
          <p className={`${styles.bodyOnNavy} rv`}>{c.body}</p>
          <div className={`${styles.actions} rv`}>
            <Link href="/register" className={styles.btnPrimaryLg}>
              {c.primary}
              <Icon name="arrowRight" />
            </Link>
            <Link href="/login" className={styles.btnOnNavy}>
              {c.secondary}
            </Link>
          </div>
        </div>
        <div className={`${styles.ctaLoop} rv`}>
          <CommerceLoop label={copy.loop.title} stages={stages} />
        </div>
      </div>
    </Reveal>
  );
}

function Footer({ copy }: { copy: SiteCopy }) {
  return (
    <footer className={styles.footer}>
      <div className={styles.footerInner}>
        <div>
          <NivaroLogo height={24} />
          <p>{copy.footer.tagline}</p>
        </div>
        <nav aria-label="Footer">
          <a href="#how">{copy.nav.how}</a>
          <a href="#product">{copy.nav.product}</a>
          <a href="#plans">{copy.nav.plans}</a>
          <Link href="/login">{copy.nav.signIn}</Link>
          <Link href="/register">{copy.nav.start}</Link>
        </nav>
        <p className={styles.footerMeta}>
          {copy.footer.rights} · {copy.footer.made}
        </p>
      </div>
    </footer>
  );
}
