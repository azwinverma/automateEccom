import { Suspense } from "react";
import { AcceptInviteView } from "@/features/auth/AccountFlows";

export default function Page() {
  return (
    <Suspense>
      <AcceptInviteView />
    </Suspense>
  );
}
