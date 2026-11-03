import { Suspense } from "react";
import { FlagsView } from "@/features/console/OpsViews";

export default function Page() {
  return (
    <Suspense>
      <FlagsView />
    </Suspense>
  );
}
