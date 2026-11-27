import { Screen } from "@/components/shell/screen";
import { TriageInbox } from "@/components/triage/inbox";

export const metadata = { title: "Email Triage" };

export default function TriagePage() {
  return (
    <Screen
      title="Email Triage"
      purpose="Bring emails in, then sort them by risk once the engine has classified them."
    >
      <TriageInbox />
    </Screen>
  );
}
