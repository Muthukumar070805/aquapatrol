import { test, expect } from "@playwright/test";
import { mockAllRoutes } from "./helpers";

/**
 * Overview page – e2e coverage.
 *
 * Scenarios:
 *  1. Renders h1 "Overview"
 *  2. Navigation bar is present with all five links
 *  3. Pipeline diagram section is rendered
 *  4. "How detection works" section is rendered
 *  5. Navigation to Quick Detect via nav link
 *  6. Navigation to Scene Monitor via nav link
 *  7. Navigation to Hindcast via nav link
 *  8. Navigation to Vessels via nav link
 *  9. Brand text is visible in the topbar
 */
test.describe("Overview page", () => {
  test("renders the Overview heading", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  });

  test("primary nav has all five links", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/");

    const nav = page.getByRole("navigation", { name: "Primary" });
    await expect(nav).toBeVisible();
    await expect(nav.getByRole("link", { name: "Overview" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Quick Detect" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Scene Monitor" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Hindcast" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Vessels" })).toBeVisible();
  });

  test("brand name is displayed in the topbar", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/");

    await expect(page.locator(".brand")).toContainText("Satellite Oil Spill Forensics");
  });

  test("detection pipeline section is visible", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Detection pipeline" })).toBeVisible();
  });

  test('"How detection works" section is visible', async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "How detection works" })).toBeVisible();
    await expect(page.getByText(/YOLO/i).first()).toBeVisible();
  });

  test("clicking Quick Detect nav link navigates to /detect", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/");

    await page.getByRole("link", { name: "Quick Detect" }).click();

    await expect(page).toHaveURL(/\/detect/);
    await expect(page.getByRole("heading", { name: "Quick Detect" })).toBeVisible();
  });

  test("clicking Scene Monitor nav link navigates to /scenes", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/");

    await page.getByRole("link", { name: "Scene Monitor" }).click();

    await expect(page).toHaveURL(/\/scenes/);
    await expect(page.getByRole("heading", { name: "Scene Monitor" })).toBeVisible();
  });

  test("clicking Hindcast nav link navigates to /hindcast", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/");

    await page.getByRole("link", { name: "Hindcast" }).click();

    await expect(page).toHaveURL(/\/hindcast/);
    await expect(
      page.getByRole("heading", { name: /Backward Drift Simulation/i }),
    ).toBeVisible();
  });

  test("clicking Vessels nav link navigates to /vessels", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/");

    await page.getByRole("link", { name: "Vessels" }).click();

    await expect(page).toHaveURL(/\/vessels/);
  });
});
