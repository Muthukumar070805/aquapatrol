import { test, expect } from "@playwright/test";
import {
  mockAllRoutes,
  PNG_DATA_URL,
  YOLO_DETECT,
  YOLO_STATUS_UNAVAILABLE,
  YOLO_DETECT_EMPTY,
} from "./helpers";

/**
 * Quick Detect page – comprehensive e2e coverage.
 *
 * Scenarios:
 *  1. Page loads with heading and sample thumbnails
 *  2. Detect button is disabled until a sample is selected
 *  3. Dropzone is visible and labelled
 *  4. Happy path: pick sample → detect → annotated image + two candidate rows
 *  5. Multiple detections render all table rows
 *  6. Empty detection (0 candidates) renders correctly
 *  7. YOLO unavailable → error banner shown, detect button disabled
 *  8. Download control visible after detection
 *  9. Second sample can also be selected
 */
test.describe("Quick Detect page", () => {
  test("renders page heading and sample thumbnails", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/detect");

    await expect(page.getByRole("heading", { name: "Quick Detect" })).toBeVisible();
    await expect(page.getByTestId("sample-scene-01")).toBeVisible();
    await expect(page.getByTestId("sample-scene-02")).toBeVisible();
  });

  test("Detect button is disabled before a sample is selected", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/detect");

    const detectBtn = page.getByTestId("detect-btn");
    await expect(detectBtn).toBeVisible();
    await expect(detectBtn).toBeDisabled();
  });

  test("dropzone is visible and labelled", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/detect");

    await expect(page.getByTestId("dropzone")).toBeVisible();
    await expect(page.getByTestId("dropzone")).toContainText("Drop an image");
  });

  test("happy path: sample -> detect -> result image + candidates", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/detect");

    await page.getByTestId("sample-scene-01").click();
    const detectBtn = page.getByTestId("detect-btn");
    await expect(detectBtn).toBeEnabled();
    await detectBtn.click();

    const result = page.getByTestId("yolo-result-img");
    await expect(result).toBeVisible();
    await expect(result).toHaveAttribute("src", PNG_DATA_URL);

    await expect(page.getByTestId("candidate-count")).toContainText("2");
    await expect(page.getByTestId("candidate-table")).toContainText("SPILL_001");
    await expect(page.getByTestId("candidate-table")).toContainText("82%");
    await expect(page.getByTestId("candidate-table")).toContainText("SPILL_002");
    await expect(page.getByTestId("candidate-table")).toContainText("61%");
  });

  test("renders correct number of candidate rows", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/detect");

    await page.getByTestId("sample-scene-01").click();
    await page.getByTestId("detect-btn").click();

    await expect(page.getByTestId("candidate-row")).toHaveCount(YOLO_DETECT.detections.length);
  });

  test("download annotated button appears after detection", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/detect");

    await page.getByTestId("sample-scene-01").click();
    await page.getByTestId("detect-btn").click();

    await expect(page.getByTestId("download-result")).toBeVisible();
  });

  test("zero-candidate detection shows count 0 and no table rows", async ({ page }) => {
    await mockAllRoutes(page);
    await page.route("**/yolo/detect", (r) => r.fulfill({ json: YOLO_DETECT_EMPTY }));
    await page.goto("/detect");

    await page.getByTestId("sample-scene-01").click();
    await page.getByTestId("detect-btn").click();

    await expect(page.getByTestId("candidate-count")).toContainText("0");
    await expect(page.getByTestId("candidate-row")).toHaveCount(0);
  });

  test("YOLO unavailable: shows error banner and disables detect button", async ({ page }) => {
    await mockAllRoutes(page);
    await page.route("**/yolo/status", (r) =>
      r.fulfill({ json: YOLO_STATUS_UNAVAILABLE }),
    );
    await page.goto("/detect");

    await expect(page.getByText(/YOLO detector unavailable/i)).toBeVisible();
    await page.getByTestId("sample-scene-01").click();
    await expect(page.getByTestId("detect-btn")).toBeDisabled();
  });

  test("second sample can also be selected and detected", async ({ page }) => {
    await mockAllRoutes(page);
    await page.goto("/detect");

    await page.getByTestId("sample-scene-02").click();
    await page.getByTestId("detect-btn").click();

    await expect(page.getByTestId("yolo-result-img")).toBeVisible();
  });
});
