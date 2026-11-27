export const DEMO_ROUTES = [
  { path: "/", title: "Security Command Center" },
  { path: "/triage", title: "Email Triage" },
  { path: "/intelligence", title: "URL & Domain Intelligence" },
  { path: "/defense", title: "Defense Layer Builder" },
  { path: "/simulator", title: "Attack Simulator" },
  { path: "/compare", title: "Before vs After" },
  { path: "/academy", title: "Awareness Academy" },
  { path: "/reports", title: "Validation & Reports" },
] as const;

export const SHOWCASE_PATH = "/triage/em-showcase";

export const BUDGETS = {
  pageLoadMs: 2_000,
  simulateMs: 300,
  whatIfMs: 250,
  analyzeMs: 1_000,
  rehearsalMs: 180_000,
} as const;

export const CLOSING_LINE =
  "Traditional phishing tools tell you what is dangerous. LayerSight tells you how vulnerable you are, where your defenses fail, and what to improve next.";
