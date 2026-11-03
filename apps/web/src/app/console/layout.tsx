import type { Metadata } from "next";
import type { ReactNode } from "react";
import { RequireSession } from "@/components/shell/RequireSession";
import { ConsoleGate, ConsoleShell } from "@/features/console/ConsoleShell";

export const metadata: Metadata = { title: "Nivaro Console", robots: { index: false, follow: false } };

export default function ConsoleLayout({ children }: { children: ReactNode }) {
  return (
    <RequireSession requireMerchant={false}>
      <ConsoleGate>
        <ConsoleShell>{children}</ConsoleShell>
      </ConsoleGate>
    </RequireSession>
  );
}
