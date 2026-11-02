import { Suspense } from "react";
import { ChannelsView } from "@/features/channels/ChannelsView";

export default function ChannelsPage() {
  return (
    <Suspense>
      <ChannelsView />
    </Suspense>
  );
}
