import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { evaluateRehearsals, REHEARSAL_LIMIT_SECONDS } from "./rehearse-lib.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const reportDir = join(here, "..", "..", "demo", "rehearsals");
const runs = [];

for (let index = 1; index <= 3; index += 1) {
  const started = Date.now();
  const code = await runOnce();
  const seconds = Number(((Date.now() - started) / 1000).toFixed(3));
  const ok = code === 0;
  runs.push({ index, ok, seconds });
  console.log(`rehearsal ${index}: ${ok ? "clean" : "failed"} in ${seconds}s`);
}

const result = evaluateRehearsals(runs);
const report = {
  limit_seconds: REHEARSAL_LIMIT_SECONDS,
  pass: result.pass,
  consecutive: result.consecutive,
  runs,
  at: new Date().toISOString(),
};

mkdirSync(reportDir, { recursive: true });
writeFileSync(join(reportDir, "latest.json"), `${JSON.stringify(report, null, 2)}\n`);
console.log(
  result.pass
    ? `passed with ${result.consecutive} consecutive clean rehearsals under ${REHEARSAL_LIMIT_SECONDS}s`
    : "failed: need two consecutive clean rehearsals under 3:00",
);
process.exit(result.pass ? 0 : 1);

function runOnce() {
  return new Promise((resolve) => {
    const child = spawn("pnpm", ["exec", "playwright", "test", "demo-path.spec.ts"], {
      cwd: here,
      stdio: "inherit",
      env: process.env,
    });
    child.on("exit", (code) => resolve(code ?? 1));
  });
}
