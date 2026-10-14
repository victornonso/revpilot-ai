import { test, expect } from "@playwright/test";
const routes = [
  "overview",
  "pipeline",
  "forecasting",
  "customers",
  "analyst",
  "automations",
  "recovery",
  "reports",
  "operations",
];
for (const route of routes) {
  test(`${route} / actual SQL-backed responsive screen`, async ({
    page,
  }, info) => {
    await page.goto("/" + route);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByLabel("Loading workspace")).toBeHidden();
    await expect(
      page.getByText("We couldn’t load this workspace."),
    ).toHaveCount(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    await page.locator(".skeleton").first().waitFor({ state: "hidden" });
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({
      path: info.outputPath(`${route}.png`),
      fullPage: true,
    });
  });
}
test("filter, drill-down and exact metric context", async ({ page }) => {
  await page.goto("/overview");
  await expect(page.getByLabel("Loading workspace")).toBeHidden();
  await page.getByLabel("Customer segment").selectOption("Enterprise");
  await expect(page).toHaveURL(/segment=Enterprise/);
  await expect(page.getByLabel("Loading workspace")).toBeHidden();
  await page.locator(".metric").first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Definition", exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
});
test("pipeline history and pagination", async ({ page }) => {
  await page.goto("/pipeline");
  await expect(page.getByLabel("Loading workspace")).toBeHidden();
  await page
    .getByRole("button", { name: /^Inspect / })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "history", exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Next page", exact: true }).click();
  await expect(page).toHaveURL(/page=2/);
});
test("rule simulation changes no approvals", async ({ page }) => {
  await page.goto("/automations");
  await expect(page.getByLabel("Loading workspace")).toBeHidden();
  await page
    .getByRole("button", { name: "Run simulation", exact: true })
    .click();
  await expect(page.getByRole("heading", { name: /Simulation/ })).toBeVisible();
});
test("invalid reporting period offers a recoverable error", async ({
  page,
}) => {
  await page.goto("/overview?start=2026-10-14&end=2026-01-01");
  await expect(page.locator(".error-state")).toContainText(
    "Choose an ordered reporting period",
  );
  await expect(
    page.getByRole("button", { name: "Retry connection" }),
  ).toBeVisible();
});
