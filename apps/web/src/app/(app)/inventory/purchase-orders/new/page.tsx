import { Suspense } from "react";
import { NewPurchaseOrderView } from "@/features/procurement/PurchaseOrdersView";

export default function NewPurchaseOrderPage() {
  return (
    <Suspense>
      <NewPurchaseOrderView />
    </Suspense>
  );
}
