import { Suspense } from "react";
import { ContentCalendar } from "@/features/content/ContentCalendar";

export default function ContentPage() {
  return (
    <Suspense>
      <ContentCalendar />
    </Suspense>
  );
}
