import { Suspense } from "react";

import { IntelligenceBoard } from "@/components/phase6/intelligence-board";
import { ScreenState } from "@/components/layersight/screen-state";
import { Screen } from "@/components/shell/screen";

export const metadata = { title: "URL & Domain Intelligence" };

export default async function IntelligencePage({
  searchParams,
}: {
  searchParams: Promise<{ state?: string }>;
}) {
  const params = await searchParams;
  const forced = params.state;
  return (
    <Screen
      title="URL & Domain Intelligence"
      purpose="Analyze URLs, detect look-alike domains, and uncover deception techniques."
    >
      {forced === "loading" || forced === "empty" || forced === "error" ? (
        <ScreenState state={forced} />
      ) : (
        <Suspense fallback={<p className="text-sm text-muted-foreground">Loading domain intelligence.</p>}>
          <IntelligenceBoard />
        </Suspense>
      )}
    </Screen>
  );
}
