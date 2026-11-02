import type { ReactNode } from "react";
import { AppShell } from "@/components/shell/AppShell";
import { RequireSession } from "@/components/shell/RequireSession";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <RequireSession requireMerchant>
      <AppShell>{children}</AppShell>
    </RequireSession>
  );
}
