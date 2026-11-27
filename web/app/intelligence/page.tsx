import { EmptyState } from "@/components/shell/empty-state";
import { Screen } from "@/components/shell/screen";

export const metadata = { title: "URL & Domain Intelligence" };

export default function IntelligencePage() {
  return (
    <Screen
      title="URL & Domain Intelligence"
      purpose="Look-alike domains, links whose text hides the real address, and a similarity score for each."
    >
      <EmptyState title="No domains to compare">
        After emails are analyzed, every sender, reply address, and link domain will be listed here
        with the protected brand it most resembles and the technique it uses.
      </EmptyState>
    </Screen>
  );
}
