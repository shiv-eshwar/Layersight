import { FlagshipProviders } from "@/components/flagship/providers";
import { SimulatorScreen } from "@/components/flagship/simulator-screen";
import { Screen } from "@/components/shell/screen";

export const metadata = { title: "Attack Simulator" };

export default function SimulatorPage() {
  return (
    <Screen
      title="Attack Simulator"
      purpose="Model how phishing emails flow through your layered defenses and estimate the chance of a successful attack."
    >
      <FlagshipProviders>
        <SimulatorScreen />
      </FlagshipProviders>
    </Screen>
  );
}
