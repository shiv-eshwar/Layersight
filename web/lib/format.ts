export function formatPct(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatScore(value: number): string {
  return value.toFixed(2);
}

export function vectorLabel(vector: string): string {
  const names: Record<string, string> = {
    malware_attachment: "Malware attachment",
    malware_link: "Malware link",
    credential_harvest: "Credential harvest",
    payment_fraud: "Payment fraud",
  };
  return names[vector] ?? vector;
}

export function layerLabel(layer: string): string {
  const names: Record<string, string> = {
    email_filter: "Email filter",
    user: "User",
    application_control: "Application control",
    antivirus: "Antivirus",
    segmentation: "Segmentation",
  };
  return names[layer] ?? layer;
}
