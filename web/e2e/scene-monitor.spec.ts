import { test, expect } from "@playwright/test";
import { mockAllRoutes, JOB_DONE, JOB_ERROR, SCENE_JOB_QUEUED } from "./helpers";

/**
 * Scene Monitor page – e2e coverage.
 *
 * Scenarios:
 *  1. Renders h1 "Scene Monitor"
 *  2. Default bounding-box inputs are pre-populated
 *  3. Start/End date fields are present
 *  4. "Analyze scene" button is visible (and enabled when YOLO is available)
 *  5. Submitting a job creates a job entry in the recent-jobs list
 *  6. Job status changes to "done" and results are shown
 *  7. Invalid bbox triggers an error message
 *  8. Job error status shows an error box
 *  9. Wind speed and optical-confirm inputs are present
 */
test.describe("Scene Monitor page", () => {
  test("renders Scene Monitor heading", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/scenes");

    await expect(page.getByRole("heading", { name: "Scene Monitor" })).toBeVisible();
  });

  test("bounding-box inputs are pre-populated with defaults", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/scenes");

    await expect(page.getByRole("spinbutton", { name: "North latitude" })).toHaveValue("41.4");
    await expect(page.getByRole("spinbutton", { name: "East longitude" })).toHaveValue("2.6");
    await expect(page.getByRole("spinbutton", { name: "South latitude" })).toHaveValue("40.9");
    await expect(page.getByRole("spinbutton", { name: "West longitude" })).toHaveValue("1.8");
  });

  test("start and end date inputs are visible", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/scenes");

    await expect(page.locator("#start")).toBeVisible();
    await expect(page.locator("#end")).toBeVisible();
  });

  test("Analyze scene button is enabled by default (YOLO available)", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/scenes");

    await expect(page.getByRole("button", { name: /Analyze scene/i })).toBeEnabled();
  });

  test("wind speed and optical-confirm inputs are present", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/scenes");

    // Wind speed input
    await expect(page.getByPlaceholder("e.g. 5.2")).toBeVisible();
    // Optical confirmation checkbox
    await expect(page.getByRole("checkbox")).toBeVisible();
    await expect(page.getByText(/Optical confirmation/i)).toBeVisible();
  });

  test("submitting a job shows it in the recent-jobs list", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/scenes");

    await page.getByRole("button", { name: /Analyze scene/i }).click();

    // The job id from mock is "job-abc123"
    await expect(page.getByText(SCENE_JOB_QUEUED.job_id)).toBeVisible();
  });

  test("completed job shows done status and YOLO result image", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/scenes");

    await page.getByRole("button", { name: /Analyze scene/i }).click();

    // The job immediately returns "done" from the mock
    await expect(page.getByText(/done/i)).toBeVisible();
    // Disclaimer text for investigation candidates
    await expect(page.getByText(/Investigation candidates/i)).toBeVisible();
    // YOLO result image
    await expect(page.getByRole("img", { name: /YOLO Detections/i })).toBeVisible();
  });

  test("invalid bbox (west >= east) shows error message", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/scenes");

    // Set west > east to trigger validation
    await page.getByRole("spinbutton", { name: "West longitude" }).fill("5.0");
    await page.getByRole("spinbutton", { name: "East longitude" }).fill("2.6");
    await page.getByRole("button", { name: /Analyze scene/i }).click();

    await expect(page.getByText(/Invalid bounding box/i)).toBeVisible();
  });

  test("job error status shows an error box", async ({ page }) => {
    await mockAllRoutes(page);
    // Override job response to return an error
    await page.route("**/jobs/job-abc123", (r) => r.fulfill({ json: JOB_ERROR }));
    await page.goto("/scenes");

    await page.getByRole("button", { name: /Analyze scene/i }).click();

    await expect(page.getByText(/Scene processing failed/i)).toBeVisible();
  });

  test("completed job shows Download GeoJSON button", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/scenes");

    await page.getByRole("button", { name: /Analyze scene/i }).click();

    await expect(page.getByRole("button", { name: /Download GeoJSON/i })).toBeVisible();
  });

  test("YOLO unavailable disables Analyze scene button", async ({ page }) => {
    await mockAllRoutes(page);
    await page.route("**/yolo/status", (r) =>
      r.fulfill({ json: { available: false, model_id: null, detail: "No weights." } }),
    );
    await page.goto("/scenes");

    await expect(page.getByRole("button", { name: /Analyze scene/i })).toBeDisabled();
    await expect(page.getByText(/YOLO detector unavailable/i)).toBeVisible();
  });
});
