import { Suspense } from "react";
import { ReelsView } from "@/features/content/ReelsView";

export default function ReelsPage() {
  return (
    <Suspense>
      <ReelsView />
    </Suspense>
  );
}
