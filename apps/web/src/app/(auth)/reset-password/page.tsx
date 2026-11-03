import { Suspense } from "react";
import { ResetPasswordForm } from "@/features/auth/AccountFlows";

export default function Page() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  );
}
