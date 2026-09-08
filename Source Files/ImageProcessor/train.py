"""Custom-model fallback: auto-label photos with the current zero-shot detector,
then fine-tune YOLO on MPS. Only needed if zero-shot detection is weak on real photos.

Usage:
  # 1. put photos with clear cutlery/hanger content into a folder, then:
  python train.py prepare --images <dir> --out tmp/dataset [--conf 0.25]
      [--detector dino]           # use Grounding-DINO for better pseudo-labels
  #    (review/fix tmp/dataset labels, add val split if you like)
  # 2. train on MPS:
  python train.py train --data tmp/dataset [--model yolo11n.pt] [--epochs 50]
  # 3. use it:
  python -m pipeline IN OUT --detector yolo-world   # auto-picks custom weights if present
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline._env import ROOT, TMP_DIR, ensure_env_dirs

ensure_env_dirs()

CUSTOM_WEIGHTS = ROOT / "models" / "detectors" / "custom_cutlery_hanger.pt"


def cmd_prepare(args) -> int:
    import numpy as np
    from pipeline.detect import Detector, normalize_class
    from pipeline.io import list_images, load_rgb, write_json
    from PIL import Image as PILImage

    out = Path(args.out)
    (out / "images" / "train").mkdir(parents=True, exist_ok=True)
    (out / "labels" / "train").mkdir(parents=True, exist_ok=True)
    (out / "images" / "val").mkdir(parents=True, exist_ok=True)
    (out / "labels" / "val").mkdir(parents=True, exist_ok=True)

    det = Detector(backend=args.detector, device=args.device)
    files = list_images(Path(args.images))
    n_det = 0
    for i, path in enumerate(files, 1):
        rgb, _ = load_rgb(path, apply_exif=True)
        dets = det.detect(rgb, conf=args.conf)
        if not dets:
            print(f"[{i}/{len(files)}] {path.name}: no detections, skipped")
            continue
        h, w = rgb.shape[:2]
        lines = []
        for d in dets:
            cls = 0 if d.cls == "hanger" else 1  # 0=hanger, 1=cutlery
            x1, y1, x2, y2 = d.bbox
            xc, yc = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h
            bw, bh = (x2 - x1) / w, (y2 - y1) / h
            lines.append(f"{cls} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
        # save as png (lossless) for training
        img_u8 = np.clip(rgb * 255 + 0.5, 0, 255).astype(np.uint8)
        stem = path.stem
        PILImage.fromarray(img_u8, "RGB").save(out / "images" / "train" / f"{stem}.png")
        (out / "labels" / "train" / f"{stem}.txt").write_text("\n".join(lines) + "\n")
        # simple val split: every 6th image
        if i % 6 == 0:
            PILImage.fromarray(img_u8, "RGB").save(out / "images" / "val" / f"{stem}.png")
            (out / "labels" / "val" / f"{stem}.txt").write_text("\n".join(lines) + "\n")
        n_det += 1
        print(f"[{i}/{len(files)}] {path.name}: {len(dets)} box(es)")
    write_json(out / "prepared.json", {"images": len(files), "labeled": n_det})
    (out / "data.yaml").write_text(
        "path: " + str(out.resolve()) + "\n"
        "train: images/train\nval: images/val\nnames:\n  0: hanger\n  1: cutlery\n")
    print(f"dataset at {out} ({n_det} labeled). data.yaml written.")
    print("review labels, then: python train.py train --data " + str(out))
    return 0


def cmd_train(args) -> int:
    from ultralytics import YOLO
    model = YOLO(args.model)
    results = model.train(
        data=str(Path(args.data) / "data.yaml"),
        epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
        device=args.device, project=str(TMP_DIR / "runs"), name="cutlery_hanger",
        exist_ok=True, patience=args.patience, plots=False,
    )
    best = Path(model.trainer.best) if hasattr(model, "trainer") else None
    if best and best.exists():
        CUSTOM_WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(best, CUSTOM_WEIGHTS)
        print(f"best weights copied to {CUSTOM_WEIGHTS}")
        print("pipeline auto-uses them when --detector yolo-custom is passed")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="train", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("prepare", help="auto-label images into a YOLO dataset")
    pp.add_argument("--images", required=True)
    pp.add_argument("--out", default=str(TMP_DIR / "dataset"))
    pp.add_argument("--detector", default="dino", choices=["yolo-world", "dino"])
    pp.add_argument("--device", default="auto")
    pp.add_argument("--conf", type=float, default=0.25)
    pp.set_defaults(func=cmd_prepare)

    pt = sub.add_parser("train", help="fine-tune YOLO on MPS")
    pt.add_argument("--data", default=str(TMP_DIR / "dataset"))
    pt.add_argument("--model", default="yolo11n.pt")
    pt.add_argument("--epochs", type=int, default=50)
    pt.add_argument("--imgsz", type=int, default=640)
    pt.add_argument("--batch", type=int, default=8)
    pt.add_argument("--patience", type=int, default=20)
    pt.add_argument("--device", default="mps")
    pt.set_defaults(func=cmd_train)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
