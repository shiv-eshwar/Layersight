import { spawn } from "node:child_process";
import { copyFileSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const destDir = join(here, "..", "..", "demo", "backup");
const dest = join(destDir, "demo-fallback.webm");

const code = await new Promise((resolve) => {
  const child = spawn("pnpm", ["exec", "playwright", "test", "demo-path.spec.ts"], {
    cwd: here,
    stdio: "inherit",
    env: { ...process.env, DEMO_VIDEO: "1" },
  });
  child.on("exit", (status) => resolve(status ?? 1));
});

if (code !== 0) {
  console.error("demo path failed; no backup video written");
  process.exit(code);
}

const video = newestWebm(join(here, "test-results"));
if (!video) {
  console.error("playwright did not write a video");
  process.exit(1);
}

mkdirSync(destDir, { recursive: true });
copyFileSync(video, dest);
const bytes = statSync(dest).size;
console.log(`${dest} (${bytes} bytes)`);

function newestWebm(dir) {
  let best = null;
  for (const name of readdirSync(dir, { recursive: true })) {
    if (!String(name).endsWith(".webm")) continue;
    const path = join(dir, String(name));
    const stamp = statSync(path).mtimeMs;
    if (!best || stamp > best.stamp) best = { path, stamp };
  }
  return best?.path ?? null;
}
