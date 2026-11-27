import { Suspense } from "react";

import { CommandCenter } from "@/components/phase6/command-center";
import { ScreenState } from "@/components/layersight/screen-state";
import { Screen } from "@/components/shell/screen";

export const metadata = { title: "Security Command Center" };

export default async function CommandCenterPage({
  searchParams,
}: {
  searchParams: Promise<{ state?: string }>;
}) {
  const params = await searchParams;
  const forced = params.state;
  return (
    <Screen
      title="Security Command Center"
      purpose="Organization-wide phishing exposure, and how far the current defenses would hold."
    >
      {forced === "loading" || forced === "empty" || forced === "error" ? (
        <ScreenState state={forced} />
      ) : (
        <Suspense fallback={<p className="text-sm text-muted-foreground">Loading the command center.</p>}>
          <CommandCenter />
        </Suspense>
      )}
    </Screen>
  );
}
