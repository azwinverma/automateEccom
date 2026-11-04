import { LabelView } from "@/features/fulfillment/LabelView";

export default async function LabelPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <LabelView id={id} />;
}
