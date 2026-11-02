import Link from "next/link";
import { getTranslator } from "@/i18n/server";

export default async function NotFound() {
  const t = await getTranslator();
  return (
    <main style={{ maxWidth: 520, margin: "0 auto", padding: "var(--space-16) var(--space-4)", display: "grid", gap: "var(--space-3)" }}>
      <h1>{t("states.notFoundTitle")}</h1>
      <p style={{ color: "var(--text-secondary)" }}>{t("states.notFoundBody")}</p>
      <p>
        <Link href="/home">{t("states.goHome")}</Link>
      </p>
    </main>
  );
}
