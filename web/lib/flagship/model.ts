/**
 * Closed-form layer model from engineering.md §10–§13.
 *
 * Screens render SimulationResult values. This module is the preview used
 * until POST /api/v1/simulations returns a run. Expected funnel counts use
 * round-half-up of (runs × cumulative survival), which reproduces the
 * illustrative remaining sequence 6500, 4550, 3413, 1536, 921.
 */

import { formatPct, formatRel } from "@/lib/flagship/format";
import {
  LAYERS,
  LEVEL_LABEL,
  PREVIEW_ENGINE,
  TRAINING_BASE,
  TRAINING_SENSITIVITY,
  VECTOR_LABEL,
  type AttackVector,
  type ComparisonResult,
  type ConfigChange,
  type EmailSimulation,
  type FilterRule,
  type JsonScalar,
  type LayerConfig,
  type LayerName,
  type LayerOutcome,
  type Particle,
  type Recommendation,
  type RecommendationSet,
  type SimEmail,
  type SimulationResult,
  type TrainingLevel,
} from "@/lib/flagship/types";

const USER_FLOOR = 0.02;
const USER_CEILING = 0.98;

export function clamp(value: number, low: number, high: number): number {
  return Math.min(high, Math.max(low, value));
}

export function wilsonInterval(rate: number, runs: number, z = 1.96): [number, number] {
  if (runs <= 0) return [0, 0];
  const z2 = z * z;
  const denom = 1 + z2 / runs;
  const center = (rate + z2 / (2 * runs)) / denom;
  const margin =
    (z * Math.sqrt((rate * (1 - rate)) / runs + z2 / (4 * runs * runs))) / denom;
  return [clamp(center - margin, 0, 1), clamp(center + margin, 0, 1)];
}

export function layerApplies(
  vector: AttackVector,
  layer: LayerName,
  config: LayerConfig,
): boolean {
  if (layer === "email_filter" || layer === "user") return true;
  const malware = vector === "malware_attachment" || vector === "malware_link";
  if (layer === "application_control" || layer === "antivirus") return malware;
  if (vector === "payment_fraud") return false;
  if (malware) return true;
  return config.segmentation.applies_to_credential_harvest;
}

function ruleMatches(rule: FilterRule, features: Record<string, unknown>): boolean {
  if (!rule.enabled) return false;
  const actual = features[rule.match.feature];
  const expected = rule.match.value;
  switch (rule.match.op) {
    case "exists":
      return actual !== undefined && actual !== null;
    case "eq":
      return actual === expected;
    case "ne":
      return actual !== expected;
    case "in":
      return Array.isArray(expected) && expected.some((item) => item === actual);
    case "gte":
      return typeof actual === "number" && typeof expected === "number" && actual >= expected;
    case "lte":
      return typeof actual === "number" && typeof expected === "number" && actual <= expected;
    case "contains":
      return (
        typeof actual === "string" &&
        typeof expected === "string" &&
        actual.includes(expected)
      );
    default:
      return false;
  }
}

function riskClass(email: SimEmail): string | null {
  const attachment = email.features["attachment.risk_class"];
  const link = email.features["link.risk_class"];
  if (email.attack_vector === "malware_link" && typeof link === "string") return link;
  if (typeof attachment === "string") return attachment;
  if (typeof link === "string") return link;
  return null;
}

