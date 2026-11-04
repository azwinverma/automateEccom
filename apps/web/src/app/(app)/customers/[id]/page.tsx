import { CustomerDetailView } from "@/features/customers/CustomerDetail";

export default async function CustomerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <CustomerDetailView id={id} />;
}
