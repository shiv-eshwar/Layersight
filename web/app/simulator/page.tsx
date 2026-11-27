import { FlagshipProviders } from "@/components/flagship/providers";
import { SimulatorScreen } from "@/components/flagship/simulator-screen";
import { Screen } from "@/components/shell/screen";

export const metadata = { title: "Attack Simulator" };

export default function SimulatorPage() {
  return (
    <Screen
      title="Attack Simulator"
      purpose="Ten thousand runs of each phishing email in scope, and where those attacks stop. Counts are modeled estimates."
    >
      <FlagshipProviders>
        <SimulatorScreen />
      </FlagshipProviders>
    </Screen>
  );
}
