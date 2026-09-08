"""Contact sheet: numbered thumbnails on checkerboard for visual review."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .io import save_png_rgba


def _checker(h: int, w: int, cell: int = 12) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w]
    c = (((yy // cell) + (xx // cell)) % 2).astype(np.float32)
    return (0.85 + 0.10 * (1.0 - c))[..., None]  # light gray checker


def item_thumb(rgb: np.ndarray, alpha: np.ndarray, size: int = 320) -> np.ndarray:
    h, w = alpha.shape
    scale = min(size / max(h, 1), size / max(w, 1), 1.0)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    a_img = Image.fromarray(np.clip(alpha * 255 + 0.5, 0, 255).astype(np.uint8), "L")
    r_img = Image.fromarray(np.clip(rgb * 255 + 0.5, 0, 255).astype(np.uint8), "RGB")
    a_img = a_img.resize((nw, nh), Image.LANCZOS)
    r_img = r_img.resize((nw, nh), Image.LANCZOS)
    a = np.asarray(a_img, dtype=np.float32) / 255.0
    r = np.asarray(r_img, dtype=np.float32) / 255.0
    bg = np.broadcast_to(_checker(nh, nw), (nh, nw, 3))
    comp = r * a[..., None] + bg * (1.0 - a[..., None])
    return comp


def contact_sheet(paths_and_imgs: list, out_path: Path, cols: int = 5,
                  size: int = 320) -> None:
    """paths_and_imgs: (name, rgb, alpha) or (name, rgb, alpha, caption_prefix)."""
    if not paths_and_imgs:
        return
    cols = max(1, min(cols, len(paths_and_imgs)))
    rows = (len(paths_and_imgs) + cols - 1) // cols
    pad, label_h = 10, 22
    W = cols * (size + pad) + pad
    H = rows * (size + label_h + pad) + pad
    canvas = np.full((H, W, 3), 0.94, dtype=np.float32)
    img = Image.fromarray(np.clip(canvas * 255, 0, 255).astype(np.uint8), "RGB")
    draw = ImageDraw.Draw(img)
    for i, entry in enumerate(paths_and_imgs):
        name, rgb, alpha = entry[0], entry[1], entry[2]
        prefix = entry[3] if len(entry) > 3 else ""
        r, c = divmod(i, cols)
        x = pad + c * (size + pad)
        y = pad + r * (size + label_h + pad)
        thumb = item_thumb(rgb, alpha, size)
        th, tw = thumb.shape[:2]
        arr = np.clip(thumb * 255 + 0.5, 0, 255).astype(np.uint8)
        img.paste(Image.fromarray(arr, "RGB"), (x, y))
        label = f"{prefix}{name}"[:48]
        color = (180, 30, 30) if prefix else (30, 30, 30)
        draw.text((x + 2, y + size + 4), label, fill=color)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", compress_level=6)


def review_sheet(rgb: np.ndarray, alpha: np.ndarray, out_path: Path) -> None:
    """Per-item side-by-side: orientation 0 vs 180 for manual checking."""
    a0, a1 = alpha, alpha[::-1, ::-1]
    r0, r1 = rgb, rgb[::-1, ::-1]
    t0 = item_thumb(r0, a0, 360)
    t1 = item_thumb(r1, a1, 360)
    h = max(t0.shape[0], t1.shape[0])
    w = t0.shape[1] + t1.shape[1] + 30
    canvas = np.full((h + 10, w + 10, 3), 0.94, dtype=np.float32)
    arr = np.clip(canvas * 255, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGB")
    img.paste(Image.fromarray(np.clip(t0 * 255, 0, 255).astype(np.uint8), "RGB"), (5, 5))
    img.paste(Image.fromarray(np.clip(t1 * 255, 0, 255).astype(np.uint8), "RGB"),
              (t0.shape[1] + 25, 5))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", compress_level=6)


def save_item_debug(path: Path, rgb: np.ndarray, alpha: np.ndarray) -> None:
    save_png_rgba(path, rgb, alpha)
