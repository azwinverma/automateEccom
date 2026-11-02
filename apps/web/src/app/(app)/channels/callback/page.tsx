import { Suspense } from "react";
import { ChannelCallback } from "@/features/channels/ChannelCallback";

export default function ChannelCallbackPage() {
  return (
    <Suspense>
      <ChannelCallback />
    </Suspense>
  );
}
