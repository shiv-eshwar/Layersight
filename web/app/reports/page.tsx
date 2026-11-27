import { Suspense } from "react";

import { Report } from "@/components/reports/report";
import { Screen } from "@/components/shell/screen";

export const metadata = { title: "Validation & Reports" };

export default function ReportsPage() {
  return (
    <Screen
      title="Validation & Reports"
      purpose="Accuracy on the labeled set, the confusion matrix, and the pass-through rate for both configurations."
    >
      <Suspense fallback={<p className="text-sm text-muted-foreground">Loading the report…</p>}>
        <Report />
      </Suspense>
    </Screen>
  );
}
