"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorState, FullPageMessage } from "../states/States";

/**
 * Client-side guard. Middleware already bounced visitors with no session cookie;
 * this restores the in-memory access token from the httpOnly refresh cookie and
 * routes users without a business to onboarding.
 */
export function RequireSession({ requireMerchant, children }: { requireMerchant: boolean; children: ReactNode }) {
  const { t } = useI18n();
  const { status, error, activeMemberships, ensureSession } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "idle") ensureSession();
  }, [status, ensureSession]);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    } else if (status === "ready" && requireMerchant && activeMemberships.length === 0) {
      router.replace("/onboarding");
    }
  }, [status, requireMerchant, activeMemberships.length, router, pathname]);

  if (status === "unreachable") {
    return (
      <FullPageMessage>
        <ErrorState title={t("auth.session.unreachableTitle")} error={error} onRetry={ensureSession} />
      </FullPageMessage>
    );
  }
  if (status !== "ready" || (requireMerchant && activeMemberships.length === 0)) {
    return (
      <FullPageMessage>
        <p role="status">{t("auth.session.checking")}</p>
      </FullPageMessage>
    );
  }
  return <>{children}</>;
}
