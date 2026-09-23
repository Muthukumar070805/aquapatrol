"""Command-line entry point for YOLO oil-candidate detection.

Runs the YOLO MVP detector on a Sentinel-1 scene and prints a short summary
(number of candidates and their confidences).

Two input modes (pick exactly one):

* ``--aoi``  -- search the Copernicus Data Space Ecosystem for a Sentinel-1
  scene over an area of interest and date range, download it, and detect.
  Requires CDSE credentials (``CDSE_USER`` / ``CDSE_PASS`` from the environment
  or a ``.env`` file). This is the only mode that uses the network.
* ``--safe`` -- run on an already-downloaded ``.SAFE`` product (no network).

Requires the ``ultralytics`` extra and YOLO weights
(``OILSPILL_API_YOLO_WEIGHTS`` or ``--weights``).

Example
-------
AOI mode (search + download + detect)::

    python scripts/detect.py --aoi aoi.geojson --start 2024-01-01 --end 2024-01-31
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as a plain script without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from oilspill.detectors.yolo_detector import YoloDetector, YoloDetectorConfig


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the ``detect`` CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="detect",
        description="Sentinel-1 YOLO oil-candidate detection.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--aoi",
        type=Path,
        help="GeoJSON AOI; search CDSE, download a scene, then detect (needs --start/--end).",
    )
    mode.add_argument(
        "--safe",
        type=Path,
        help="Path to a downloaded .SAFE product to detect on (no network).",
    )

    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional output directory for the candidate GeoJSON.",
    )

    # AOI-mode options.
    parser.add_argument("--start", type=str, default=None, help="AOI mode: start date YYYY-MM-DD.")
    parser.add_argument("--end", type=str, default=None, help="AOI mode: end date YYYY-MM-DD.")
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=None,
        help="AOI mode: directory for the downloaded SAFE (default <out>/safe).",
    )

    # Shared detection options.
    parser.add_argument(
        "--weights",
        type=Path,
        default=None,
        help="YOLO checkpoint (.pt). Default: OILSPILL_API_YOLO_WEIGHTS env.",
    )
    parser.add_argument(
        "--polarisation",
        type=str,
        default="vv",
        help="SAR polarisation to calibrate (SAFE/AOI modes). Default vv.",
    )
    parser.add_argument(
        "--coastlines",
        type=Path,
        default=None,
        help="Natural Earth land vector for land screening (SAFE/AOI modes).",
    )
    parser.add_argument("--conf", type=float, default=0.25, help="YOLO confidence threshold.")
    parser.add_argument("--iou", type=float, default=0.45, help="NMS IoU threshold.")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the YOLO detection CLI; returns a process exit code."""
    import json
    import os

    from dotenv import load_dotenv

    from oilspill.pipeline.detect import detect_yolo_from_aoi, detect_yolo_from_safe

    args = parse_args(argv)
    load_dotenv()

    weights = args.weights or (
        Path(os.environ["OILSPILL_API_YOLO_WEIGHTS"])
        if os.environ.get("OILSPILL_API_YOLO_WEIGHTS")
        else None
    )
    detector = YoloDetector(
        YoloDetectorConfig(weights_path=weights, conf_threshold=args.conf, iou_threshold=args.iou)
    )

    if args.aoi is not None:
        if not args.start or not args.end:
            raise SystemExit("--aoi mode requires --start and --end (YYYY-MM-DD).")
        print(f"mode       : aoi ({args.aoi})")
        print(f"date range : {args.start} .. {args.end}")
        out = args.out or Path("outputs") / "yolo_run"
        output = detect_yolo_from_aoi(
            args.aoi,
            args.start,
            args.end,
            detector,
            out,
            download_dir=args.download_dir,
            polarisation=args.polarisation,
            coastlines_path=args.coastlines,
        )
    else:
        print(f"mode       : safe ({args.safe})")
        from oilspill.detectors.contracts import DetectionOutput

        output = detect_yolo_from_safe(
            args.safe,
            detector,
            polarisation=args.polarisation,
            coastlines_path=args.coastlines,
        )
        assert isinstance(output, DetectionOutput)

    print(f"candidates : {len(output.candidates)}")
    for cand in output.candidates:
        print(f"  - conf={cand.model_confidence:.2f} source={cand.geometry_source}")
    if args.out is not None:
        from dataclasses import asdict

        geo_path = args.out / "yolo_candidates.geojson"
        geo_path.parent.mkdir(parents=True, exist_ok=True)
        geo_path.write_text(json.dumps(asdict(output), default=str), encoding="utf-8")
        print(f"candidates : {geo_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
