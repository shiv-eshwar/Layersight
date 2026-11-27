import { Suspense } from "react";

import { Investigation } from "@/components/investigation/detail";
import { Screen } from "@/components/shell/screen";

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
      <Suspense fallback={<p className="text-sm text-muted-foreground">Opening the analysis…</p>}>
        <Investigation emailId={id} />
      </Suspense>
    </Screen>
  );
}
