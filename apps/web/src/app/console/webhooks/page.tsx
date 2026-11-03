import { Suspense } from "react";
import { WebhooksView } from "@/features/console/OpsViews";

export default function Page() {
  return (
    <Suspense>
      <WebhooksView />
    </Suspense>
  );
}
