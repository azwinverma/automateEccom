import { StudioJobView } from "@/features/studio/StudioJob";

export default async function StudioJobPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <StudioJobView id={id} />;
}
