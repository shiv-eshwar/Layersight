import assert from "node:assert/strict";
import test from "node:test";

import { evaluateRehearsals, REHEARSAL_LIMIT_SECONDS } from "./rehearse-lib.mjs";

test("two consecutive clean rehearsals under 3:00 pass", () => {
  const result = evaluateRehearsals([
    { ok: true, seconds: 42 },
    { ok: true, seconds: 40 },
    { ok: true, seconds: 200 },
  ]);
  assert.equal(result.pass, true);
  assert.equal(result.consecutive, 2);
  assert.equal(REHEARSAL_LIMIT_SECONDS, 180);
});

test("a failure between runs breaks the consecutive streak", () => {
  const result = evaluateRehearsals([
    { ok: true, seconds: 20 },
    { ok: false, seconds: 10 },
    { ok: true, seconds: 20 },
  ]);
  assert.equal(result.pass, false);
  assert.equal(result.consecutive, 1);
});

test("a run at the 3:00 limit is not under the limit", () => {
  const result = evaluateRehearsals([
    { ok: true, seconds: 180 },
    { ok: true, seconds: 10 },
  ]);
  assert.equal(result.pass, false);
});
