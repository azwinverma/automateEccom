import { notFound } from "next/navigation";
import { DevFixtures } from "@/features/dev/DevFixtures";

export const dynamic = "force-dynamic";

export default function DevComponentsPage() {
  if (process.env.NODE_ENV === "production") notFound();
  return <DevFixtures />;
}
