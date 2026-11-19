import { Suspense } from "react";
import { AnalyticsView } from "@/features/intelligence/AnalyticsView";

export default function AnalyticsPage() {
  return (
    <Suspense>
      <AnalyticsView />
    </Suspense>
  );
}
