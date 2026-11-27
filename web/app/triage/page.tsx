import { Suspense } from "react";

import { Screen } from "@/components/shell/screen";
import { TriageInbox } from "@/components/triage/inbox";

export const metadata = { title: "Email Triage" };

export default function TriagePage() {
  return (
    <Screen
      title="Email Triage"
      purpose="Upload, analyze, and classify emails. Get risk scores, evidence, and layered defense insights."
    >
      <Suspense fallback={<p className="text-sm text-muted-foreground">Loading triage…</p>}>
        <TriageInbox />
      </Suspense>
    </Screen>
  );
}
