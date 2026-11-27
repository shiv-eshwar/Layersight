import { EmptyState } from "@/components/shell/empty-state";
import { Screen } from "@/components/shell/screen";

export const metadata = { title: "Awareness Academy" };

export default function AcademyPage() {
  return (
    <Screen
      title="Awareness Academy"
      purpose="A short quiz built from emails the engine has already analyzed, with the evidence as the explanation."
    >
      <EmptyState title="No questions yet">
        Questions are written from real messages in the loaded set: is it phishing, which part is
        the warning sign, and where a link actually goes.
      </EmptyState>
    </Screen>
  );
}
