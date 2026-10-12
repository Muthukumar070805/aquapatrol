import { test, expect } from "@playwright/test";
import { mockAllRoutes, CASE_DETAIL, VESSEL_1, REPORT_RESPONSE } from "./helpers";

/**
 * Case Detail page – e2e coverage.
 *
 * Scenarios:
 *  1. Renders "Investigation Case" heading
 *  2. Case number and status badge are visible
 *  3. Spill ID and candidate confidence are shown
 *  4. Origin lat/lon and origin confidence are shown
 *  5. Vessel details panel: name, MMSI, IMO, type
 *  6. Timeline items are rendered
 *  7. INVESTIGATION SIGNAL section is visible
 *  8. "View report" link navigates to the report page
 *  9. "Back to vessels" link is present
 * 10. Case API error shows error box and Back to vessels link
 */
test.describe("Case Detail page", () => {
  test("renders Investigation Case heading", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/cases/case-uuid-001");

    await expect(page.getByRole("heading", { name: "Investigation Case" })).toBeVisible();
  });

  test("case number and status badge are visible", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/cases/case-uuid-001");

    await expect(page.getByText(CASE_DETAIL.case_number)).toBeVisible();
    await expect(page.getByText(CASE_DETAIL.status)).toBeVisible();
    await expect(page.getByText(CASE_DETAIL.risk_level)).toBeVisible();
  });

  test("candidate panel shows spill ID and confidence", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/cases/case-uuid-001");

    await expect(page.getByText(CASE_DETAIL.spill_id)).toBeVisible();
    await expect(
      page.getByText(CASE_DETAIL.candidate_confidence.toFixed(3)),
    ).toBeVisible();
  });

  test("origin panel shows lat, lon and confidence", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/cases/case-uuid-001");

    await expect(page.getByText(CASE_DETAIL.origin_lat.toFixed(4))).toBeVisible();
    await expect(page.getByText(CASE_DETAIL.origin_lon.toFixed(4))).toBeVisible();
    await expect(
      page.getByText(CASE_DETAIL.origin_confidence.toFixed(3)),
    ).toBeVisible();
  });

  test("vessel panel shows name, MMSI and IMO", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/cases/case-uuid-001");

    await expect(page.getByText(VESSEL_1.name)).toBeVisible();
    await expect(page.getByText(VESSEL_1.mmsi)).toBeVisible();
    await expect(page.getByText(VESSEL_1.imo)).toBeVisible();
    await expect(page.getByText(VESSEL_1.vessel_type)).toBeVisible();
  });

  test("timeline items are rendered", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/cases/case-uuid-001");

    for (const step of CASE_DETAIL.timeline) {
      await expect(page.getByText(step)).toBeVisible();
    }
  });

  test("INVESTIGATION SIGNAL section is visible", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/cases/case-uuid-001");

    await expect(page.getByRole("heading", { name: /INVESTIGATION SIGNAL/i })).toBeVisible();
    // Report returns level "HIGH"
    await expect(page.getByText(REPORT_RESPONSE.investigation_signal.level)).toBeVisible();
  });

  test("View report button navigates to report page", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/cases/case-uuid-001");

    await page.getByRole("button", { name: /View report/i }).click();

    await expect(page).toHaveURL(/\/reports\/case-uuid-001/);
  });

  test("Back to vessels link is present", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/cases/case-uuid-001");

    await expect(page.getByRole("link", { name: /Back to vessels/i })).toBeVisible();
  });

  test("case API error shows error box and Back to vessels", async ({ page }) => {
    await mockAllRoutes(page);
    await page.route("**/cases/case-uuid-001", (r) =>
      r.fulfill({ status: 404, json: { detail: "Case not found." } }),
    );
    await page.goto("/cases/case-uuid-001");

    await expect(page.locator(".error-box")).toBeVisible();
    await expect(page.getByRole("link", { name: /Back to vessels/i })).toBeVisible();
  });
});
