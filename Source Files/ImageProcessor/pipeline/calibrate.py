"""Build YOLOE visual-prompt embeddings (PE) from exemplar boxes.

Usage:
    python -m pipeline.calibrate exemplars.json

exemplars.json: [{"image": "IMG_6128.HEIC", "class": "hanger",
                  "box": [x1, y1, x2, y2]}]
Box coords are pixels in the EXIF-applied, enhanced image (what the detector
sees). One exemplar per class; classes from PROMPTS without an exemplar fall
back to MobileCLIP text prompts (e.g. fork/knife/spoon).

Output: models/detectors/yoloe-pe.npz (loaded by the `yoloe` detector backend).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

from ._env import DETECTORS_DIR, ensure_env_dirs

ensure_env_dirs()

DEFAULT_PE = DETECTORS_DIR / "yoloe-pe.npz"


def _preprocess(rgb_u8: np.ndarray, imgsz: int) -> torch.Tensor:
    """Net-space tensor. The channel flip is deliberate: empirically the
    YOLOE26 head performs best when the PE image and the detection images are
    presented in the same flipped domain (see detect._detect_yoloe)."""
    from ultralytics.data.augment import LetterBox
    lb = LetterBox(new_shape=(imgsz, imgsz), auto=False, center=True, stride=32)(image=rgb_u8)
    im = np.ascontiguousarray(lb.transpose(2, 0, 1)[::-1]) / 255.0
    return torch.from_numpy(im)[None].float()


def build_vpe(model, rgb_u8: np.ndarray, boxes: list[list[int]],
              cls_ids: list[int], imgsz: int, device: str) -> torch.Tensor:
    """Visual PE for one calibration image: (1, n_classes_in_image, D)."""
    from ultralytics.data.augment import LoadVisualPrompt
    h, w = rgb_u8.shape[:2]
    gain = min(imgsz / h, imgsz / w)
    pad_x, pad_y = (imgsz - round(w * gain)) / 2, (imgsz - round(h * gain)) / 2
    lb_boxes = np.array([[b[0] * gain + pad_x, b[1] * gain + pad_y,
                          b[2] * gain + pad_x, b[3] * gain + pad_y] for b in boxes],
                        dtype=np.float32)
    im_t = _preprocess(rgb_u8, imgsz).to(device)
    vis = LoadVisualPrompt().get_visuals(np.asarray(cls_ids), (imgsz, imgsz),
                                         bboxes=lb_boxes)
    with torch.no_grad():
        return model.model(im_t, vpe=vis[None].to(device), return_vpe=True)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="pipeline.calibrate",
                                description="Build YOLOE prompt embeddings from exemplar boxes")
    p.add_argument("exemplars", type=Path, help="exemplar JSON file")
    p.add_argument("--weights", default="yoloe-26x-seg.pt")
    p.add_argument("--imgsz", type=int, default=1024)
    p.add_argument("--device", default="mps")
    p.add_argument("--images-dir", type=Path, default=Path("test_images/real"),
                   help="directory exemplar 'image' names are resolved against")
    p.add_argument("--out", type=Path, default=DEFAULT_PE)
    p.add_argument("--no-text-fallback", action="store_true",
                   help="fail instead of adding text-prompt classes for missing ones")
    args = p.parse_args(argv)

    from ultralytics import YOLOE
    from .detect import PROMPTS, _ensure_ultralytics_weights, normalize_class

    specs = json.loads(args.exemplars.read_text(encoding="utf-8"))
    by_class: dict[str, dict] = {}
    for spec in specs:
        cls = spec["class"]
        if cls in by_class:
            raise SystemExit(f"class '{cls}' has more than one exemplar (not supported yet)")
        by_class[cls] = spec

    from .io import load_rgb
    from .enhance import enhance
    from ._env import ROOT
    weights = _ensure_ultralytics_weights(args.weights)
    model = YOLOE(str(weights), verbose=False).to(args.device)

    cols, names = [], []
    for cls, spec in by_class.items():
        img_path = Path(spec["image"])
        if not img_path.is_absolute():
            img_path = args.images_dir / img_path
        rgb, _ = load_rgb(img_path)
        er, _ = enhance(rgb)
        u8 = np.clip(er * 255, 0, 255).astype(np.uint8)
        pe = build_vpe(model, u8, [spec["box"]], [0], args.imgsz, args.device)
        cols.append(pe)
        names.append(cls)
        print(f"visual PE: {cls} <- {spec['image']} box={spec['box']}")

    text_classes = [t for t in PROMPTS if normalize_class(t) not in by_class]
    if text_classes and not args.no_text_fallback:
        pe_t = model.model.get_text_pe(text_classes)
        cols.append(pe_t)
        names.extend(text_classes)
        print(f"text PE: {text_classes}")
    elif text_classes and args.no_text_fallback:
        raise SystemExit(f"no exemplar for classes {text_classes} and --no-text-fallback set")

    pe = torch.cat(cols, dim=1)
    model.set_classes(names, pe)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    model.save_prompt_embeddings(str(args.out))
    print(f"saved {len(names)} class embeddings -> {args.out}  names={names}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
