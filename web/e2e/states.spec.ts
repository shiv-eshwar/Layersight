import { expect, test } from "@playwright/test";

import { DEMO_ROUTES, SHOWCASE_PATH } from "./contract";
import { trackConsole } from "./console";

const paths = [...DEMO_ROUTES.map((route) => route.path), SHOWCASE_PATH];

test("every screen has loading, empty, and error states", async ({ page }) => {
  const errors = trackConsole(page);

  for (const path of paths) {
    await page.goto(`${path}?state=loading`);
    await expect(page.getByTestId("screen-loading")).toBeVisible();
    await expect(page.getByTestId("screen-loading")).toContainText(/loading/i);

    await page.goto(`${path}?state=empty`);
    await expect(page.getByTestId("screen-empty")).toBeVisible();
    await expect(page.getByTestId("screen-empty")).toContainText(/upload/i);

    await page.goto(`${path}?state=error`);
    await expect(page.getByTestId("screen-error")).toBeVisible();
    await expect(page.getByTestId("retry")).toBeVisible();
  }

  expect(errors).toEqual([]);
});

test("ready screens name themselves and keep the shell", async ({ page }) => {
  for (const route of DEMO_ROUTES) {
    await page.goto(route.path);
    await expect(page.getByTestId("screen-ready")).toBeVisible();
    await expect(page.getByTestId("screen-title")).toHaveText(route.title);
    await expect(page.getByTestId("nav-triage")).toBeVisible();
    await expect(page.getByTestId("dataset-select")).toBeVisible();
    await expect(page.getByTestId("config-pair")).toBeVisible();
  }
});
