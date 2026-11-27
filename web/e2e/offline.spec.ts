import { expect, test } from "@playwright/test";

import { SHOWCASE_PATH } from "./contract";

test("demo path does not request anything off the machine", async ({ page }) => {
  const external: string[] = [];
  await page.route("**/*", (route) => {
    const url = new URL(route.request().url());
    const local = url.hostname === "127.0.0.1" || url.hostname === "localhost";
    if (!local) {
      external.push(url.href);
      return route.abort("internetdisconnected");
    }
    return route.continue();
  });

  await page.goto("/triage");
  await expect(page.getByTestId("triage-row").first()).toBeVisible();
  await page.goto(SHOWCASE_PATH);
  await expect(page.getByTestId("advice")).toBeVisible();
  await page.goto("/simulator");
  await expect(page.getByTestId("funnel")).toBeVisible();
  await page.goto("/compare");
  await expect(page.getByTestId("comparison-narrative")).toBeVisible();
  await page.goto("/reports");
  await expect(page.getByTestId("confusion-matrix")).toBeVisible();

  expect(external).toEqual([]);
});
