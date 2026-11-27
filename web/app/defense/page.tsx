import { FlagshipProviders } from "@/components/flagship/providers";
import { DefenseScreen } from "@/components/flagship/defense-screen";
import { Screen } from "@/components/shell/screen";

export const metadata = { title: "Defense Layer Builder" };

export default function DefensePage() {
  return (
    <Screen
      title="Defense Layer Builder"
      purpose="Set the five layers: email filter, user training, application control, antivirus, and segmentation. Residual risk updates from the closed form as you edit."
    >
      <FlagshipProviders>
        <DefenseScreen />
      </FlagshipProviders>
    </Screen>
  );
}
