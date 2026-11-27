import { parse, stringify } from "yaml";
import { z } from "zod";

import type { FilterRule, LayerConfig, MatchOp, TrainingLevel } from "@/lib/flagship/types";

export interface FieldError {
  field: string;
  message: string;
}

export interface AdaptResult {
  config: LayerConfig | null;
  warnings: string[];
  errors: FieldError[];
}

const MATCH_OPS = ["eq", "ne", "in", "gte", "lte", "contains", "exists"] as const;

const rateSchema = z.number().min(0).max(1);
const levelSchema = z.enum(["none", "basic", "advanced"]);

function asRate(value: unknown, field: string, warnings: string[]): number | null {
  if (typeof value === "string" && value.trim().endsWith("%")) {
    const parsed = Number(value.trim().slice(0, -1));
    if (!Number.isFinite(parsed)) return null;
    warnings.push(`${field} was read as a percent and stored as a fraction.`);
    return parsed / 100;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    if (value > 1 && value <= 100) {
      warnings.push(`${field} was above 1 and was read as a percent.`);
      return value / 100;
    }
    return value;
  }
  return null;
}

function asLevel(value: unknown, warnings: string[]): TrainingLevel | null {
  if (typeof value !== "string") return null;
  const level = value.trim().toLowerCase();
  if (level === "none" || level === "untrained") {
    if (level === "untrained") warnings.push("user_training.level untrained was read as none.");
    return "none";
  }
  if (level === "basic") return "basic";
  if (level === "advanced" || level === "trained") {
    if (level === "trained") warnings.push("user_training.level trained was read as advanced.");
    return "advanced";
  }
  return null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

function adaptRule(value: unknown, index: number, warnings: string[], errors: FieldError[]): FilterRule | null {
  const record = asRecord(value);
  const field = `email_filter.rules[${index}]`;
  if (!record) {
    errors.push({ field, message: "Each rule must be a mapping." });
    return null;
  }
  const id = typeof record.id === "string" ? record.id.trim() : "";
  if (!id) errors.push({ field: `${field}.id`, message: "Rule id is required." });
  const match = asRecord(record.match);
  const op = typeof match?.op === "string" ? match.op : "";
  if (!MATCH_OPS.includes(op as MatchOp)) {
    errors.push({
      field: `${field}.match.op`,
      message: "Operator must be eq, ne, in, gte, lte, contains, or exists.",
    });
  }
  const feature = typeof match?.feature === "string" ? match.feature.trim() : "";
  if (!feature) errors.push({ field: `${field}.match.feature`, message: "Feature name is required." });
  const catchRate = asRate(record.catch_rate, `${field}.catch_rate`, warnings);
  if (catchRate === null || !rateSchema.safeParse(catchRate).success) {
    errors.push({ field: `${field}.catch_rate`, message: "Catch rate must be between 0 and 1." });
  }
  if (errors.some((error) => error.field.startsWith(field))) return null;
  let matchValue: FilterRule["match"]["value"];
  if (Array.isArray(match?.value)) {
    matchValue = match.value.map((item) => String(item));
  } else if (
    typeof match?.value === "string" ||
    typeof match?.value === "number" ||
    typeof match?.value === "boolean" ||
    match?.value === null
  ) {
    matchValue = match.value;
  }
  return {
    id,
    description: typeof record.description === "string" ? record.description : "",
    match: { feature, op: op as MatchOp, value: matchValue },
    catch_rate: catchRate ?? 0,
    enabled: record.enabled !== false,
  };
}

export function adaptConfig(input: unknown): AdaptResult {
  const warnings: string[] = [];
  const errors: FieldError[] = [];
  const record = asRecord(input);
  if (!record) {
    return { config: null, warnings, errors: [{ field: "config", message: "Configuration must be a YAML mapping." }] };
  }

  const name = typeof record.name === "string" ? record.name.trim() : "";
  if (!name) errors.push({ field: "name", message: "Name is required." });

  const filter = asRecord(record.email_filter) ?? {};
  const base = asRate(filter.base_catch_rate, "email_filter.base_catch_rate", warnings);
  if (base === null || !rateSchema.safeParse(base).success) {
    errors.push({
      field: "email_filter.base_catch_rate",
      message: "Base catch rate must be between 0 and 1.",
    });
  }
  const rawRules = Array.isArray(filter.rules) ? filter.rules : [];
  const rules = rawRules
    .map((rule, index) => adaptRule(rule, index, warnings, errors))
    .filter((rule): rule is FilterRule => rule !== null);

  const training = asRecord(record.user_training);
  const level = asLevel(training?.level ?? record.user_training, warnings);
  if (!level || !levelSchema.safeParse(level).success) {
    errors.push({
      field: "user_training.level",
      message: "Level must be none, basic, or advanced.",
    });
  }
  let catchRate: number | null = null;
  if (training && training.catch_rate !== null && training.catch_rate !== undefined) {
    catchRate = asRate(training.catch_rate, "user_training.catch_rate", warnings);
    if (catchRate === null || !rateSchema.safeParse(catchRate).success) {
      errors.push({
        field: "user_training.catch_rate",
        message: "Custom catch rate must be between 0 and 1, or empty.",
      });
    }
  }

  const application = asRecord(record.application_control) ?? {};
  const effectiveness = asRate(application.effectiveness, "application_control.effectiveness", warnings);
  if (effectiveness === null || !rateSchema.safeParse(effectiveness).success) {
    errors.push({
      field: "application_control.effectiveness",
      message: "Effectiveness must be between 0 and 1.",
    });
  }
  const overrides: Record<string, number> = {};
  const rawOverrides = asRecord(application.overrides) ?? {};
  for (const [key, value] of Object.entries(rawOverrides)) {
    const parsed = asRate(value, `application_control.overrides.${key}`, warnings);
    if (parsed === null || !rateSchema.safeParse(parsed).success) {
      errors.push({
        field: `application_control.overrides.${key}`,
        message: "Override must be between 0 and 1.",
      });
    } else {
      overrides[key] = parsed;
    }
  }

  const antivirus = asRecord(record.antivirus) ?? {};
  const detection = asRate(antivirus.detection_rate, "antivirus.detection_rate", warnings);
  if (detection === null || !rateSchema.safeParse(detection).success) {
    errors.push({
      field: "antivirus.detection_rate",
      message: "Detection rate must be between 0 and 1.",
    });
  }

  const segmentation = asRecord(record.segmentation) ?? {};
  const containment = asRate(segmentation.containment_rate, "segmentation.containment_rate", warnings);
  if (containment === null || !rateSchema.safeParse(containment).success) {
    errors.push({
      field: "segmentation.containment_rate",
      message: "Containment rate must be between 0 and 1.",
    });
  }

  const simulation = asRecord(record.simulation) ?? {};
  const runs = typeof simulation.runs === "number" ? simulation.runs : 10_000;
  const seed = typeof simulation.seed === "number" ? simulation.seed : 42;
  if (!Number.isInteger(runs) || runs < 1) {
    errors.push({ field: "simulation.runs", message: "Runs must be a positive integer." });
  }
  if (!Number.isInteger(seed)) {
    errors.push({ field: "simulation.seed", message: "Seed must be an integer." });
  }

  const domains = Array.isArray(record.org_domains)
    ? record.org_domains.filter((domain): domain is string => typeof domain === "string")
    : ["contoso.example"];

  if (errors.length > 0) return { config: null, warnings, errors };

  return {
    config: {
      schema_version: 1,
      name,
      org_domains: domains,
      email_filter: { base_catch_rate: base ?? 0, rules },
      user_training: { level: level ?? "none", catch_rate: catchRate },
      application_control: { effectiveness: effectiveness ?? 0, overrides },
      antivirus: { detection_rate: detection ?? 0 },
      segmentation: {
        containment_rate: containment ?? 0,
        applies_to_credential_harvest: segmentation.applies_to_credential_harvest !== false,
      },
      simulation: { runs, seed },
    },
    warnings,
    errors,
  };
}

export function parseConfigYaml(text: string): AdaptResult {
  try {
    return adaptConfig(parse(text));
  } catch (error) {
    const message = error instanceof Error ? error.message : "YAML could not be read.";
    return { config: null, warnings: [], errors: [{ field: "yaml", message }] };
  }
}

export function exportConfigYaml(config: LayerConfig): string {
  return stringify(config, { lineWidth: 88 });
}
