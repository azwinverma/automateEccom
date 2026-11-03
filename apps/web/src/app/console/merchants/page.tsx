import { Suspense } from "react";
import { MerchantsView } from "@/features/console/MerchantsView";

export default function Page() {
  return (
    <Suspense>
      <MerchantsView />
    </Suspense>
  );
}