function percent(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

export function layerProbabilities(
  email: SimEmail,
  config: LayerConfig,
): Pick<LayerOutcome, "layer" | "applicable" | "p_stop" | "reasons">[] {
  return LAYERS.map((layer) => {
    const applicable = layerApplies(email.attack_vector, layer, config);
    if (!applicable) {
      return {
        layer,
        applicable: false,
        p_stop: 0,
        reasons: [`Not applicable to ${VECTOR_LABEL[email.attack_vector].toLowerCase()}.`],
      };
    }
    if (layer === "email_filter") {
      const matched = config.email_filter.rules.filter((rule) =>
        ruleMatches(rule, email.features),
      );
      let survival = 1 - config.email_filter.base_catch_rate;
      for (const rule of matched) survival *= 1 - rule.catch_rate;
      const reasons = [`Base catch rate ${percent(config.email_filter.base_catch_rate)}.`];
      for (const rule of matched) {
        reasons.push(`Rule ${rule.id} matched (${rule.catch_rate.toFixed(2)}).`);
      }
      return { layer, applicable: true, p_stop: 1 - survival, reasons };
    }
    if (layer === "user") {
      const override = config.user_training.catch_rate;
      if (override !== null) {
        return {
          layer,
          applicable: true,
          p_stop: override,
          reasons: [`Custom catch rate ${percent(override)}.`],
        };
      }
      const level = config.user_training.level;
      const base = TRAINING_BASE[level];
      const sensitivity = TRAINING_SENSITIVITY[level];
      const pStop = clamp(base + sensitivity * (email.cue_score - 0.5), USER_FLOOR, USER_CEILING);
      return {
        layer,
        applicable: true,
        p_stop: pStop,
        reasons: [
          `Training level ${level}, base catch rate ${base.toFixed(2)}, cue ${email.cue_score.toFixed(2)}.`,
        ],
      };
    }
    if (layer === "application_control") {
      const risk = riskClass(email);
      const override = risk ? config.application_control.overrides[risk] : undefined;
      if (override !== undefined) {
        return {
          layer,
          applicable: true,
          p_stop: override,
          reasons: [`Override for ${risk} (${override.toFixed(2)}).`],
        };
      }
      return {
        layer,
        applicable: true,
        p_stop: config.application_control.effectiveness,
        reasons: [`Effectiveness ${percent(config.application_control.effectiveness)}.`],
      };
    }
    if (layer === "antivirus") {
      let pStop = config.antivirus.detection_rate;
      const archive =
        email.features["attachment.password_protected"] === true &&
        email.features["attachment.risk_class"] === "archive";
      if (archive) pStop *= 0.5;
      return {
        layer,
        applicable: true,
        p_stop: pStop,
        reasons: [
          archive
            ? `Detection rate ${percent(config.antivirus.detection_rate)}, halved for a password-protected archive.`
            : `Detection rate ${percent(config.antivirus.detection_rate)}.`,
        ],
      };
    }
    return {
      layer,
      applicable: true,
      p_stop: config.segmentation.containment_rate,
      reasons: [`Containment rate ${percent(config.segmentation.containment_rate)}.`],
    };
  });
}

function roundCount(value: number): number {
  // Snap binary noise so 3412.5 stays 3412.5 before half-up rounding.
  const snapped = Math.round(value * 1e6) / 1e6;
  return Math.round(snapped);
}

function funnel(probabilities: number[], runs: number): { entered: number; stopped: number }[] {
  let survival = 1;
  let previous = runs;
  return probabilities.map((pStop) => {
    survival *= 1 - pStop;
    const remaining = roundCount(runs * survival);
    const stopped = Math.max(0, previous - remaining);
    const row = { entered: previous, stopped };
    previous = previous - stopped;
    return row;
  });
}

export function closedForm(probabilities: number[]): number {
  return probabilities.reduce((product, pStop) => product * (1 - pStop), 1);
}

function simulateEmail(email: SimEmail, config: LayerConfig, runs: number): EmailSimulation {
  const probabilities = layerProbabilities(email, config);
  const counts = funnel(
    probabilities.map((layer) => layer.p_stop),
    runs,
  );
  const layers: LayerOutcome[] = probabilities.map((layer, index) => ({
    ...layer,
    entered: counts[index]?.entered ?? 0,
    stopped: counts[index]?.stopped ?? 0,
  }));
  const passed = Math.max(0, runs - layers.reduce((sum, layer) => sum + layer.stopped, 0));
  const exact = closedForm(probabilities.map((layer) => layer.p_stop));
  return {
    email_id: email.email_id,
    attack_vector: email.attack_vector,
    layers,
    passed,
    pass_rate: runs === 0 ? 0 : passed / runs,
    ci95: wilsonInterval(exact, runs),
    closed_form: exact,
  };
}

function mean(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export function simulate(
  emails: readonly SimEmail[],
  config: LayerConfig,
  runs = config.simulation.runs,
  seed = config.simulation.seed,
): SimulationResult {
  const perEmail = emails.map((email) => simulateEmail(email, config, runs));
  const closed = mean(perEmail.map((email) => email.closed_form));
  const passRate = mean(perEmail.map((email) => email.pass_rate));
  return {
    config_snapshot: {
      ...structuredClone(config),
      simulation: { runs, seed },
    },
    runs,
    seed,
    per_email: perEmail,
    aggregate: {
      email_count: emails.length,
      runs,
      pass_rate: passRate,
      blocked_rate: 1 - passRate,
      ci95: wilsonInterval(closed, Math.max(1, runs * Math.max(emails.length, 1))),
      closed_form: closed,
      layers: LAYERS.map((layer) => {
        const rows = perEmail.map(
          (email) => email.layers.find((item) => item.layer === layer)!,
        );
        return {
          layer,
          entered: Math.round(mean(rows.map((row) => row.entered))),
          stopped: Math.round(mean(rows.map((row) => row.stopped))),
          applicable_emails: rows.filter((row) => row.applicable).length,
        };
      }),
    },
    engine_version: PREVIEW_ENGINE,
  };
}

function scalar(value: unknown): JsonScalar {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return value;
  }
  return null;
}

export function diffConfigs(before: LayerConfig, after: LayerConfig): ConfigChange[] {
  const changes: ConfigChange[] = [];
  const push = (path: string, left: unknown, right: unknown) => {
    if (left === right) return;
    if (typeof left === "number" && typeof right === "number" && Math.abs(left - right) < 1e-9) {
      return;
    }
    changes.push({ path, before: scalar(left), after: scalar(right) });
  };

  push("name", before.name, after.name);
  push("org_domains", before.org_domains.join(","), after.org_domains.join(","));
  push(
    "email_filter.base_catch_rate",
    before.email_filter.base_catch_rate,
    after.email_filter.base_catch_rate,
  );
  push("user_training.level", before.user_training.level, after.user_training.level);
  push("user_training.catch_rate", before.user_training.catch_rate, after.user_training.catch_rate);
  push(
    "application_control.effectiveness",
    before.application_control.effectiveness,
    after.application_control.effectiveness,
  );
  const overrideKeys = new Set([
    ...Object.keys(before.application_control.overrides),
    ...Object.keys(after.application_control.overrides),
  ]);
  for (const key of overrideKeys) {
    push(
      `application_control.overrides.${key}`,
      before.application_control.overrides[key] ?? null,
      after.application_control.overrides[key] ?? null,
    );
  }
  push("antivirus.detection_rate", before.antivirus.detection_rate, after.antivirus.detection_rate);
  push(
    "segmentation.containment_rate",
    before.segmentation.containment_rate,
    after.segmentation.containment_rate,
  );
  push(
    "segmentation.applies_to_credential_harvest",
    before.segmentation.applies_to_credential_harvest,
    after.segmentation.applies_to_credential_harvest,
  );
  push("simulation.runs", before.simulation.runs, after.simulation.runs);
  push("simulation.seed", before.simulation.seed, after.simulation.seed);

  const beforeRules = new Map(before.email_filter.rules.map((rule) => [rule.id, rule]));
  const afterRules = new Map(after.email_filter.rules.map((rule) => [rule.id, rule]));
  for (const id of new Set([...beforeRules.keys(), ...afterRules.keys()])) {
    const left = beforeRules.get(id);
    const right = afterRules.get(id);
    if (!left || !right) {
      changes.push({
        path: `email_filter.rules.${id}`,
        before: left ? "present" : null,
        after: right ? "present" : null,
      });
      continue;
    }
    push(`email_filter.rules.${id}.enabled`, left.enabled, right.enabled);
    push(`email_filter.rules.${id}.catch_rate`, left.catch_rate, right.catch_rate);
  }
  return changes;
}

export function comparisonNarrative(
  before: number,
  after: number,
  changes: ConfigChange[],
): string {
  const from = formatPct(before);
  const to = formatPct(after);
  const relative = before === 0 ? 0 : (before - after) / before;
  const amount = formatRel(relative);
  const reduces = after <= before;
  const verb = reduces ? "reduces" : "increases";
  const noun = reduces ? "reduction" : "increase";
  const controls = changes.filter(
    (change) => change.path !== "name" && change.path !== "org_domains",
  );
  const onlyTraining = controls.length === 1 && controls[0]?.path === "user_training.level";
  if (onlyTraining) {
    const change = controls[0];
    const left = LEVEL_LABEL[String(change?.before) as TrainingLevel] ?? String(change?.before);
    const right = LEVEL_LABEL[String(change?.after) as TrainingLevel] ?? String(change?.after);
    const action = reduces ? "Improving" : "Changing";
    return `${action} user training from ${left} to ${right}, with all other controls unchanged, ${verb} the modeled chance an attack passes every layer from ${from} to ${to}, a ${amount} ${noun}.`;
  }
  return `These configuration changes ${verb} the modeled chance an attack passes every layer from ${from} to ${to}, a ${amount} ${noun}.`;
}

export function compare(
  emails: readonly SimEmail[],
  configA: LayerConfig,
  configB: LayerConfig,
  runs = configA.simulation.runs,
  seed = configA.simulation.seed,
): ComparisonResult {
  const resultA = simulate(emails, configA, runs, seed);
  const resultB = simulate(emails, configB, runs, seed);
  const before = resultA.aggregate.closed_form;
  const after = resultB.aggregate.closed_form;
  const changes = diffConfigs(configA, configB);
  const perEmail = emails
    .map((email) => {
      const left = resultA.per_email.find((item) => item.email_id === email.email_id);
      const right = resultB.per_email.find((item) => item.email_id === email.email_id);
      const passA = left?.closed_form ?? 0;
      const passB = right?.closed_form ?? 0;
      return {
        email_id: email.email_id,
        pass_rate_a: passA,
        pass_rate_b: passB,
        absolute_reduction: passA - passB,
      };
    })
    .sort((a, b) => b.absolute_reduction - a.absolute_reduction);
  return {
    config_a_name: configA.name,
    config_b_name: configB.name,
    result_a: resultA,
    result_b: resultB,
    absolute_reduction: before - after,
    relative_reduction: before === 0 ? 0 : (before - after) / before,
    narrative: comparisonNarrative(before, after, changes),
    changes,
    per_email: perEmail,
  };
}

function withTraining(config: LayerConfig, level: TrainingLevel): LayerConfig {
  return {
    ...config,
    user_training: { level, catch_rate: null },
  };
}

function withRule(config: LayerConfig, rule: FilterRule): LayerConfig {
  return {
    ...config,
    email_filter: {
      ...config.email_filter,
      rules: [...config.email_filter.rules.filter((item) => item.id !== rule.id), rule],
    },
  };
}

function recommendationFor(
  id: string,
  title: string,
  detail: string,
  layer: LayerName,
  emails: readonly SimEmail[],
  before: LayerConfig,
  after: LayerConfig,
): Recommendation | null {
  const base = simulate(emails, before);
  const next = simulate(emails, after);
  const absolute = base.aggregate.closed_form - next.aggregate.closed_form;
  if (absolute <= 1e-6) return null;
  const helped = new Set<AttackVector>();
  for (const email of emails) {
    const left = base.per_email.find((item) => item.email_id === email.email_id);
    const right = next.per_email.find((item) => item.email_id === email.email_id);
    if ((left?.closed_form ?? 0) - (right?.closed_form ?? 0) > 1e-6) {
      helped.add(email.attack_vector);
    }
  }
  return {
    id,
    title,
    detail,
    layer,
    absolute_reduction: absolute,
    relative_reduction:
      base.aggregate.closed_form === 0 ? 0 : absolute / base.aggregate.closed_form,
    vectors_helped: [...helped],
  };
}

export function recommend(
  emails: readonly SimEmail[],
  config: LayerConfig,
): RecommendationSet {
  const items: Recommendation[] = [];
  const nextLevel: Partial<Record<TrainingLevel, TrainingLevel>> = {
    none: "basic",
    basic: "advanced",
  };
  const level = nextLevel[config.user_training.level];
  if (level && config.user_training.catch_rate === null) {
    const item = recommendationFor(
      "raise_training",
      `Advance user training to ${LEVEL_LABEL[level]}`,
      `Moving from ${LEVEL_LABEL[config.user_training.level]} to ${LEVEL_LABEL[level]} changes every email, including credential harvesting and payment fraud that antivirus cannot see.`,
      "user",
      emails,
      config,
      withTraining(config, level),
    );
    if (item) items.push(item);
  }

  if (!config.email_filter.rules.some((rule) => rule.id === "quarantine_dmarc_fail" && rule.enabled)) {
    const item = recommendationFor(
      "quarantine_dmarc",
      "Quarantine DMARC failures",
      "Add a filter rule that catches messages whose DMARC result is fail, at a catch rate of 85%.",
      "email_filter",
      emails,
      config,
      withRule(config, {
        id: "quarantine_dmarc_fail",
        description: "Quarantine messages that fail DMARC",
        match: { feature: "auth.dmarc", op: "eq", value: "fail" },
        catch_rate: 0.85,
        enabled: true,
      }),
    );
    if (item) items.push(item);
  }

  const hasLookalike = config.email_filter.rules.some(
    (rule) =>
      rule.enabled &&
      rule.match.feature === "links.max_lookalike_score" &&
      rule.match.op === "gte",
  );
  if (!hasLookalike) {
    const item = recommendationFor(
      "lookalike_filter",
      "Filter look-alike links",
      "Quarantine messages whose closest look-alike score is 0.85 or higher, at a catch rate of 90%.",
      "email_filter",
      emails,
      config,
      withRule(config, {
        id: "quarantine_lookalikes",
        description: "Quarantine look-alike links",
        match: { feature: "links.max_lookalike_score", op: "gte", value: 0.85 },
        catch_rate: 0.9,
        enabled: true,
      }),
    );
    if (item) items.push(item);
  }

  const macro = config.application_control.overrides.macro_document;
  if (macro === undefined || macro < 0.9) {
    const item = recommendationFor(
      "block_macros",
      "Block macro documents",
      "Set the application-control override for macro documents to 90%.",
      "application_control",
      emails,
      config,
      {
        ...config,
        application_control: {
          ...config.application_control,
          overrides: { ...config.application_control.overrides, macro_document: 0.9 },
        },
      },
    );
    if (item) items.push(item);
  }

  if (config.antivirus.detection_rate < 0.99) {
    const item = recommendationFor(
      "antivirus_detection",
      "Raise antivirus detection 15 points",
      "Endpoint detection only changes malware. Credential harvesting and payment fraud are unchanged.",
      "antivirus",
      emails,
      config,
      {
        ...config,
        antivirus: {
          detection_rate: Math.min(1, Math.round((config.antivirus.detection_rate + 0.15) * 1000) / 1000),
        },
      },
    );
    if (item) items.push(item);
  }

  if (config.segmentation.containment_rate < 0.99) {
    const item = recommendationFor(
      "tighter_segmentation",
      "Tighten segmentation 20 points",
      "Raise containment by 20 points. Payment fraud still bypasses this layer.",
      "segmentation",
      emails,
      config,
      {
        ...config,
        segmentation: {
          ...config.segmentation,
          containment_rate: Math.min(
            1,
            Math.round((config.segmentation.containment_rate + 0.2) * 1000) / 1000,
          ),
        },
      },
    );
    if (item) items.push(item);
  }

  items.sort((a, b) => b.absolute_reduction - a.absolute_reduction || a.title.localeCompare(b.title));

  const baseline = simulate(emails, config).aggregate.closed_form;
  const sensitivity = LAYERS.map((layer) => {
    const decreased = mean(
      emails.map((email) => shiftedClosedForm(email, config, layer, -0.1)),
    );
    const increased = mean(
      emails.map((email) => shiftedClosedForm(email, config, layer, 0.1)),
    );
    return { layer, baseline, decreased, increased };
  }).sort((a, b) => {
    const swing = (row: { baseline: number; decreased: number; increased: number }) =>
      Math.max(Math.abs(row.decreased - row.baseline), Math.abs(row.increased - row.baseline));
    return swing(b) - swing(a);
  });

  return { recommendations: items, sensitivity };
}

function shiftedClosedForm(
  email: SimEmail,
  config: LayerConfig,
  layer: LayerName,
  delta: number,
): number {
  const probabilities = layerProbabilities(email, config).map((item) => {
    if (item.layer !== layer || !item.applicable) return item.p_stop;
    return clamp(item.p_stop + delta, 0, 1);
  });
  return closedForm(probabilities);
}

export function sampleParticles(
  stopped: number[],
  passed: number,
  count = 240,
): Particle[] {
  const weights = [...stopped, Math.max(0, passed)];
  const total = weights.reduce((sum, value) => sum + value, 0);
  if (total <= 0 || count <= 0) return [];
  const raw = weights.map((weight) => (weight / total) * count);
  const base = raw.map((value) => Math.floor(value));
  let left = count - base.reduce((sum, value) => sum + value, 0);
  const order = raw
    .map((value, index) => ({ index, fraction: value - Math.floor(value) }))
    .sort((a, b) => b.fraction - a.fraction || a.index - b.index);
  for (const item of order) {
    if (left <= 0) break;
    base[item.index] = (base[item.index] ?? 0) + 1;
    left -= 1;
  }
  const particles: Particle[] = [];
  let id = 0;
  base.forEach((amount, stopAt) => {
    for (let index = 0; index < amount; index += 1) {
      particles.push({ id, stopAt });
      id += 1;
    }
  });
  return particles;
}
