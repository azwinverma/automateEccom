import { Suspense } from "react";
import { VerifyEmailView } from "@/features/auth/AccountFlows";

export default function Page() {
  return (
    <Suspense>
      <VerifyEmailView />
    </Suspense>
  );
}
