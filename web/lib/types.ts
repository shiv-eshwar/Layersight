export type Band = "critical" | "high" | "suspicious" | "low";
export type Verdict = "phishing" | "genuine";

export type DatasetSummary = {
  id: string;
  name: string;
  source: string;
  emails: number;
  created_at: string;
};

export type ConfigSummary = { id: string; name: string };

export type TriageEmail = {
  id: string;
  filename: string;
  subject: string;
  sender: string;
  sender_domain: string;
  prediction: Verdict;
  band: Band;
  risk_score: number;
  attack_vector: string;
  top_evidence: string | null;
  date: string | null;
  ground_truth: Verdict | null;
};

export type TriageResponse = {
  dataset_id: string;
  counts: { all: number; phishing: number; genuine: number };
  emails: TriageEmail[];
};

export type Evidence = {
  rule_id: string;
  category: string;
  title: string;
  detail: string;
  location: string | null;
  contribution: number;
  share: number;
  user_visible: boolean;
};

export type CharDiff = { char: string; changed: boolean };

export type LinkView = {
  text: string;
  href: string;
  display_href: string;
  registrable_domain: string;
  similarity: number;
  closest: string | null;
  technique: string | null;
  candidate_label: string;
  closest_label: string;
  diff: CharDiff[];
};

export type Address = {
  display_name: string;
  address: string;
  domain: string;
  registrable_domain: string;
};

export type EmailDetail = {
  id: string;
  dataset_id: string;
  filename: string;
  ground_truth: Verdict | null;
  sha256: string;
  presentation: {
    subject: string;
    date: string | null;
    sender: Address;
    reply_to: Address | null;
    return_path: Address | null;
    auth: { spf: string; dkim: string; dmarc: string };
    mismatches: string[];
    links: LinkView[];
    attachments: {
      filename: string;
      content_type: string;
      extension: string;
      risk_class: string;
      double_extension: boolean;
    }[];
    body_text_sanitized: string;
    highlights: string[];
    parse_warnings: string[];
  };
  analysis: {
    risk_score: number;
    label: Verdict;
    band: Band;
    attack_vector: string;
    vector_reason: string;
    evidence: Evidence[];
    advice: string[];
    engine_version: string;
    weights_hash: string;
  };
  outlook: {
    baseline: { config_name: string; simulation: SimulationSide };
    comparison: { config_name: string; simulation: SimulationSide };
    relative_reduction: number;
    narrative: string;
    seed: number;
    runs: number;
  } | null;
};

export type SimulationSide = {
  pass_rate: number;
  closed_form: number;
  ci95: [number, number];
  passed: number;
  layers: { layer: string; applicable: boolean; p_stop: number; reasons: string[]; entered: number; stopped: number }[];
};

export type ValidationReport = {
  total: number;
  labeled: number;
  actual_phishing: number;
  actual_genuine: number;
  correct: number | null;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  false_positive_rate: number | null;
  confusion: { tp: number; fp: number; tn: number; fn: number };
  per_email: {
    filename: string;
    subject: string;
    actual: string | null;
    predicted: string;
    risk_score: number;
    band: string;
    correct: boolean | null;
    top_evidence: string | null;
    explanation: string | null;
  }[];
  misclassifications: { filename: string; subject: string; explanation: string | null; risk_score: number }[];
  engine_version: string;
  weights_hash: string;
  threshold: number;
  dataset_name: string;
  notes: string[];
  pass_through: {
    narrative: string;
    relative_reduction: number;
    seed: number;
    runs: number;
    baseline: { config_name: string; simulation: { closed_form: number; pass_rate: number; ci95: [number, number] } };
    comparison: { config_name: string; simulation: { closed_form: number; pass_rate: number; ci95: [number, number] } };
  };
};
