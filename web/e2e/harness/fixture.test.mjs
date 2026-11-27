import assert from "node:assert/strict";
import test from "node:test";

import {
  comparisonNarrative,
  formatPct,
  relativeReduction,
  SHOWCASE,
} from "./fixture.mjs";

test("illustrative pass-through formats to the published two decimals", () => {
  assert.equal(formatPct(0.0921), "9.21%");
  assert.equal(formatPct(0.0329), "3.29%");
});

test("trained versus untrained reduction matches the narrative", () => {
  const reduction = relativeReduction(SHOWCASE.passRateUntrained, SHOWCASE.passRateTrained);
  assert.ok(Math.abs(reduction - 0.6427796) < 0.0001);
  const sentence = comparisonNarrative(SHOWCASE.passRateUntrained, SHOWCASE.passRateTrained);
  assert.match(sentence, /modeled/);
  assert.match(sentence, /9\.21%/);
  assert.match(sentence, /3\.29%/);
  assert.match(sentence, /64\.3%/);
});

test("showcase email carries the spoken demo evidence", () => {
  assert.equal(SHOWCASE.email.auth.dmarc, "fail");
  assert.equal(SHOWCASE.email.replyToMismatch, true);
  assert.ok(SHOWCASE.email.evidence.some((item) => item.rule_id === "L02"));
  assert.ok(SHOWCASE.email.evidence.some((item) => item.rule_id === "L01"));
  assert.ok(SHOWCASE.email.advice.length >= 1);
  assert.equal(SHOWCASE.validation.correct, 18);
  assert.equal(SHOWCASE.validation.total, 20);
});
