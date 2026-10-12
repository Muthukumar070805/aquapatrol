import { test, expect } from "@playwright/test";
import { mockAllRoutes, VESSEL_1, VESSEL_2, CORRELATION_RESPONSE } from "./helpers";

/**
 * Vessel Intelligence page – e2e coverage.
 *
 * Scenarios:
 *  1. Renders h1 "Vessel Intelligence"
 *  2. Origin lat/lon inputs have default values
 *  3. Both mock vessels are listed by name
 *  4. Dark vessel badge is shown for the dark vessel
 *  5. Selecting a vessel shows its details panel (name, MMSI, IMO, type, speed)
 *  6. "Correlate" button appears after vessel selection
 *  7. Running correlation shows correlation score, distance and disclaimer
 *  8. "Create Case" button appears after correlation
 *  9. Creating a case navigates to the case detail page
 * 10. Origin lat/lon pre-filled from query string (Hindcast link-through)
 */
test.describe("Vessel Intelligence page", () => {
  test("renders Vessel Intelligence heading", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/vessels");

    await expect(page.getByRole("heading", { name: "Vessel Intelligence" })).toBeVisible();
  });

  test("origin lat/lon inputs have default values", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/vessels");

    await expect(page.getByLabel("Origin lat")).toHaveValue("-20.44");
    await expect(page.getByLabel("Origin lon")).toHaveValue("57.72");
  });

  test("both mock vessels are listed", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/vessels");

    await expect(page.getByText(VESSEL_1.name)).toBeVisible();
    await expect(page.getByText(VESSEL_2.name)).toBeVisible();
  });

  test("dark vessel badge shown for dark vessel", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/vessels");

    // The dark vessel button should contain a "dark" badge
    const v2Btn = page.getByRole("button", { name: new RegExp(VESSEL_2.name) });
    await expect(v2Btn).toBeVisible();
    await expect(v2Btn.getByText("dark")).toBeVisible();
  });

  test("selecting a vessel shows detail panel with MMSI and IMO", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/vessels");

    await page.getByRole("button", { name: new RegExp(VESSEL_1.name) }).click();

    await expect(page.getByText(VESSEL_1.mmsi)).toBeVisible();
    await expect(page.getByText(VESSEL_1.imo)).toBeVisible();
    await expect(page.getByText(VESSEL_1.vessel_type)).toBeVisible();
  });

  test("Correlate button is visible after vessel selection", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/vessels");

    await page.getByRole("button", { name: new RegExp(VESSEL_1.name) }).click();

    await expect(page.getByRole("button", { name: /Correlate/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Correlate/i })).toBeEnabled();
  });

  test("running correlation shows score and distance", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/vessels");

    await page.getByRole("button", { name: new RegExp(VESSEL_1.name) }).click();
    await page.getByRole("button", { name: /Correlate/i }).click();

    await expect(page.getByText(/Investigative correlation/i)).toBeVisible();
    await expect(
      page.getByText(CORRELATION_RESPONSE.distance_km.toFixed(2)),
    ).toBeVisible();
    await expect(
      page.getByText(CORRELATION_RESPONSE.correlation_score.toFixed(1)),
    ).toBeVisible();
  });

  test("Create Case button appears after correlation", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/vessels");

    await page.getByRole("button", { name: new RegExp(VESSEL_1.name) }).click();
    await page.getByRole("button", { name: /Correlate/i }).click();

    await expect(page.getByRole("button", { name: /Create Case/i })).toBeVisible();
  });

  test("creating a case navigates to case detail page", async ({ page }) => {
    await mockAllRoutes(page);
    // Override /cases POST to succeed, then provide case-detail mock
    await page.route("**/cases", (r) => {
      if (r.request().method() === "POST") {
        return r.fulfill({ json: { id: "case-uuid-001", case_number: "CASE-2024-001", status: "open", spill_id: "SPILL_001", candidate_confidence: 0.82, origin_lat: -20.48, origin_lon: 57.68, origin_confidence: 0.87, risk_level: "HIGH", selected_vessel_id: "vessel-001", summary: null, created_at: "2024-01-15T10:00:00Z" } });
      }
      return r.fulfill({ json: [] });
    });
    await page.goto("/vessels");

    await page.getByRole("button", { name: new RegExp(VESSEL_1.name) }).click();
    await page.getByRole("button", { name: /Correlate/i }).click();
    await page.getByRole("button", { name: /Create Case/i }).click();

    await expect(page).toHaveURL(/\/cases\/case-uuid-001/);
  });

  test("origin coords pre-filled from Hindcast query string", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/vessels?origin_lat=-20.4800&origin_lon=57.6800");

    await expect(page.getByLabel("Origin lat")).toHaveValue("-20.4800");
    await expect(page.getByLabel("Origin lon")).toHaveValue("57.6800");
  });

  test("vessels API error shows error box", async ({ page }) => {
    await mockAllRoutes(page);
    await page.route("**/vessels", (r) =>
      r.fulfill({ status: 503, json: { detail: "Vessels unavailable." } }),
    );
    await page.goto("/vessels");

    await expect(page.locator(".error-box")).toBeVisible();
  });
});
