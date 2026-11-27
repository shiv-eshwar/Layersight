/** Illustrative demo figures. The live app replaces these with engine results. */

export const ENGINE_VERSION = "0.1.0";
export const WEIGHTS_HASH = "illustrative";
export const SEED = 42;
export const RUNS = 10_000;
export const DATASET_ID = "official";

export const SHOWCASE = {
  passRateUntrained: 0.0921,
  passRateTrained: 0.0329,
  email: {
    id: "em-showcase",
    filename: "microsoft-verify.eml",
    subject: "Action required: verify your Microsoft account",
    sender: "Microsoft Account <support@micros0ft.com>",
    replyTo: "accounts@ms-account-verify.com",
    returnPath: "bounce@ms-account-verify.com",
    replyToMismatch: true,
    auth: { spf: "fail", dkim: "fail", dmarc: "fail" },
    risk: 0.97,
    label: "phishing",
    band: "critical",
    attackVector: "credential_harvest",
    linkText: "https://login.microsoft.com/verify",
    linkHref: "http://login.micros0ft.com/verify",
    evidence: [
      {
        rule_id: "H01",
        title: "Reply-To mismatch",
        detail: "Replies go to ms-account-verify.com, not micros0ft.com.",
      },
      {
        rule_id: "A03",
        title: "DMARC failed",
        detail: "This message failed sender authentication, so the sender address is probably forged.",
      },
      {
        rule_id: "L02",
        title: "Look-alike domain",
        detail: "micros0ft.com imitates microsoft.com (homoglyph, 0.98).",
      },
      {
        rule_id: "L01",
        title: "Deceptive link",
        detail: "The link text shows microsoft.com, but the address is micros0ft.com.",
      },
    ],
    advice: [
      "Replies would go to ms-account-verify.com, not micros0ft.com. Don't reply; contact the sender through a channel you already know.",
      "The link goes to micros0ft.com, which imitates microsoft.com. Don't click it. Type microsoft.com into your browser instead.",
      "Report it with the Report Phish button, then delete it.",
    ],
  },
  validation: { correct: 18, total: 20 },
  funnel: [
    { layer: "Email filter", entered: 10000, stopped: 3500, remaining: 6500 },
    { layer: "User", entered: 6500, stopped: 1950, remaining: 4550 },
    { layer: "Application control", entered: 4550, stopped: 1137, remaining: 3413 },
    { layer: "Antivirus", entered: 3413, stopped: 1877, remaining: 1536 },
    { layer: "Segmentation", entered: 1536, stopped: 615, remaining: 921 },
  ],
};

const SUPPORTING = [
  ["em-02", "invoice.exe.eml", "Your invoice is attached", "billing@vendor.example", 0.93, "phishing", "malware_attachment", "Executable attachment"],
  ["em-03", "payroll.eml", "Updated payroll details", "cfo@company-pay.co", 0.9, "phishing", "payment_fraud", "Payment request"],
  ["em-04", "sharepoint.eml", "Shared a document with you", "docs@sharepoint-secure.io", 0.86, "phishing", "credential_harvest", "Look-alike domain"],
  ["em-05", "shipping.eml", "Package waiting for customs fee", "notify@shipment-help.com", 0.84, "phishing", "credential_harvest", "Urgency"],
  ["em-06", "vpn.eml", "VPN certificate expired", "it@corp-vpn.net", 0.81, "phishing", "credential_harvest", "Credential request"],
  ["em-07", "hr.eml", "Benefits enrollment closes today", "hr@benefits-portal.co", 0.78, "phishing", "credential_harvest", "Threat of loss"],
  ["em-08", "docusign.eml", "Please sign the agreement", "sign@docusign-docs.com", 0.74, "phishing", "credential_harvest", "Deceptive link"],
  ["em-09", "gift.eml", "Need gift cards for the client", "alex@company.com", 0.71, "phishing", "payment_fraud", "Gift card request"],
  ["em-10", "reset.eml", "Password reset request", "security@company.com", 0.42, "genuine", "credential_harvest", "Aligned authentication"],
  ["em-11", "newsletter.eml", "Weekly product update", "news@vendor.example", 0.38, "genuine", "credential_harvest", "Sender domain links"],
  ["em-12", "invoice-real.eml", "Invoice 1044", "ap@vendor.example", 0.33, "genuine", "payment_fraud", "Known vendor"],
  ["em-13", "ticket.eml", "Your support ticket was updated", "support@vendor.example", 0.29, "genuine", "credential_harvest", "No warning signs"],
  ["em-14", "calendar.eml", "Accepted: design review", "alex@company.com", 0.22, "genuine", "payment_fraud", "Internal sender"],
  ["em-15", "shipping-real.eml", "Your package shipped", "ship@carrier.example", 0.18, "genuine", "credential_harvest", "Known carrier"],
  ["em-16", "github.eml", "New sign-in to GitHub", "noreply@github.com", 0.16, "genuine", "credential_harvest", "Aligned authentication"],
  ["em-17", "receipt.eml", "Your receipt from Northwind", "receipts@northwind.example", 0.14, "genuine", "payment_fraud", "Receipt"],
  ["em-18", "ood.eml", "Out of office", "sam@company.com", 0.08, "genuine", "payment_fraud", "No warning signs"],
  ["em-19", "borderline-phish.eml", "Please review the wire instructions", "finance@company.com", 0.62, "phishing", "payment_fraud", "Payment request"],
  ["em-20", "borderline-real.eml", "Reminder: submit timesheets", "hr@company.com", 0.57, "genuine", "credential_harvest", "Internal urgency"],
];

