import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  DATASET_ID,
  ENGINE_VERSION,
  SEED,
  simulationPayload,
  validationRows,
  WEIGHTS_HASH,
} from "./fixture.mjs";
import { render } from "./pages.mjs";

const port = Number(process.env.HARNESS_PORT ?? 4173);
const styles = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "styles.css"), "utf8");

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  if (request.method === "POST") await readBody(request);

  if (url.pathname === "/health") return send(response, 200, "ok", "text/plain");
  if (url.pathname === "/favicon.ico") return send(response, 204, "", "image/x-icon");
  if (url.pathname === "/styles.css") return send(response, 200, styles, "text/css; charset=utf-8");

  if (request.method === "POST" && url.pathname === "/api/v1/demo/reset") {
    return sendJson(response, {
      dataset_id: DATASET_ID,
      email_count: 20,
      seed: SEED,
      config_a: "untrained",
      config_b: "trained",
    });
  }
  if (request.method === "POST" && url.pathname === "/api/v1/simulations") {
    return sendJson(response, simulationPayload());
  }
  if (request.method === "POST" && url.pathname === "/api/v1/datasets") {
    return sendJson(response, { dataset_id: DATASET_ID, email_count: 20 });
  }
  if (url.pathname === `/api/v1/datasets/${DATASET_ID}/report.json`) {
    return sendJson(response, reportJson());
  }
  if (url.pathname === `/api/v1/datasets/${DATASET_ID}/report.csv`) {
    return send(response, 200, reportCsv(), "text/csv; charset=utf-8");
  }

  const html = render(url.pathname, url.searchParams.get("state") ?? "ready");
  if (!html) return send(response, 404, "not found", "text/plain");
  return send(response, 200, html, "text/html; charset=utf-8");
});

server.listen(port, "127.0.0.1");

function reportJson() {
  const rows = validationRows();
  const correct = rows.filter((row) => row.correct).length;
  return {
    dataset_id: DATASET_ID,
    correct,
    total: rows.length,
    accuracy: correct / rows.length,
    engine_version: ENGINE_VERSION,
    weights_hash: WEIGHTS_HASH,
    seed: SEED,
    figures: "illustrative",
    rows,
  };
}

function reportCsv() {
  const lines = ["filename,actual,predicted,correct,risk"];
  for (const row of validationRows()) {
    lines.push(`${row.filename},${row.actual},${row.predicted},${row.correct},${row.risk}`);
  }
  return `${lines.join("\n")}\n`;
}

function readBody(request) {
  return new Promise((resolve, reject) => {
    request.on("data", () => {});
    request.on("end", resolve);
    request.on("error", reject);
  });
}

function send(response, status, body, type) {
  response.writeHead(status, { "content-type": type, "cache-control": "no-store" });
  response.end(body);
}

function sendJson(response, body) {
  send(response, 200, JSON.stringify(body), "application/json; charset=utf-8");
}
