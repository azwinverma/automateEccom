import { notFound } from "next/navigation";
import { ComingSection } from "@/features/home/ComingSection";
import { findSection } from "@/lib/sections";

export default async function SectionPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  const def = findSection(section);
  if (!def || def.phase === undefined || def.key === "home") notFound();
  return <ComingSection section={{ ...def, key: def.key, phase: def.phase }} />;
}
