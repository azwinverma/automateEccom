import { ReturnDetailView } from "@/features/returns/ReturnDetail";

export default async function ReturnPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ReturnDetailView id={id} />;
}
