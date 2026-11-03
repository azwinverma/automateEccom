import { Suspense } from "react";
import { OutboxView } from "@/features/console/OpsViews";

export default function Page() {
  return (
    <Suspense>
      <OutboxView />
    </Suspense>
  );
}
