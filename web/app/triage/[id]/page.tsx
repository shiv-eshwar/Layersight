import Link from "next/link";

import { EmptyState } from "@/components/shell/empty-state";
import { Screen } from "@/components/shell/screen";
import { buttonVariants } from "@/components/ui/button";

export const metadata = { title: "Threat Investigation" };

export default async function InvestigationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <Screen
      title="Threat Investigation"
      purpose="The risk score, the headers, the authentication results, and the evidence behind them."
    >
      <EmptyState
        title="This email has not been analyzed"
        action={
          <Link href="/triage" className={buttonVariants({ variant: "outline" })}>
            Back to triage
          </Link>
        }
      >
        There is no analysis for <span className="font-mono text-foreground">{id}</span>. Open an
        email from a classified set and the evidence will be listed here.
      </EmptyState>
    </Screen>
  );
}
