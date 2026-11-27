import Link from "next/link";

import { EmptyState } from "@/components/shell/empty-state";
import { Screen } from "@/components/shell/screen";
import { buttonVariants } from "@/components/ui/button";

export default function CommandCenterPage() {
  return (
    <Screen
      title="Security Command Center"
      purpose="Organization-wide phishing exposure, and how far the current defenses would hold."
    >
      <EmptyState
        title="No emails loaded"
        action={
          <Link href="/triage" className={buttonVariants()}>
            Upload emails
          </Link>
        }
      >
        Upload a set to see residual risk, where attacks stop, and which change reduces that risk
        the most. Every figure on this page will come from the engine.
      </EmptyState>
    </Screen>
  );
}
