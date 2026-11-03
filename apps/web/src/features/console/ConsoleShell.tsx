"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { NivaroLogo } from "@/components/brand/Brand";
import { EmptyState, FullPageMessage } from "@/components/states/States";
import { Button, ButtonLink } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth/AuthProvider";
import { C } from "./copy";
import styles from "./console.module.css";

/** Build-time environment name shown in the top bar so staff always know where they are. */
export const CONSOLE_ENV = process.env.NEXT_PUBLIC_NIVARO_ENV || "local";

export const RAIL = [
  { href: "/console/merchants", label: C.rail.merchants },
  { href: "/console/webhooks", label: C.rail.webhooks },
  { href: "/console/outbox", label: C.rail.outbox },
  { href: "/console/ai", label: C.rail.ai },
  { href: "/console/flags", label: C.rail.flags },
  { href: "/console/audit", label: C.rail.audit },
] as const;

/**
 * Staff gate. Non-staff see a plain "not found" (the Console's existence isn't advertised); staff
 * without a two-step-verified sign-in are told how to get one. The API enforces both regardless.
 */
export function ConsoleGate({ children }: { children: ReactNode }) {
  const { me } = useAuth();
  if (!me?.user.is_platform_staff) {
    return (
      <FullPageMessage>
        <EmptyState title={C.gate.notFoundTitle} body={C.gate.notFoundBody} actions={<ButtonLink href="/home">{C.gate.toApp}</ButtonLink>} />
      </FullPageMessage>
    );
  }
  if (!me.session?.mfa) {
    return (
      <FullPageMessage>
        <EmptyState
          title={C.gate.mfaTitle}
          body={me.user.mfa_enabled ? C.gate.mfaBodyEnabled : C.gate.mfaBodySetup}
          actions={
            me.user.mfa_enabled ? (
              <SignOutButton variant="link" next="/console" label={C.gate.signInAgain} />
            ) : (
              <ButtonLink href="/settings/security" variant="primary">
                {C.gate.setUpMfa}
              </ButtonLink>
            )
          }
        />
      </FullPageMessage>
    );
  }
  return <>{children}</>;
}

function SignOutButton({ next, label, variant }: { next?: string; label: string; variant?: "link" | "bar" }) {
  const { signOut } = useAuth();
  const router = useRouter();
  const go = async () => {
    await signOut();
    router.replace(next ? `/login?next=${encodeURIComponent(next)}` : "/login");
  };
  if (variant === "bar") {
    return (
      <button type="button" className={styles.signOut} onClick={go}>
        {label}
      </button>
    );
  }
  return (
    <Button variant="primary" onClick={go}>
      {label}
    </Button>
  );
}

export function ConsoleShell({ children }: { children: ReactNode }) {
  const { me } = useAuth();
  const pathname = usePathname();
  return (
    <div className={styles.shell}>
      <header className={styles.topbar}>
        <Link href="/console/merchants" aria-label={C.homeLabel} style={{ display: "inline-flex", color: "inherit" }}>
          <NivaroLogo height={22} />
        </Link>
        <span className={styles.product}>{C.product}</span>
        <span className={[styles.env, CONSOLE_ENV === "production" && styles.envProduction].filter(Boolean).join(" ")} data-testid="console-env">
          {CONSOLE_ENV}
        </span>
        <div className={styles.who}>
          <span>{me?.user.email}</span>
          <SignOutButton variant="bar" label={C.signOut} />
        </div>
      </header>
      <div className={styles.body}>
        <nav className={styles.rail} aria-label={C.railLabel}>
          <ul>
            {RAIL.map((r) => (
              <li key={r.href}>
                <Link href={r.href} aria-current={pathname.startsWith(r.href) ? "page" : undefined}>
                  {r.label}
                </Link>
              </li>
            ))}
          </ul>
          <p className={styles.railNote}>{C.railNote}</p>
        </nav>
        <main className={styles.main} id="main">
          {children}
        </main>
      </div>
    </div>
  );
}

export function ConsoleHead({ title, subtitle, children }: { title: string; subtitle?: string; children?: ReactNode }) {
  return (
    <div className={styles.head}>
      <div>
        <h1>{title}</h1>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      {children ? <div className={styles.filters}>{children}</div> : null}
    </div>
  );
}
