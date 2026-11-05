import { WorkflowBuilder } from "@/features/automation/WorkflowBuilder";

export default async function WorkflowPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <WorkflowBuilder id={id} />;
}
