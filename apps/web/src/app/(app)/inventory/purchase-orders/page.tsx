import { Suspense } from "react";
import { PurchaseOrdersView } from "@/features/procurement/PurchaseOrdersView";

export default function PurchaseOrdersPage() {
  return (
    <Suspense>
      <PurchaseOrdersView />
    </Suspense>
  );
}
