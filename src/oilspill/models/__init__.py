"""Removed: segmentation model registry (YOLO-only build).

The five-class segmentation architectures (U-Net, DeepLabV3+, SegFormer,
foundation ViT) lived here. Oil-spill detection now uses the single-class YOLO
candidate detector in :mod:`oilspill.detectors.yolo_detector`.
"""

from __future__ import annotations

__all__: list[str] = []
