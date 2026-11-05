import { Suspense } from "react";
import { AutomationView } from "@/features/automation/AutomationView";

export default function AutomationPage() {
  return (
    <Suspense>
      <AutomationView />
    </Suspense>
  );
}
