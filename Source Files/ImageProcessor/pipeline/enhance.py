"""Enhancement: white balance, auto contrast, saturation — all in float32, no quantization."""

from __future__ import annotations

import cv2
import numpy as np


def _border_mask(shape: tuple[int, int], frac: float = 0.08) -> np.ndarray:
    h, w = shape
    m = np.zeros((h, w), dtype=bool)
    bh, bw = max(1, int(h * frac)), max(1, int(w * frac))
    m[:bh, :] = True
    m[-bh:, :] = True
    m[:, :bw] = True
    m[:, -bw:] = True
    return m


def _near_white(rgb: np.ndarray) -> np.ndarray:
    lum = rgb.mean(axis=2)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    return (lum > 0.90) & (sat < 0.10)


def white_balance(rgb: np.ndarray) -> np.ndarray:
    """Estimate the white point from bright border pixels (photo background is white)."""
    ring = _border_mask(rgb.shape[:2])
    if not ring.any():
        return rgb
    vals = rgb[ring]
    lum = vals.mean(axis=1)
    bright = vals[lum >= np.percentile(lum, 80)] if len(vals) > 10 else vals
    wp = np.clip(bright.mean(axis=0), 1e-3, 1.0)
    gain = 1.0 / wp
    # Keep gains mild to avoid extreme casts on already-correct images.
    gain = np.clip(gain, 0.7, 1.4)
    return np.clip(rgb * gain[None, None, :], 0.0, 1.0)


def auto_contrast(rgb: np.ndarray, max_gain: float = 1.5) -> np.ndarray:
    """Background-anchored levels stretch with a gain clamp.

    The white background (99.5th pct of the border ring) is mapped to 1.0. The
    black point follows from the global 0.5th percentile, but the overall gain is
    clamped so a small subject on a huge white field is never crushed to black."""
    ring = _border_mask(rgb.shape[:2])
    flat = rgb.reshape(-1, 3)
    if ring.any():
        hi = np.percentile(rgb[ring].reshape(-1, 3), 99.5, axis=0)
    else:
        hi = np.percentile(flat, 99.5, axis=0)
    lo_global = np.percentile(flat, 0.5, axis=0)
    hi = np.maximum(hi, 0.05)
    gain = np.clip(1.0 / np.maximum(hi - lo_global, 1e-3), 1.0, max_gain)
    eff_lo = hi - 1.0 / gain
    return np.clip((rgb - eff_lo[None, None, :]) * gain[None, None, :], 0.0, 1.0)


def auto_color(rgb: np.ndarray, target_sat: float = 0.35) -> np.ndarray:
    """Gently normalise saturation of the subject toward a mild target."""
    hsv = cv2.cvtColor(np.clip(rgb, 0.0, 1.0), cv2.COLOR_RGB2HSV)
    s = hsv[..., 1]
    fg = ~_near_white(np.clip(rgb, 0.0, 1.0))
    mean_s = float(s[fg].mean()) if fg.any() else float(s.mean())
    gain = float(np.clip(target_sat / max(mean_s, 1e-3), 0.9, 1.3))
    hsv[..., 1] = np.clip(s * gain, 0.0, 1.0)
    return np.clip(cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB), 0.0, 1.0)


def enhance(rgb: np.ndarray) -> tuple[np.ndarray, dict]:
    """Full enhancement chain. Input/output float32 RGB [0,1]. Single pass, no rounding."""
    wb = white_balance(rgb)
    ac = auto_contrast(wb)
    out = auto_color(ac)
    info = {"white_balance": True, "auto_contrast": True, "auto_color": True}
    return out, info
