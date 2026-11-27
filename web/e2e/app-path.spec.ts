import { expect, test } from "@playwright/test";

import { CLOSING_LINE } from "./contract";

const live = process.env.E2E_TARGET === "app";

test("live app walks triage, one investigation, simulation, comparison, and reports", async ({
  page,
  request,
}) => {
  test.skip(!live, "Runs against the Next.js app and the API, not the illustrative harness.");

  const reset = await request.post("/api/v1/demo/reset");
  expect(reset.ok()).toBeTruthy();
  const datasetId = (await reset.json()).id as string;
  expect(datasetId).toBeTruthy();
  const query = `?dataset=${datasetId}`;

  await page.goto(`/triage${query}`);
  await expect(page.getByTestId("triage-dropzone")).toBeVisible();
  await expect(page.getByTestId("triage-tab-phishing")).toContainText("12");
  const rows = page.getByTestId("triage-row");
  await expect(rows).toHaveCount(20);
  const risks = await rows.evaluateAll((items) =>
    items.map((item) => Number(item.getAttribute("data-risk"))),
  );
  for (let index = 1; index < risks.length; index += 1) {
    expect(risks[index - 1]).toBeGreaterThanOrEqual(risks[index] ?? 0);
  }

  await rows.first().click();
  await expect(page).toHaveURL(/\/triage\/.+/);
  await expect(page.getByTestId("verdict")).toContainText(/phishing/i);
  await expect(page.getByTestId("risk-score")).toBeVisible();
  await expect(page.getByTestId("header-reply-to")).toHaveAttribute("data-mismatch", "true");
  await expect(page.getByTestId("auth-dmarc")).toHaveAttribute("data-status", "fail");
  await expect(page.locator('[data-testid="evidence-item"][data-rule="L02"]')).toBeVisible();
  await expect(page.locator('[data-testid="evidence-item"][data-rule="L01"]')).toBeVisible();
  await expect(page.getByTestId("link-row").first()).toHaveAttribute("data-deceptive", "true");
  await expect(page.getByTestId("advice")).not.toBeEmpty();

  await page.goto(`/simulator${query}`);
  await expect(page.getByTestId("sim-runs")).toHaveAttribute("data-value", "10000");
  await expect(page.getByTestId("sim-seed")).toHaveAttribute("data-value", "42");
  await expect(page.getByTestId("funnel")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("closed-form")).toBeVisible();
  await expect(page.getByTestId("modeled-estimate")).toContainText(/modeled/i);
  const closedForm = Number(await page.getByTestId("closed-form").getAttribute("data-value"));
  expect(closedForm).toBeGreaterThan(0.09);
  expect(closedForm).toBeLessThan(0.1);

  await page.goto(`/compare${query}`);
  await expect(page.getByTestId("comparison-narrative")).toBeVisible({ timeout: 20_000 });
  const before = Number(await page.getByTestId("result-card-a").getAttribute("data-pass-rate"));
  const after = Number(await page.getByTestId("result-card-b").getAttribute("data-pass-rate"));
  const relative = Number(await page.getByTestId("relative-reduction").getAttribute("data-value"));
  expect(Math.abs(relative - (before - after) / before)).toBeLessThan(0.001);
  const sentence = await page.getByTestId("comparison-narrative").innerText();
  expect(sentence.toLowerCase()).toContain("modeled");
  expect(sentence).toContain(`${(before * 100).toFixed(2)}%`);
  expect(sentence).toContain(`${(after * 100).toFixed(2)}%`);
  await expect(page.getByTestId("config-diff")).toBeVisible();

  await page.goto(`/reports${query}`);
  await expect(page.getByTestId("report-total")).toHaveAttribute("data-value", "20", { timeout: 20_000 });
  const correct = Number(await page.getByTestId("report-correct").getAttribute("data-value"));
  expect(correct).toBeGreaterThanOrEqual(18);
  await expect(page.getByTestId("confusion-matrix")).toBeVisible();
  await expect(page.getByTestId("per-email-table")).toBeVisible();
  await expect(page.getByTestId("reproducibility")).toHaveAttribute("data-seed", "42");
  const report = await request.get(`/api/v1/datasets/${datasetId}/report.json`);
  expect(report.ok()).toBeTruthy();

  await page.getByTestId("show-title-card").click();
  await expect(page.getByTestId("title-card")).toContainText(CLOSING_LINE);
});
