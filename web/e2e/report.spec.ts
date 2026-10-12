import { test, expect } from "@playwright/test";
import { mockAllRoutes, REPORT_RESPONSE, VESSEL_1 } from "./helpers";

/**
 * Report page – e2e coverage.
 *
 * Scenarios:
 *  1. Renders "Incident Report" heading with case number
 *  2. Case ID panel shows case_id and case_number
 *  3. Observation time is displayed
 *  4. Spill candidate section shows spill ID
 *  5. Estimated origin section is present (even if lat/lon are "—" when keys differ)
 *  6. Vessel info section shows vessel name, MMSI, IMO
 *  7. AIS observations section shows ais_status
 *  8. Investigation signal: level, score and status are shown
 *  9. Disclaimer/warning box is visible
 * 10. "Back to case" link navigates back to /cases/:id
 * 11. "Generate Report" button is present and enabled
 * 12. Report API error shows error box and Back to case link
 */
test.describe("Report page", () => {
  test("renders Incident Report heading with case number", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/reports/case-uuid-001");

    await expect(page.getByRole("heading", { name: "Incident Report" })).toBeVisible();
    await expect(page.getByText(REPORT_RESPONSE.case_number).first()).toBeVisible();
  });

  test("Case ID panel shows case_id and case_number", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/reports/case-uuid-001");

    await expect(page.getByText(REPORT_RESPONSE.case_id).first()).toBeVisible();
    await expect(page.getByText(REPORT_RESPONSE.case_number).first()).toBeVisible();
  });

  test("observation time is displayed", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/reports/case-uuid-001");

    await expect(page.getByText(REPORT_RESPONSE.observation_time)).toBeVisible();
  });

  test("spill candidate section shows spill ID", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/reports/case-uuid-001");

    // The report.spill_candidate["spill_id"] is "SPILL_001"
    await expect(
      page.getByText(String(REPORT_RESPONSE.spill_candidate["spill_id"])),
    ).toBeVisible();
  });

  test("estimated origin section is present", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/reports/case-uuid-001");

    await expect(page.getByRole("heading", { name: "Estimated origin" })).toBeVisible();
  });

  test("vessel info section shows name and MMSI", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/reports/case-uuid-001");

    await expect(page.getByText(VESSEL_1.name)).toBeVisible();
    await expect(page.getByText(VESSEL_1.mmsi)).toBeVisible();
    await expect(page.getByText(VESSEL_1.imo)).toBeVisible();
  });

  test("AIS observations section shows ais_status", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/reports/case-uuid-001");

    await expect(page.getByRole("heading", { name: "AIS observations" })).toBeVisible();
    await expect(page.getByText(VESSEL_1.ais_status)).toBeVisible();
  });

  test("investigation signal shows level, score and status", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/reports/case-uuid-001");

    const signal = REPORT_RESPONSE.investigation_signal;
    await expect(page.getByText(signal.level)).toBeVisible();
    await expect(page.getByText(`${signal.score.toFixed(1)}%`)).toBeVisible();
    await expect(page.getByText(signal.status)).toBeVisible();
  });

  test("disclaimer/warning box is present", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/reports/case-uuid-001");

    await expect(page.getByText(/Simulated demo data/i)).toBeVisible();
  });

  test("Back to case link navigates to case detail page", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/reports/case-uuid-001");

    await page.getByRole("link", { name: /Back to case/i }).click();

    await expect(page).toHaveURL(/\/cases\/case-uuid-001/);
  });

  test("Generate Report button is present and enabled", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/reports/case-uuid-001");

    await expect(page.getByRole("button", { name: /Generate Report/i })).toBeEnabled();
  });

  test("report API error shows error box and Back to case link", async ({ page }) => {
    await mockAllRoutes(page);
    await page.route("**/reports/case-uuid-001", (r) =>
      r.fulfill({ status: 404, json: { detail: "Report not found." } }),
    );
    await page.goto("/reports/case-uuid-001");

    await expect(page.locator(".error-box")).toBeVisible();
    await expect(page.getByRole("link", { name: /Back to case/i })).toBeVisible();
  });
});
