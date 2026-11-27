import { expect, test } from "@playwright/test";

import { BUDGETS } from "./contract";

test("triage becomes ready in under 2 seconds", async ({ page }) => {
  const started = Date.now();
  await page.goto("/triage");
  await expect(page.getByTestId("screen-ready")).toBeVisible();
  expect(Date.now() - started).toBeLessThan(BUDGETS.pageLoadMs);
});

test("a 10,000-run simulation answers within 300ms", async ({ request }) => {
  const started = Date.now();
  const response = await request.post("/api/v1/simulations", {
    data: { dataset_id: "official", config_id: "untrained", runs: 10_000, seed: 42, persist: true },
  });
  const elapsed = Date.now() - started;
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.runs).toBe(10_000);
  expect(body.seed).toBe(42);
  expect(body.aggregate.pass_rate).toBeGreaterThan(0);
  expect(elapsed).toBeLessThan(BUDGETS.simulateMs);
});

test("a what-if simulation answers within 250ms", async ({ request }) => {
  const started = Date.now();
  const response = await request.post("/api/v1/simulations", {
    data: { dataset_id: "official", config_id: "trained", runs: 10_000, seed: 42, persist: false },
  });
  const elapsed = Date.now() - started;
  expect(response.ok()).toBeTruthy();
  expect(elapsed).toBeLessThan(BUDGETS.whatIfMs);
});

test("analyzing 20 emails answers within 1 second", async ({ request }) => {
  const started = Date.now();
  const response = await request.post("/api/v1/datasets", {
    data: { name: "official", email_count: 20 },
  });
  const elapsed = Date.now() - started;
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.email_count).toBe(20);
  expect(elapsed).toBeLessThan(BUDGETS.analyzeMs);
});
