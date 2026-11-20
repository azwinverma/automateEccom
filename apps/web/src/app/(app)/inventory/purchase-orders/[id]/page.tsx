import { PurchaseOrderDetailView } from "@/features/procurement/PurchaseOrderDetail";

export default async function PurchaseOrderPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <PurchaseOrderDetailView id={id} />;
}
