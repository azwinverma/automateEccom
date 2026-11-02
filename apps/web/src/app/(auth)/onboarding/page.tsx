import { RequireSession } from "@/components/shell/RequireSession";
import { OnboardingForm } from "@/features/auth/OnboardingForm";

export default function OnboardingPage() {
  return (
    <RequireSession requireMerchant={false}>
      <OnboardingForm />
    </RequireSession>
  );
}