export const emails = [
  summaryFromShowcase(),
  ...SUPPORTING.map(toSummary),
].sort((a, b) => b.risk - a.risk);

function summaryFromShowcase() {
  const email = SHOWCASE.email;
  return {
    id: email.id,
    filename: email.filename,
    subject: email.subject,
    sender: email.sender,
    risk: email.risk,
    label: email.label,
    band: email.band,
    attackVector: email.attackVector,
    topEvidence: email.evidence[2].title,
  };
}

function toSummary([id, filename, subject, sender, risk, label, attackVector, topEvidence]) {
  return {
    id,
    filename,
    subject,
    sender,
    risk,
    label,
    band: bandFor(risk),
    attackVector,
    topEvidence,
  };
}

function bandFor(risk) {
  if (risk >= 0.85) return "critical";
  if (risk >= 0.7) return "high";
  if (risk >= 0.5) return "suspicious";
  return "low";
}

export function formatPct(rate) {
  return `${(rate * 100).toFixed(2)}%`;
}

export function formatReduction(rate) {
  return `${(rate * 100).toFixed(1)}%`;
}

export function formatCount(value) {
  return new Intl.NumberFormat("en-US").format(value);
}

export function relativeReduction(before, after) {
  return (before - after) / before;
}

export function comparisonNarrative(before, after) {
  const reduction = relativeReduction(before, after);
  return `Improving user training from None to Advanced, with all other controls unchanged, reduces the modeled chance an attack passes every layer from ${formatPct(before)} to ${formatPct(after)}, a ${formatReduction(reduction)} reduction.`;
}

export function wilsonInterval(rate, runs, z = 1.96) {
  const z2 = z * z;
  const denom = 1 + z2 / runs;
  const center = (rate + z2 / (2 * runs)) / denom;
  const margin =
    (z * Math.sqrt((rate * (1 - rate)) / runs + z2 / (4 * runs * runs))) / denom;
  return [center - margin, center + margin];
}

export function counts() {
  const phishing = emails.filter((email) => email.label === "phishing").length;
  return {
    total: emails.length,
    phishing,
    genuine: emails.length - phishing,
  };
}

export const narrative = comparisonNarrative(
  SHOWCASE.passRateUntrained,
  SHOWCASE.passRateTrained,
);

export const reduction = relativeReduction(
  SHOWCASE.passRateUntrained,
  SHOWCASE.passRateTrained,
);

export const assumptions = [
  ["A1", "Layers are independent, given the email."],
  ["A2", "Training levels map to base user catch rates: none 0.30, basic 0.55, advanced 0.75."],
  ["A3", "Each email has one primary attack vector, chosen by severity."],
  ["A4", "Password-protected archives halve antivirus detection."],
  ["A5", "Aggregate pass-through weights each phishing email equally."],
  ["A6", "Simulation runs on emails predicted as phishing."],
  ["A7", "Classification threshold is 0.50."],
];

export function simulationPayload() {
  const [low, high] = wilsonInterval(SHOWCASE.passRateUntrained, RUNS);
  return {
    runs: RUNS,
    seed: SEED,
    engine_version: ENGINE_VERSION,
    figures: "illustrative",
    aggregate: {
      email_count: counts().phishing,
      runs: RUNS,
      pass_rate: SHOWCASE.passRateUntrained,
      blocked_rate: 1 - SHOWCASE.passRateUntrained,
      ci95: [low, high],
      closed_form: SHOWCASE.passRateUntrained,
    },
  };
}

export function validationRows() {
  return emails.map((email, index) => ({
    ...email,
    actual: email.label,
    predicted: index < 18 ? email.label : email.label === "phishing" ? "genuine" : "phishing",
    correct: index < 18,
  }));
}
