import { CompareScreen } from "@/components/flagship/compare-screen";
import { FlagshipProviders } from "@/components/flagship/providers";
import { Screen } from "@/components/shell/screen";

export const metadata = { title: "Before vs After" };

export default function ComparePage() {
  return (
    <Screen
      title="Before vs After"
      purpose="The chance an attack passes every layer, before training and after, and what that change is worth."
    >
      <FlagshipProviders>
        <CompareScreen />
      </FlagshipProviders>
    </Screen>
  );
}
