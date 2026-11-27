/** Documented defaults from the engine. Shown only when the API is unreachable. */

export const documentedAssumptions = {
  layers_independent_given_email: true,
  training_base_catch_rate: { none: 0.3, basic: 0.55, advanced: 0.75 },
  training_cue_sensitivity: { none: 0.1, basic: 0.25, advanced: 0.35 },
  classification_threshold: 0.5,
  score_bias: -2,
  password_archive_antivirus_factor: 0.5,
  aggregate_weights_emails_equally: true,
  simulate_predicted_phishing_only: true,
};

export type Assumptions = typeof documentedAssumptions;

export const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
