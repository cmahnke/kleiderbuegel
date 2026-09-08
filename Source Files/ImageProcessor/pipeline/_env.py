"""Local directory pinning for all caches/temp files. Import FIRST, before heavy libs."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MODELS_DIR = ROOT / "models"
TMP_DIR = ROOT / "tmp"
OUTPUT_DIR = ROOT / "output"

# Keep every cache and temp artifact inside the project directory.
os.environ.setdefault("U2NET_HOME", str(MODELS_DIR / "rembg"))
os.environ.setdefault("HF_HOME", str(MODELS_DIR / "hf"))
os.environ.setdefault("YOLO_CONFIG_DIR", str(TMP_DIR / "ultralytics"))
os.environ.setdefault("ULTRALYTICS_SETTINGS", str(TMP_DIR / "ultralytics"))
# Allow CPU fallback for ops not implemented on MPS (e.g. some attention paths).
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
# torch and onnxruntime both ship libomp on macOS; without this the process aborts.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
# Avoid ultralytics telemetry and update checks.
os.environ.setdefault("YOLO_OFFLINE", "0")
os.environ.setdefault("ULTRALYTICS_AUTO_UPDATE", "false")

DETECTORS_DIR = MODELS_DIR / "detectors"


def ensure_env_dirs() -> None:
    for p in (MODELS_DIR, TMP_DIR, OUTPUT_DIR, DETECTORS_DIR,
              Path(os.environ["YOLO_CONFIG_DIR"]),
              MODELS_DIR / "rembg", MODELS_DIR / "hf"):
        p.mkdir(parents=True, exist_ok=True)
