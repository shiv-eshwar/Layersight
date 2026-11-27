import { FlagshipProviders } from "@/components/flagship/providers";
import { DefenseScreen } from "@/components/flagship/defense-screen";
import { Screen } from "@/components/shell/screen";

export const metadata = { title: "Defense Layer Builder" };

export default function DefensePage() {
  return (
    <Screen
      title="Defense Layer Builder"
      purpose="Configure your layered defense, simulate its effectiveness, and compare results before and after training."
    >
      <FlagshipProviders>
        <DefenseScreen />
      </FlagshipProviders>
    </Screen>
  );
}
