import { Suspense } from "react";
import { InboxView } from "@/features/inbox/InboxView";

export default function InboxPage() {
  return (
    <Suspense>
      <InboxView />
    </Suspense>
  );
}
