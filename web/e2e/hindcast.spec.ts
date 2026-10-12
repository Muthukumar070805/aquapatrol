import { test, expect } from "@playwright/test";
import { mockAllRoutes, HINDCAST_RESPONSE } from "./helpers";

/**
 * Hindcast page – e2e coverage.
 *
 * Scenarios:
 *  1. Renders heading "Backward Drift Simulation"
 *  2. All observed slick parameter inputs are present with defaults
 *  3. Simulation configuration inputs are present
 *  4. Historical forcing vector inputs are present
 *  5. "Run Hindcast Simulation" button is visible and enabled
 *  6. Happy path: submit -> shows origin confidence, drift distance, coordinates
 *  7. Happy path: "Investigate Vessels" link appears after results
 *  8. Happy path: particle trajectory count is displayed
 *  9. API error shows an error box
 */
test.describe("Hindcast page", () => {
  test("renders Backward Drift Simulation heading", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/hindcast");

    await expect(
      page.getByRole("heading", { name: /Backward Drift Simulation/i }),
    ).toBeVisible();
  });

  test("observed slick parameter inputs have default values", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/hindcast");

    await expect(page.getByLabel("Latitude (°N)")).toHaveValue("-20.44");
    await expect(page.getByLabel("Longitude (°E)")).toHaveValue("57.72");
    await expect(page.getByLabel(/Detection Time/i)).toHaveValue("2020-07-25T04:35:00Z");
    await expect(page.getByLabel(/Slick Area/i)).toHaveValue("3.1");
  });

  test("simulation configuration inputs are visible", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/hindcast");

    await expect(page.getByLabel("Duration (hours)")).toBeVisible();
    await expect(page.getByLabel("Particles")).toBeVisible();
  });

  test("historical forcing vector inputs are visible", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/hindcast");

    await expect(page.getByLabel(/Current U/i)).toBeVisible();
    await expect(page.getByLabel(/Current V/i)).toBeVisible();
    await expect(page.getByLabel(/Wind U/i)).toBeVisible();
    await expect(page.getByLabel(/Wind V/i)).toBeVisible();
  });

  test("Run Hindcast Simulation button is visible and enabled", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/hindcast");

    await expect(page.getByRole("button", { name: /Run Hindcast Simulation/i })).toBeEnabled();
  });

  test("happy path: shows origin confidence and coordinates", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/hindcast");

    await page.getByRole("button", { name: /Run Hindcast Simulation/i }).click();

    // Origin confidence = 87%
    const confidence = HINDCAST_RESPONSE.json.origin_probability;
    await expect(page.getByText(`${Math.round(confidence * 100)}%`)).toBeVisible();

    // Probable spill origin coordinates
    const { latitude, longitude } = HINDCAST_RESPONSE.json.probable_spill_origin;
    await expect(page.getByText(new RegExp(latitude.toFixed(4)))).toBeVisible();
    await expect(page.getByText(new RegExp(longitude.toFixed(4)))).toBeVisible();
  });

  test("results show estimated spill time", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/hindcast");

    await page.getByRole("button", { name: /Run Hindcast Simulation/i }).click();

    await expect(
      page.getByText(HINDCAST_RESPONSE.json.estimated_spill_time),
    ).toBeVisible();
  });

  test("results show particle trajectory count", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/hindcast");

    await page.getByRole("button", { name: /Run Hindcast Simulation/i }).click();

    const count = HINDCAST_RESPONSE.json.backward_trajectories.length;
    await expect(page.getByText(String(count))).toBeVisible();
  });

  test("Investigate Vessels link appears after simulation", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/hindcast");

    await page.getByRole("button", { name: /Run Hindcast Simulation/i }).click();

    const link = page.getByRole("link", { name: /Investigate Vessels/i });
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("href", expect.stringContaining("origin_lat="));
  });

  test("API error shows error box", async ({ page }) => {
    await mockAllRoutes(page);
    await page.route("**/hindcast", (r) =>
      r.fulfill({ status: 500, json: { detail: "Simulation failed." } }),
    );
    await page.goto("/hindcast");

    await page.getByRole("button", { name: /Run Hindcast Simulation/i }).click();

    await expect(page.locator(".error-box")).toBeVisible();
  });
});
