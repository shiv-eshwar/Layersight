import type { FilterRule, LayerConfig, SimEmail } from "@/lib/flagship/types";

export const ILLUSTRATIVE_ID = "email_illustrative";
export const DATASET_NAME = "Illustrative phishing set";

const quarantineDmarc: FilterRule = {
  id: "quarantine_dmarc_fail",
  description: "Quarantine messages that fail DMARC",
  match: { feature: "auth.dmarc", op: "eq", value: "fail" },
  catch_rate: 0.85,
  enabled: true,
};

const blockExecutables: FilterRule = {
  id: "block_executables",
  description: "Block executable and script attachments",
  match: { feature: "attachment.risk_class", op: "in", value: ["executable", "script"] },
  catch_rate: 0.98,
  enabled: true,
};

function baseConfig(name: string, level: LayerConfig["user_training"]["level"]): LayerConfig {
  return {
    schema_version: 1,
    name,
    org_domains: ["contoso.example"],
    email_filter: {
      base_catch_rate: 0.35,
      rules: [structuredClone(quarantineDmarc), structuredClone(blockExecutables)],
    },
    user_training: { level, catch_rate: null },
    application_control: {
      effectiveness: 0.25,
      overrides: { macro_document: 0.9, executable: 0.95 },
    },
    antivirus: { detection_rate: 0.55 },
    segmentation: { containment_rate: 0.4, applies_to_credential_harvest: true },
    simulation: { runs: 10_000, seed: 42 },
  };
}

export function untrainedConfig(): LayerConfig {
  return baseConfig("Untrained users (v1)", "none");
}

export function trainedConfig(): LayerConfig {
  return baseConfig("Trained users (v2)", "advanced");
}

export const WORKSPACE_EMAILS: SimEmail[] = [
  {
    email_id: ILLUSTRATIVE_ID,
    subject: "Budget archive for Friday's review",
    attack_vector: "malware_attachment",
    cue_score: 0.5,
    features: {
      "auth.dmarc": "pass",
      "auth.spf": "pass",
      "header.reply_to_mismatch": false,
      "links.max_lookalike_score": 0,
      "attachment.risk_class": "archive",
      "attachment.password_protected": false,
      "content.urgency": false,
    },
  },
  {
    email_id: "email_credential",
    subject: "Sign in to view your pay stub",
    attack_vector: "credential_harvest",
    cue_score: 0.5,
    features: {
      "auth.dmarc": "pass",
      "links.max_lookalike_score": 0.2,
      "content.credential_request": true,
      "header.reply_to_mismatch": true,
    },
  },
  {
    email_id: "email_payment",
    subject: "Updated bank details for the vendor",
    attack_vector: "payment_fraud",
    cue_score: 0.5,
    features: {
      "auth.dmarc": "pass",
      "content.payment_request": true,
      "links.max_lookalike_score": 0,
    },
  },
  {
    email_id: "email_dmarc",
    subject: "Your mailbox will be locked today",
    attack_vector: "credential_harvest",
    cue_score: 0.8,
    features: {
      "auth.dmarc": "fail",
      "links.max_lookalike_score": 0.92,
      "content.urgency": true,
      "content.credential_request": true,
      "header.reply_to_mismatch": true,
    },
  },
  {
    email_id: "email_executable",
    subject: "Enable content to view the purchase order",
    attack_vector: "malware_link",
    cue_score: 0.5,
    features: {
      "auth.dmarc": "pass",
      "attachment.risk_class": "executable",
      "link.risk_class": "executable",
      "links.max_lookalike_score": 0.1,
    },
  },
];

export function selectEmails(scope: string, emails: readonly SimEmail[] = WORKSPACE_EMAILS): SimEmail[] {
  if (scope === "all") return [...emails];
  const match = emails.filter((email) => email.email_id === scope);
  if (match.length > 0) return match;
  return emails.filter((email) => email.email_id === ILLUSTRATIVE_ID);
}

export const CANONICAL_UNTRAINED_YAML = `schema_version: 1
name: Untrained users (v1)
org_domains:
  - contoso.example
email_filter:
  base_catch_rate: 0.35
  rules:
    - id: quarantine_dmarc_fail
      description: Quarantine messages that fail DMARC
      match:
        feature: auth.dmarc
        op: eq
        value: fail
      catch_rate: 0.85
      enabled: true
    - id: block_executables
      description: Block executable and script attachments
      match:
        feature: attachment.risk_class
        op: in
        value:
          - executable
          - script
      catch_rate: 0.98
      enabled: true
user_training:
  level: none
  catch_rate: null
application_control:
  effectiveness: 0.25
  overrides:
    macro_document: 0.9
    executable: 0.95
antivirus:
  detection_rate: 0.55
segmentation:
  containment_rate: 0.4
  applies_to_credential_harvest: true
simulation:
  runs: 10000
  seed: 42
`;
