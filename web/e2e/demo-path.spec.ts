import { expect, test } from "@playwright/test";

import { CLOSING_LINE, BUDGETS, SHOWCASE_PATH } from "./contract";
import { trackConsole } from "./console";

test("judge demo path stays inside three minutes with no console errors", async ({ page, request }) => {
  const errors = trackConsole(page);
  const started = Date.now();

  const reset = await request.post("/api/v1/demo/reset");
  expect(reset.ok()).toBeTruthy();
  const resetBody = await reset.json();
  expect(resetBody.dataset_id).toBe("official");
  expect(resetBody.seed).toBe(42);

  await page.goto("/triage");
  await expect(page.getByTestId("screen-ready")).toBeVisible();
  await expect(page.getByTestId("triage-dropzone")).toBeVisible();
  await expect(page.getByTestId("triage-tab-phishing")).toContainText(/\d+/);
  await page.getByTestId("sort-risk").click();

  const risks = await page.getByTestId("triage-row").evaluateAll((rows) =>
    rows.map((row) => Number(row.getAttribute("data-risk"))),
  );
  expect(risks.length).toBeGreaterThanOrEqual(20);
  for (let index = 1; index < risks.length; index += 1) {
    expect(risks[index - 1]).toBeGreaterThanOrEqual(risks[index]);
  }

  await page.getByTestId("triage-row").first().click();
  await expect(page).toHaveURL(new RegExp(`${SHOWCASE_PATH}$`));
  await expect(page.getByTestId("verdict")).toContainText(/phishing/i);
  await expect(page.getByTestId("risk-score")).toBeVisible();
  await expect(page.getByTestId("header-reply-to")).toHaveAttribute("data-mismatch", "true");
  await expect(page.getByTestId("auth-dmarc")).toHaveAttribute("data-status", "fail");
  await expect(page.locator('[data-testid="evidence-item"][data-rule="L02"]')).toBeVisible();
  await expect(page.locator('[data-testid="evidence-item"][data-rule="L01"]')).toBeVisible();
  await expect(page.getByTestId("link-row")).toHaveAttribute("data-deceptive", "true");
  await expect(page.getByTestId("advice")).not.toBeEmpty();

  await page.goto("/simulator");
  await expect(page.getByTestId("sim-runs")).toHaveAttribute("data-value", "10000");
  await expect(page.getByTestId("sim-seed")).toHaveAttribute("data-value", "42");
  await expect(page.getByTestId("funnel")).toBeVisible();
  await expect(page.getByTestId("pass-rate")).toBeVisible();
  await expect(page.getByTestId("closed-form")).toBeVisible();
  await expect(page.getByTestId("ci95")).toBeVisible();
  await expect(page.getByTestId("modeled-estimate").first()).toBeVisible();
  await page.getByTestId("assumptions-button").click();
  await expect(page.getByTestId("assumptions-panel")).toContainText(/independent/i);

  await page.goto("/compare");
  const before = Number(await page.getByTestId("result-card-a").getAttribute("data-pass-rate"));
  const after = Number(await page.getByTestId("result-card-b").getAttribute("data-pass-rate"));
  const relative = Number(await page.getByTestId("relative-reduction").getAttribute("data-value"));
  expect(Math.abs(relative - (before - after) / before)).toBeLessThan(0.001);
  const sentence = await page.getByTestId("comparison-narrative").innerText();
  expect(sentence.toLowerCase()).toContain("modeled");
  expect(sentence).toContain(formatPct(before));
  expect(sentence).toContain(formatPct(after));
  await expect(page.getByTestId("config-diff")).toBeVisible();
  await expect(page.getByTestId("top-recommendation")).toBeVisible();

  await page.goto("/reports");
  const correct = Number(await page.getByTestId("report-correct").getAttribute("data-value"));
  const total = Number(await page.getByTestId("report-total").getAttribute("data-value"));
  const accuracy = Number(await page.getByTestId("accuracy").getAttribute("data-value"));
  expect(total).toBe(20);
  expect(correct).toBeGreaterThanOrEqual(18);
  expect(Math.abs(accuracy - correct / total)).toBeLessThan(0.001);
  await expect(page.getByTestId("confusion-matrix")).toBeVisible();
  await expect(page.getByTestId("per-email-table")).toBeVisible();
  await expect(page.getByTestId("reproducibility")).toHaveAttribute("data-seed", "42");
  await expect(page.getByTestId("reproducibility")).toHaveAttribute("data-engine-version", /.+/);
  await expect(page.getByTestId("reproducibility")).toHaveAttribute("data-weights-hash", /.+/);
  const report = await request.get("/api/v1/datasets/official/report.json");
  expect(report.ok()).toBeTruthy();
  const csv = await request.get("/api/v1/datasets/official/report.csv");
  expect(csv.ok()).toBeTruthy();

  await page.getByTestId("show-title-card").click();
  await expect(page.getByTestId("title-card")).toContainText(CLOSING_LINE);

  expect(Date.now() - started).toBeLessThan(BUDGETS.rehearsalMs);
  expect(errors).toEqual([]);
});

function formatPct(rate: number): string {
  return `${(rate * 100).toFixed(2)}%`;
}
