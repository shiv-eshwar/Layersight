/** Shapes shared with engine/layersight/models.py. Additive fields stay optional. */

export const LAYERS = [
  "email_filter",
  "user",
  "application_control",
  "antivirus",
  "segmentation",
] as const;

export type LayerName = (typeof LAYERS)[number];

export type AttackVector =
  | "malware_attachment"
  | "malware_link"
  | "credential_harvest"
  | "payment_fraud";

export type TrainingLevel = "none" | "basic" | "advanced";

export type MatchOp = "eq" | "ne" | "in" | "gte" | "lte" | "contains" | "exists";

export type JsonScalar = string | number | boolean | null;

export type MatchValue = JsonScalar | string[];

export interface RuleMatch {
  feature: string;
  op: MatchOp;
  value?: MatchValue;
}

export interface FilterRule {
  id: string;
  description: string;
  match: RuleMatch;
  catch_rate: number;
  enabled: boolean;
}

export interface LayerConfig {
  schema_version: number;
  name: string;
  org_domains: string[];
  email_filter: {
    base_catch_rate: number;
    rules: FilterRule[];
  };
  user_training: {
    level: TrainingLevel;
    catch_rate: number | null;
  };
  application_control: {
    effectiveness: number;
    overrides: Partial<Record<string, number>>;
  };
  antivirus: {
    detection_rate: number;
  };
  segmentation: {
    containment_rate: number;
    applies_to_credential_harvest: boolean;
  };
  simulation: {
    runs: number;
    seed: number;
  };
}

export interface SimEmail {
  email_id: string;
  subject: string;
  attack_vector: AttackVector;
  cue_score: number;
  features: Record<string, unknown>;
}

export interface LayerOutcome {
  layer: LayerName;
  applicable: boolean;
  p_stop: number;
  reasons: string[];
  entered: number;
  stopped: number;
}

export interface EmailSimulation {
  email_id: string;
  id?: string;
  filename?: string;
  subject?: string;
  attack_vector: AttackVector;
  layers: LayerOutcome[];
  passed: number;
  pass_rate: number;
  ci95: [number, number];
  closed_form: number;
}

export interface AggregateLayer {
  layer: LayerName;
  entered: number;
  stopped: number;
  applicable_emails: number;
}

export interface AggregateSimulation {
  email_count: number;
  runs: number;
  pass_rate: number;
  blocked_rate: number;
  ci95: [number, number];
  closed_form: number;
  layers: AggregateLayer[];
}

export interface SimulationResult {
  config_snapshot: LayerConfig;
  runs: number;
  seed: number;
  per_email: EmailSimulation[];
  aggregate: AggregateSimulation;
  engine_version: string;
}

export interface ConfigChange {
  path: string;
  before: JsonScalar;
  after: JsonScalar;
}

export interface EmailComparison {
  email_id: string;
  pass_rate_a: number;
  pass_rate_b: number;
  absolute_reduction: number;
  attack_vector?: AttackVector;
  subject?: string;
  filename?: string;
}

export interface ComparisonResult {
  config_a_name: string;
  config_b_name: string;
  result_a: SimulationResult;
  result_b: SimulationResult;
  absolute_reduction: number;
  relative_reduction: number;
  narrative: string;
  changes: ConfigChange[];
  per_email: EmailComparison[];
}

export interface Recommendation {
  id: string;
  title: string;
  detail: string;
  layer: LayerName;
  absolute_reduction: number;
  relative_reduction: number;
  vectors_helped: AttackVector[];
}

export interface SensitivityRow {
  layer: LayerName;
  baseline: number;
  decreased: number;
  increased: number;
}

export interface RecommendationSet {
  recommendations: Recommendation[];
  sensitivity: SensitivityRow[];
}

export interface Particle {
  id: number;
  stopAt: number;
}

export const LAYER_LABEL: Record<LayerName, string> = {
  email_filter: "Email filter",
  user: "User training",
  application_control: "Application control",
  antivirus: "Antivirus",
  segmentation: "Segmentation",
};

export const VECTOR_LABEL: Record<AttackVector, string> = {
  malware_attachment: "Malware attachment",
  malware_link: "Malware link",
  credential_harvest: "Credential harvesting",
  payment_fraud: "Payment fraud",
};

export const LEVEL_LABEL: Record<TrainingLevel, string> = {
  none: "None",
  basic: "Basic",
  advanced: "Advanced",
};

export const LAYER_COLOR: Record<LayerName, string> = {
  email_filter: "#6d8bff",
  user: "#8b6cff",
  application_control: "#2ec8c0",
  antivirus: "#3ddc97",
  segmentation: "#ff8a3d",
};

export const PASSED_COLOR = "#ff5c6c";

export const PREVIEW_ENGINE = "preview";

export const TRAINING_BASE: Record<TrainingLevel, number> = {
  none: 0.3,
  basic: 0.55,
  advanced: 0.75,
};

export const TRAINING_SENSITIVITY: Record<TrainingLevel, number> = {
  none: 0.1,
  basic: 0.25,
  advanced: 0.35,
};
