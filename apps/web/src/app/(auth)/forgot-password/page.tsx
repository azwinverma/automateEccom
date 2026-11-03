import { Suspense } from "react";
import { ForgotPasswordForm } from "@/features/auth/AccountFlows";

export default function Page() {
  return (
    <Suspense>
      <ForgotPasswordForm />
    </Suspense>
  );
}
