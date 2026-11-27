import { describe, expect, it } from "vitest";

import { CANONICAL_UNTRAINED_YAML, selectEmails, trainedConfig, untrainedConfig } from "@/lib/flagship/fixtures";
import { formatCount, formatPct, formatRel } from "@/lib/flagship/format";
import {
  compare,
  layerProbabilities,
  recommend,
  sampleParticles,
  simulate,
} from "@/lib/flagship/model";
import { parseConfigYaml } from "@/lib/flagship/yaml-config";

const OFFICIAL_SENTENCE =
  "Improving user training from None to Advanced, with all other controls unchanged, reduces the modeled chance an attack passes every layer from 9.21% to 3.29%, a 64.3% reduction.";

describe("formatters", () => {
  it("formats the published pass-through and counts", () => {
    expect(formatPct(0.0921)).toBe("9.21%");
    expect(formatPct(0.0329)).toBe("3.29%");
    expect(formatCount(10000)).toBe("10,000");
    expect(formatRel(0.6428)).toBe("64.3%");
  });
});

describe("illustrative scenario", () => {
  const illustrative = selectEmails("email_illustrative");

  it("reproduces 9.21%, the funnel, and the trained 3.29%", () => {
    const untrained = simulate(illustrative, untrainedConfig(), 10_000, 42);
    const trained = simulate(illustrative, trainedConfig(), 10_000, 42);
    const email = untrained.per_email[0];
    expect(email).toBeDefined();
    if (!email) return;
    expect(email.layers.map((layer) => layer.entered - layer.stopped)).toEqual([
      6500, 4550, 3413, 1536, 921,
    ]);
    expect(email.passed).toBe(921);
    expect(formatPct(email.pass_rate)).toBe("9.21%");
    expect(formatPct(email.closed_form)).toBe("9.21%");
    expect(email.ci95[0]).toBeLessThan(email.closed_form);
    expect(email.ci95[1]).toBeGreaterThan(email.closed_form);
    expect(formatPct(trained.aggregate.closed_form)).toBe("3.29%");
    expect(trained.per_email[0]?.passed).toBe(329);
  });

  it("writes the official comparison sentence", () => {
    const result = compare(illustrative, untrainedConfig(), trainedConfig(), 10_000, 42);
    expect(result.narrative).toBe(OFFICIAL_SENTENCE);
    expect(result.changes).toContainEqual({
      path: "user_training.level",
      before: "none",
      after: "advanced",
    });
    expect(formatRel(result.relative_reduction)).toBe("64.3%");
  });

  it("updates residual risk for a training change in under 250 ms", () => {
    const advanced = untrainedConfig();
    advanced.user_training = { level: "advanced", catch_rate: null };
    advanced.name = untrainedConfig().name;
    const started = performance.now();
    const result = simulate(illustrative, advanced, 10_000, 42);
    const elapsed = performance.now() - started;
    expect(elapsed).toBeLessThan(250);
    expect(formatPct(result.aggregate.closed_form)).toBe("3.29%");
  });
});

describe("vector applicability", () => {
  it("lets credential harvesting pass endpoint controls and payment fraud stop at the user", () => {
    const credential = simulate(selectEmails("email_credential"), untrainedConfig());
    const payment = simulate(selectEmails("email_payment"), untrainedConfig());
    expect(formatPct(credential.aggregate.closed_form)).toBe("27.30%");
    expect(formatPct(payment.aggregate.closed_form)).toBe("45.50%");
    const paymentLayers = layerProbabilities(selectEmails("email_payment")[0]!, untrainedConfig());
    expect(paymentLayers.find((layer) => layer.layer === "antivirus")?.applicable).toBe(false);
    expect(paymentLayers.find((layer) => layer.layer === "segmentation")?.applicable).toBe(false);
  });

  it("halves antivirus for a password-protected archive and honors executable overrides", () => {
    const archive = selectEmails("email_illustrative")[0]!;
    const protectedArchive = {
      ...archive,
      features: { ...archive.features, "attachment.password_protected": true },
    };
    const probabilities = layerProbabilities(protectedArchive, untrainedConfig());
    expect(probabilities.find((layer) => layer.layer === "antivirus")?.p_stop).toBeCloseTo(0.275);
    const executable = layerProbabilities(selectEmails("email_executable")[0]!, untrainedConfig());
    expect(executable.find((layer) => layer.layer === "application_control")?.p_stop).toBeCloseTo(0.95);
    expect(executable.find((layer) => layer.layer === "email_filter")?.p_stop).toBeGreaterThan(0.9);
  });
});

describe("recommendations", () => {
  it("ranks training above antivirus on a credential-heavy set", () => {
    const emails = selectEmails("all").filter((email) => email.attack_vector !== "malware_attachment");
    const result = recommend(emails, untrainedConfig());
    expect(result.recommendations[0]?.id).toBe("raise_training");
    const antivirus = result.recommendations.find((item) => item.id === "antivirus_detection");
    const training = result.recommendations[0];
    expect(training).toBeDefined();
    if (antivirus && training) {
      expect(antivirus.absolute_reduction).toBeLessThan(training.absolute_reduction);
    }
    const credentialOnly = recommend(selectEmails("email_credential"), untrainedConfig());
    expect(credentialOnly.recommendations.some((item) => item.id === "antivirus_detection")).toBe(false);
    const antivirusRow = credentialOnly.sensitivity.find((row) => row.layer === "antivirus");
    expect(antivirusRow?.decreased).toBeCloseTo(antivirusRow?.baseline ?? -1);
    expect(antivirusRow?.increased).toBeCloseTo(antivirusRow?.baseline ?? -1);
  });
});

describe("particles and import", () => {
  it("samples particles in proportion to stop counts", () => {
    const particles = sampleParticles([3500, 1950, 1137, 1877, 615], 921, 300);
    expect(particles).toHaveLength(300);
    const passed = particles.filter((particle) => particle.stopAt === 5).length;
    expect(passed).toBeGreaterThan(20);
    expect(passed).toBeLessThan(40);
  });

  it("imports the canonical untrained config", () => {
    const parsed = parseConfigYaml(CANONICAL_UNTRAINED_YAML);
    expect(parsed.errors).toEqual([]);
    expect(parsed.config?.user_training.level).toBe("none");
    expect(parsed.config?.email_filter.base_catch_rate).toBe(0.35);
    expect(parsed.config?.email_filter.rules).toHaveLength(2);
  });

  it("rejects an out-of-range catch rate with a field name", () => {
    const parsed = parseConfigYaml("name: Bad\nemail_filter:\n  base_catch_rate: 150\n  rules: []\nuser_training:\n  level: none\napplication_control:\n  effectiveness: 0.25\nantivirus:\n  detection_rate: 0.55\nsegmentation:\n  containment_rate: 0.4\n");
    expect(parsed.config).toBeNull();
    expect(parsed.errors.some((error) => error.field === "email_filter.base_catch_rate")).toBe(true);
  });
});
