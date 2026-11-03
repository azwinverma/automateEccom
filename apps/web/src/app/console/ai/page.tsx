import { Suspense } from "react";
import { ProvidersView } from "@/features/console/OpsViews";

export default function Page() {
  return (
    <Suspense>
      <ProvidersView />
    </Suspense>
  );
}
