import { EmptyState } from "@/components/shell/empty-state";
import { Screen } from "@/components/shell/screen";

export const metadata = { title: "Validation & Reports" };

export default function ReportsPage() {
  return (
    <Screen
      title="Validation & Reports"
      purpose="Accuracy on the labeled set, the confusion matrix, and the pass-through rate for both configurations."
    >
      <EmptyState title="No labeled results">
        The official test set has not been loaded. When it is, this page will show how many of the
        20 emails were classified correctly, including the ones the engine got wrong.
      </EmptyState>
    </Screen>
  );
}
