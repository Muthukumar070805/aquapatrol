import { test, expect } from "@playwright/test";

// 1x1 transparent PNG, used as a stand-in for sample/annotated images so the
// test is fully self-contained and deterministic with no real backend.
const PNG_1PX =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC";
const PNG_DATA_URL = `data:image/png;base64,${PNG_1PX}`;
const PNG_BYTES = Buffer.from(PNG_1PX, "base64");

const SAMPLES = {
  samples: [{ id: "scene-01", url: "/samples/scene-01.png" }],
};

const YOLO_STATUS = {
  available: true,
  model_id: "best.pt",
  detail: "YOLO detector ready (one-class oil candidate model).",
};

const YOLO_DETECT = {
  model_id: "best.pt",
  width: 1,
  height: 1,
  num_candidates: 1,
  detections: [
    {
      spill_id: "SPILL_001",
      bbox: [0, 0, 1, 1],
      confidence: 0.82,
      class_id: 0,
      class_name: "oil",
      tile_provenance: [0],
    },
  ],
  yolo_result_image: PNG_DATA_URL,
};

test("quick detect: sample → detect → annotated image + candidates", async ({ page }) => {
  // Mock every backend endpoint the app touches.
  await page.route("**/healthz", (r) =>
    r.fulfill({ json: { status: "ok" } }),
  );
  await page.route("**/samples", (r) => r.fulfill({ json: SAMPLES }));
  await page.route("**/samples/scene-01.png", (r) =>
    r.fulfill({ contentType: "image/png", body: PNG_BYTES }),
  );
  await page.route("**/yolo/status", (r) => r.fulfill({ json: YOLO_STATUS }));
  await page.route("**/yolo/detect", (r) => r.fulfill({ json: YOLO_DETECT }));

  await page.goto("/detect");

  await expect(page.getByRole("heading", { name: "Quick Detect" })).toBeVisible();

  // Pick the preloaded sample, then run detect.
  await page.getByTestId("sample-scene-01").click();
  await page.getByTestId("detect-btn").click();

  // Annotated result image appears.
  const result = page.getByTestId("yolo-result-img");
  await expect(result).toBeVisible();
  await expect(result).toHaveAttribute("src", PNG_DATA_URL);

  // Candidate count and table row appear.
  await expect(page.getByTestId("candidate-count")).toContainText("1");
  const rows = page.getByTestId("candidate-row");
  await expect(rows).toHaveCount(1);
  await expect(page.getByTestId("candidate-table")).toContainText("SPILL_001");
  await expect(page.getByTestId("candidate-table")).toContainText("82%");

  // Annotated download control is offered.
  await expect(page.getByTestId("download-result")).toBeVisible();
});
