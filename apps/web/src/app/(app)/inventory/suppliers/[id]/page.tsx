import { SupplierDetailView } from "@/features/procurement/SupplierDetail";

export default async function SupplierPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SupplierDetailView id={id} />;
}
