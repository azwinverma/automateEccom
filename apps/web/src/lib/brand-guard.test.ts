import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

/**
 * Brand guard (BRD-016, specs/26 §5/§19): component styles use semantic tokens, never raw colours,
 * legacy indigo, or the pre-Nivaro product name. Exceptions must be listed with a reason.
 */
const ROOT = join(__dirname, "..");
const ALLOW: Record<string, string> = {
  // QR codes must be pure black-on-white to scan reliably; values passed to the QR library.
  "features/settings/SecurityView.tsx": "QR colours",
  "features/settings/settings.module.css": "QR quiet zone must be white in both themes",
  // Flat product illustration (a maroon kurta): garment colours, not UI colours.
  "features/site/SitePage.tsx": "product illustration",
  // Video letterbox is true black regardless of theme.
  "features/content/ReelsView.tsx": "video letterbox",
};

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    if (statSync(p).isDirectory()) return files(p);
    return /\.(css|tsx)$/.test(n) && !/\.test\.tsx$/.test(n) ? [p] : [];
  });
}

describe("brand guard", () => {
  const all = files(ROOT).map((p) => ({ rel: relative(ROOT, p), text: readFileSync(p, "utf8") }));

  it("no hard-coded colours outside the allowlist", () => {
    const offenders = all
      .filter((f) => !ALLOW[f.rel])
      .flatMap((f) =>
        f.text
          .split("\n")
          .map((line, i) => ({ line, i }))
          // hex colours and rgb()/rgba() literals; ignore url fragments (#id) and mask fills of pure white/black in SVG masks
          .filter(({ line }) => /#[0-9a-fA-F]{3,8}\b|rgba?\(/.test(line) && !/url\(#|href=\{?["`]#|fill="#fff"|stroke="#000"|stopColor="#fff"/.test(line))
          .map(({ line, i }) => `${f.rel}:${i + 1}: ${line.trim()}`),
      );
    expect(offenders).toEqual([]);
  });

  it("no legacy indigo tokens", () => {
    expect(all.filter((f) => /indigo/i.test(f.text)).map((f) => f.rel)).toEqual([]);
  });

  it("no pre-Nivaro product name in UI copy", () => {
    const msgs = ["i18n/messages/en.ts", "i18n/messages/ne.ts"].map((p) => readFileSync(join(ROOT, p), "utf8"));
    for (const m of msgs) expect(m).not.toMatch(/(?<!Autonomous )Commerce OS/);
  });
});
