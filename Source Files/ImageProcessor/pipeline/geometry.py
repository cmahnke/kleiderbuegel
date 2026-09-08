"""Geometry: crop with margin + rotation via PCA principal axis of the item mask."""

from __future__ import annotations

import cv2
import numpy as np

MARGIN_PX = 3  # user requirement


def item_bbox(alpha: np.ndarray, thr: float = 0.01) -> tuple[int, int, int, int] | None:
    ys, xs = np.nonzero(alpha > thr)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def crop_with_margin(rgb: np.ndarray, alpha: np.ndarray, margin: int = MARGIN_PX):
    bb = item_bbox(alpha)
    if bb is None:
        return None
    h, w = alpha.shape
    x1, y1, x2, y2 = bb
    x1, y1 = max(0, x1 - margin), max(0, y1 - margin)
    x2, y2 = min(w, x2 + margin), min(h, y2 + margin)
    return rgb[y1:y2, x1:x2].copy(), alpha[y1:y2, x1:x2].copy()


def principal_angle_deg(bin_mask: np.ndarray) -> float:
    """Angle of the mask's LONG axis measured from +x axis (image coords, y down),
    normalised to (-90, 90]."""
    ys, xs = np.nonzero(bin_mask)
    pts = np.stack([xs, ys], axis=1).astype(np.float64)
    pts -= pts.mean(axis=0, keepdims=True)
    cov = np.cov(pts.T)
    evals, evecs = np.linalg.eigh(cov)
    v = evecs[:, int(np.argmax(evals))]
    theta = float(np.degrees(np.arctan2(v[1], v[0])))  # (-180, 180]
    while theta > 90.0:
        theta -= 180.0
    while theta <= -90.0:
        theta += 180.0
    return theta


def rotate_expand(rgb: np.ndarray, alpha: np.ndarray, angle_deg: float):
    """Rotate content by angle_deg around center with expanded canvas (never crops).

    Positive angle rotates counter-clockwise in screen terms (OpenCV convention with
    y-down flips visual direction; validated by synthetic tests)."""
    h, w = alpha.shape
    M = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), angle_deg, 1.0)
    cos, sin = abs(M[0, 0]), abs(M[0, 1])
    nw, nh = int(round(h * sin + w * cos)), int(round(h * cos + w * sin))
    M[0, 2] += nw / 2.0 - w / 2.0
    M[1, 2] += nh / 2.0 - h / 2.0
    rgb_r = cv2.warpAffine(rgb, M, (nw, nh), flags=cv2.INTER_CUBIC,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)
    alpha_r = cv2.warpAffine(alpha, M, (nw, nh), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)
    return rgb_r, alpha_r


def align_item(rgb: np.ndarray, alpha: np.ndarray, cls: str,
               rot_threshold_deg: float = 1.0):
    """Rotate so long axis matches target: cutlery vertical, hanger horizontal.

    Returns (rgb, alpha, info) where info carries measured/applied angles."""
    bin_mask = alpha >= 0.5
    theta = principal_angle_deg(bin_mask)
    # Empirically (OpenCV y-down coords): warpAffine with angle A changes the measured
    # long-axis angle by -A, i.e. theta_after = theta - A. So A = theta - target.
    if cls == "hanger" or cls == "unknown":
        applied = theta          # target: long axis horizontal (theta = 0);
                                 # unknown items keep their measured orientation
    else:
        applied = theta - 90.0   # target: long axis vertical (theta = ±90)
    while applied > 90.0:
        applied -= 180.0
    while applied <= -90.0:
        applied += 180.0

    if abs(applied) < rot_threshold_deg:
        return rgb, alpha, {"measured_angle": theta, "applied_rotation": 0.0,
                            "skipped_rotation": True}

    rgb_r, alpha_r = rotate_expand(rgb, alpha, applied)
    # re-verify long axis after rotation
    theta_after = principal_angle_deg(alpha_r >= 0.5)
    return rgb_r, alpha_r, {"measured_angle": theta, "applied_rotation": float(applied),
                            "measured_angle_after": theta_after, "skipped_rotation": False}


def final_trim(rgb: np.ndarray, alpha: np.ndarray, margin: int = MARGIN_PX):
    """Crop again after rotation to the tight bbox + margin (drops rotated canvas waste)."""
    cropped = crop_with_margin(rgb, alpha, margin)
    if cropped is None:
        return rgb, alpha
    return cropped
