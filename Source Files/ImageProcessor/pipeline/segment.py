"""Background removal via rembg, run in an isolated worker process.

macOS: torch (parent) and onnxruntime (child) each bundle libomp and crash when
loaded together; the persistent worker avoids both that and per-image model reloads.
Communication is lossless float32 .npy in tmp/seg/.
"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

import numpy as np

from ._env import ROOT, TMP_DIR

DEFAULT_SEGMENTER = "birefnet-general"


class Segmenter:
    def __init__(self, model: str = DEFAULT_SEGMENTER):
        self.model = model
        self._proc: subprocess.Popen | None = None
        self._dir = TMP_DIR / "seg"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _ensure_worker(self) -> subprocess.Popen:
        if self._proc is not None and self._proc.poll() is None:
            return self._proc
        self._proc = subprocess.Popen(
            [sys.executable, "-m", "pipeline.segworker", self.model],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr,
            text=True, cwd=str(ROOT),
        )
        line = self._proc.stdout.readline()
        if line.strip() != "READY":
            err = self._proc.stderr.read() if self._proc.stderr else ""
            raise RuntimeError(f"segmentation worker failed to start: {line!r} {err}")
        return self._proc

    def alpha(self, rgb: np.ndarray, model: str | None = None) -> np.ndarray:
        """Return float32 alpha in [0,1] at full original resolution (lossless round trip)."""
        worker = self._ensure_worker()
        token = uuid.uuid4().hex
        in_path = self._dir / f"{token}_in.npy"
        out_path = self._dir / f"{token}_out.npy"
        np.save(in_path, rgb)
        req = {"in": str(in_path), "out": str(out_path)}
        if model:
            req["model"] = model
        worker.stdin.write(json.dumps(req) + "\n")
        worker.stdin.flush()
        resp = json.loads(worker.stdout.readline())
        if not resp.get("ok"):
            raise RuntimeError(f"segmentation worker error: {resp.get('error')}")
        alpha = np.load(out_path)
        in_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)
        return alpha

    def human_mask(self, rgb: np.ndarray) -> np.ndarray:
        """Alpha of people/hands (u2net_human_seg) for occlusion handling."""
        return self.alpha(rgb, model="u2net_human_seg")

    def close(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.stdin.write(json.dumps({"cmd": "shutdown"}) + "\n")
                self._proc.stdin.flush()
                self._proc.wait(timeout=10)
            except Exception:
                self._proc.kill()
        self._proc = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def _binary_components(bin_mask: np.ndarray):
    """Connected components of a binary mask; returns (labels, stats, n) via OpenCV."""
    import cv2
    m = (bin_mask > 0).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    return labels, stats, n


def _fill_holes(bin_mask: np.ndarray) -> np.ndarray:
    """Flood-fill background from image border; everything unreached is a hole -> object."""
    import cv2
    h, w = bin_mask.shape
    inv = (1 - bin_mask.astype(np.uint8)).copy()
    ffmask = np.zeros((h + 2, w + 2), dtype=np.uint8)
    cv2.floodFill(inv, ffmask, (0, 0), 0)
    holes = inv.astype(bool)
    return (bin_mask | holes)


def clean_alpha(alpha: np.ndarray, min_area_frac: float = 0.002,
                fill_holes: bool = True,
                human: np.ndarray | None = None,
                thin_rescue_r: int = 60) -> np.ndarray:
    """Connectivity-based cleanup. alpha float32 [0,1]. Returns float32 [0,1].

    human: optional people/hands alpha; those pixels are removed from the object
    mask (a hand holding an item must not become part of it). A hand mask also
    covers the thin wire/hook it grips, so subtracting it wholesale amputates
    hooks (the severed remainder is later dropped as a small component). Thin
    structures are therefore rescued BEFORE subtraction: within the overlap
    their distance-transform radius is the wire half-width, while hand blobs
    are thick and stay removed. Where a hand overlapped an object the outline
    is reconnected with a closing pass and the hole-fill cap is relaxed, since
    the occluded area is genuinely unknown.
    """
    import cv2
    if alpha.max() <= 0.01:
        return alpha

    # low threshold: thin/soft structures (metal hooks, matte edges) must not be
    # cut away; soft alpha values are preserved inside the kept region.
    bin_mask = alpha >= 0.15
    if not bin_mask.any():
        return alpha * 0.0

    human_used = False
    if human is not None:
        hm = human >= 0.5
        if hm.any() and (bin_mask & hm).any():
            medium = hm & bin_mask
            if medium.any() and thin_rescue_r > 0:
                dt = cv2.distanceTransform(medium.astype(np.uint8),
                                           cv2.DIST_L2, 5)
                thin = medium & (dt <= thin_rescue_r)
                bin_mask = (bin_mask & ~hm) | thin
            else:
                bin_mask &= ~hm
            human_used = True
            if not bin_mask.any():
                return alpha * 0.0

    # re-connect outlines cut by removed hands (closing), then fill holes
    if human_used:
        k = max(5, int(0.01 * np.sqrt(bin_mask.shape[0] * bin_mask.shape[1]))) | 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        bin_mask = cv2.morphologyEx(bin_mask.astype(np.uint8), cv2.MORPH_CLOSE,
                                    kernel).astype(bool)

    # 1) fill enclosed holes (white reflection patches on metal) — only small ones,
    #    so background seen *between* fork tines is not painted over when large.
    keep = bin_mask
    if fill_holes:
        filled = _fill_holes(bin_mask)
        holes = filled & ~bin_mask
        if holes.any():
            h_labels, h_stats, h_n = _binary_components(holes)
            obj_area = int(bin_mask.sum())
            hole_cap = 0.15 if human_used else 0.02  # hand-occluded area is unknown
            h_keep = np.zeros_like(holes)
            for i in range(1, h_n):
                area = int(h_stats[i, cv2.CC_STAT_AREA])
                if area <= max(1, int(obj_area * hole_cap)):
                    h_keep |= h_labels == i
            keep = bin_mask | h_keep

    # 2) drop components that are background leaks: tiny, or border-touching with low alpha
    labels, stats, n = _binary_components(keep)
    for i in range(1, n):
        comp = labels == i
        touches_border = comp[0, :].any() or comp[-1, :].any() or comp[:, 0].any() or comp[:, -1].any()
        mean_a = float(alpha[comp].mean())
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < max(64, min_area_frac * alpha.size):
            keep &= ~comp
        elif touches_border and mean_a < 0.45:
            keep &= ~comp

    if not keep.any():
        return alpha * 0.0

    # 3) keep model soft alpha inside 'keep'; hard-suppress outside.
    #    Enclosed filled holes get a high alpha (they are metal, not background).
    out = alpha * keep.astype(np.float32)
    holes_kept = keep & ~bin_mask
    if holes_kept.any():
        out[holes_kept] = np.maximum(out[holes_kept], 0.92)
    return out
