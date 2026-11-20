import { Suspense } from "react";
import { MetaCallback } from "@/features/channels/MetaCallback";

export default function MetaCallbackPage() {
  return (
    <Suspense>
      <MetaCallback />
    </Suspense>
  );
}
