import { Suspense } from "react";

import { AcademyQuiz } from "@/components/phase6/academy-quiz";
import { ScreenState } from "@/components/layersight/screen-state";
import { Screen } from "@/components/shell/screen";

export const metadata = { title: "Awareness Academy" };

export default async function AcademyPage({
  searchParams,
}: {
  searchParams: Promise<{ state?: string }>;
}) {
  const params = await searchParams;
  const forced = params.state;
  return (
    <Screen
      title="Awareness Academy"
      purpose="A short quiz built from emails the engine has already analyzed, with the evidence as the explanation."
    >
      {forced === "loading" || forced === "empty" || forced === "error" ? (
        <ScreenState state={forced} />
      ) : (
        <Suspense fallback={<p className="text-sm text-muted-foreground">Loading the quiz.</p>}>
          <AcademyQuiz />
        </Suspense>
      )}
    </Screen>
  );
}
