import { Suspense } from "react";
import { AuditView } from "@/features/console/OpsViews";

export default function Page() {
  return (
    <Suspense>
      <AuditView />
    </Suspense>
  );
}
