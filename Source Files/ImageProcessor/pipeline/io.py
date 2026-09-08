"""Lossless I/O: HEIC/JPEG decode to float32 RGB, PNG encode only."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

import pillow_heif

_EXIF_ORIENTATION = 274
SUPPORTED_EXT = {".heic", ".heif", ".hif", ".jpg", ".jpeg", ".jpe", ".png", ".tif", ".tiff", ".bmp"}

pillow_heif.register_heif_opener(thumbnails=False)


def list_images(directory: Path) -> list[Path]:
    files = [p for p in sorted(directory.iterdir())
             if p.is_file() and p.suffix.lower() in SUPPORTED_EXT]
    return files


def _exif_orientation(img: Image.Image) -> int:
    try:
        exif = img.getexif()
        return int(exif.get(_EXIF_ORIENTATION, 1))
    except Exception:
        return 1


def load_rgb(path: Path, apply_exif: bool = True) -> tuple[np.ndarray, dict]:
    """Decode once to float32 RGB in [0,1]; EXIF orientation applied as a hint only.

    Returns (rgb float32 HxWx3, info dict). No re-encoding, single decode."""
    with Image.open(path) as img:
        info = {
            "size": img.size,
            "exif_orientation": _exif_orientation(img),
            "mode": img.mode,
        }
        if apply_exif:
            img = ImageOps.exif_transpose(img)
        info["size_after_exif"] = img.size
        rgb = img.convert("RGB")
    arr = np.asarray(rgb, dtype=np.float32) / 255.0
    return arr, info


def save_png_rgba(path: Path, rgb: np.ndarray, alpha: np.ndarray, depth: int = 8) -> None:
    """Final save: the ONLY 8-bit quantization step in the whole pipeline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if depth == 8:
        a8 = np.clip(np.rint(alpha * 255.0), 0, 255).astype(np.uint8)
        rgba = np.dstack([np.clip(np.rint(rgb * 255.0), 0, 255).astype(np.uint8), a8])
        Image.fromarray(rgba, "RGBA").save(path, format="PNG", compress_level=6)
    elif depth == 16:
        a16 = np.clip(np.rint(alpha * 65535.0), 0, 65535).astype(np.uint16)
        rgba = np.dstack([np.clip(np.rint(rgb * 65535.0), 0, 65535).astype(np.uint16), a16])
        Image.fromarray(rgba, "RGBA").save(path, format="PNG", compress_level=6)
    else:
        raise ValueError(f"unsupported depth {depth}")


def save_debug_image(path: Path, arr: np.ndarray) -> None:
    """tmp/ artifacts only; always lossless (PNG float impossible -> use .npy for float)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if arr.dtype == np.float32:
        np.save(path.with_suffix(".npy"), arr)
    else:
        Image.fromarray(arr).save(path.with_suffix(".png"), format="PNG")


def write_report_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for r in rows:
        for k in r.keys():
            if k not in fieldnames:
                fieldnames.append(k)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, default=str)
