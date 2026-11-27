import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const blockedHosts = [
  "fonts.googleapis.com",
  "fonts.gstatic.com",
  "cdn.jsdelivr.net",
  "unpkg.com",
  "cdnjs.cloudflare.com",
  "www.google-analytics.com",
  "esm.sh",
];

const skip = new Set([
  "node_modules",
  "test-results",
  "playwright-report",
  "blob-report",
  ".next",
  "out",
  "coverage",
]);

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const web = join(root, "web");
const hits = [];
walk(web, hits);

if (hits.length > 0) {
  console.error("demo loads a host that Wi-Fi off would block:");
  for (const hit of hits) console.error(`  ${hit}`);
  process.exit(1);
}

console.log("offline scan clean: web assets stay on the machine");

function walk(dir, found) {
  let entries = [];
  try {
    entries = readdirSync(dir);
  } catch {
    return;
  }
  for (const name of entries) {
    if (skip.has(name)) continue;
    const path = join(dir, name);
    const info = statSync(path);
    if (info.isDirectory()) {
      walk(path, found);
      continue;
    }
    if (!/\.(tsx?|jsx?|mjs|cjs|css|html)$/.test(name)) continue;
    const text = readFileSync(path, "utf8");
    for (const host of blockedHosts) {
      if (text.includes(host)) found.push(`${path}: ${host}`);
    }
  }
}
