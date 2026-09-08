"""CLI orchestrator: python -m pipeline IN_DIR OUT_DIR [options]"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

from ._env import ROOT, TMP_DIR, ensure_env_dirs
from .contact import contact_sheet, review_sheet
from .detect import Detection
from .geometry import align_item, crop_with_margin, final_trim
from .io import (list_images, load_rgb, save_debug_image, save_png_rgba,
                 write_json, write_report_csv)
from .orient import apply_manual_flip, pick_orientation
from .segment import DEFAULT_SEGMENTER, Segmenter, clean_alpha
from .split import split_items


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="pipeline",
        description="Cutlery / coat hanger photo pipeline -> transparent PNG crops")
    p.add_argument("input_dir", type=Path)
    p.add_argument("output_dir", type=Path)
    p.add_argument("--detector", default="yoloe",
                   choices=["yolo-world", "yoloe", "dino", "yolo-custom"],
                   help="yoloe = YOLOE26 visual-prompt detector (default, most accurate); "
                        "yolo-world = YOLOv8s-Worldv2 (text prompts, legacy fallback)")
    p.add_argument("--yoloe-weights", default="yoloe-26x-seg.pt",
                   help="YOLOE weights file (downloaded into models/detectors/ on first use)")
    p.add_argument("--yoloe-pe", type=Path, default=None,
                   help="prompt-embedding file for --detector yoloe (default models/detectors/yoloe-pe.npz)")
    p.add_argument("--segmenter", default=DEFAULT_SEGMENTER,
                   choices=["birefnet-general", "bria-rmbg", "isnet-general-use", "u2net"])
    p.add_argument("--dino-weights", default="IDEA-Research/grounding-dino-tiny")
    p.add_argument("--conf", type=float, default=0.15)
    p.add_argument("--margin", type=int, default=3, help="crop margin px (default 3)")
    p.add_argument("--device", default="auto", choices=["auto", "mps", "cpu"])
    p.add_argument("--clip-device", default="auto", choices=["auto", "mps", "cpu"])
    p.add_argument("--depth", type=int, default=8, choices=[8, 16])
    p.add_argument("--no-exif-rotate", action="store_true",
                   help="ignore EXIF orientation hint (metadata untrusted)")
    p.add_argument("--no-hole-fill", action="store_true",
                   help="do not fill enclosed holes in the mask")
    p.add_argument("--no-clip", action="store_true", help="disable CLIP end-up scoring")
    p.add_argument("--rot-threshold", type=float, default=1.0)
    p.add_argument("--cls-margin", type=float, default=0.15,
                   help="min CLIP class-probability margin; below -> item ambiguous (no output)")
    p.add_argument("--orient-margin", type=float, default=0.05,
                   help="min CLIP up/down margin; below -> heuristic, else ambiguous")
    p.add_argument("--occlusion-limit", type=float, default=0.35,
                   help="max fraction of an item that may be occluded by a hand")
    p.add_argument("--no-human", action="store_true",
                   help="skip people/hand mask subtraction (faster)")
    p.add_argument("--force", action="store_true", help="reprocess already-processed inputs")
    p.add_argument("--review", action="store_true", help="write per-item both-orientation sheets")
    p.add_argument("--debug", action="store_true", help="dump stage checkpoints to tmp/")
    p.add_argument("--orient", action="append", default=[],
                   metavar="FILESTEM=DEG", help="manual flip for an item, e.g. IMG_0001_2=180")
    return p.parse_args(argv)


def resolve_device(pref: str) -> str:
    if pref != "auto":
        return pref
    import torch
    return "mps" if torch.backends.mps.is_available() else "cpu"


def process_image(path: Path, out_dir: Path, args, detector, segmenter,
                  manual_flips: dict[str, int]) -> list[dict]:
    t0 = time.time()
    stem = path.stem
    rgb, meta = load_rgb(path, apply_exif=not args.no_exif_rotate)
    h, w = rgb.shape[:2]

    enhanced, enh_info = _enhance_hook(rgb)
    if args.debug:
        save_debug_image(TMP_DIR / "debug" / f"{stem}_1_enhanced", enhanced)

    detections = detector.detect(enhanced, conf=args.conf)
    if args.debug:
        write_json(TMP_DIR / "debug" / f"{stem}_2_detections.json",
                   {"detections": [d.__dict__ for d in detections]})

    alpha_raw = segmenter.alpha(enhanced)
    if args.debug:
        save_debug_image(TMP_DIR / "debug" / f"{stem}_3_alpha_raw", alpha_raw)

    human = None
    if not args.no_human:
        human = segmenter.human_mask(enhanced)

    alpha = clean_alpha(alpha_raw, fill_holes=not args.no_hole_fill, human=human)
    if args.debug:
        save_debug_image(TMP_DIR / "debug" / f"{stem}_4_alpha_clean", alpha)

    fg_frac = float((alpha >= 0.5).mean())
    if fg_frac < 0.005 or fg_frac > 0.60:
        raise ValueError(f"suspicious segmentation: foreground {fg_frac:.1%} of image")

    clip_dev = resolve_device(args.clip_device)

    def classify_whole(comp_mask: np.ndarray) -> str | None:
        """CLIP verdict on an ENTIRE component (before any split decision).
        Returns the confident class or None. Prevents false force-splits of
        single hangers that YOLO-World covers with several weak 'knife' boxes."""
        from .orient import clip_class_scores
        ys, xs = np.nonzero(comp_mask)
        if len(xs) < 400:
            return None
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        try:
            raw = clip_class_scores(enhanced[y0:y1, x0:x1],
                                    comp_mask[y0:y1, x0:x1].astype(np.float32),
                                    clip_dev)
        except Exception:
            return None
        # probability space (same softmax as pick_orientation), not raw logits
        flat = {f"{c}:{o}": s for c, (up, dn) in raw.items()
                for o, s in (("up", up), ("down", dn))}
        v = np.array(list(flat.values()), dtype=np.float64)
        p = np.exp(v - v.max())
        p /= p.sum()
        probs: dict[str, float] = {}
        for (k, _), pi in zip(flat.items(), p):
            probs[k.split(":")[0]] = probs.get(k.split(":")[0], 0.0) + float(pi)
        ranked = sorted(probs, key=lambda c: -probs[c])
        margin = probs[ranked[0]] - probs[ranked[1]]
        return ranked[0] if margin >= args.cls_margin else None

    items = split_items(alpha, detections, classify_whole=classify_whole)
    if not items:
        return [{"input": path.name, "status": "no-object",
                 "seconds": round(time.time() - t0, 2)}]
    hm_bin = (human >= 0.5) if human is not None else None

    rows = []
    thumbs = []
    orient_scores_by_item: dict[str, dict] = {}
    for idx, item in enumerate(items, start=1):
        cropped = crop_with_margin(enhanced, item.alpha, margin=args.margin)
        if cropped is None:
            continue
        crgb, calpha = cropped
        key = f"{stem}_{idx}"
        orient_scores_by_item.setdefault(key, {})

        item_bin = item.alpha >= 0.15
        item_area = max(1.0, float(item_bin.sum()))
        # Hand occlusion measured against the RAW segmentation (pre-cleanup):
        # there the gripping hand is still part of the object blob, so a held
        # item shows a large hand fraction. The cleaned mask alone always
        # reads ~0 because the hand pixels were already subtracted.
        occlusion = 0.0
        if hm_bin is not None and hm_bin.any():
            ys, xs = np.nonzero(item_bin)
            y0, y1 = int(ys.min()), int(ys.max()) + 1
            x0, x1 = int(xs.min()), int(xs.max()) + 1
            raw_bin = alpha_raw[y0:y1, x0:x1] >= 0.5
            hand_in_item = hm_bin[y0:y1, x0:x1] & raw_bin
            occlusion = float(hand_in_item.sum()) / item_area

        ambiguous: list[str] = []
        if item.edge_clipped:
            ambiguous.append("object clipped at image edge (partial object)")
        if occlusion > args.occlusion_limit:
            ambiguous.append(f"occluded by hand ({occlusion:.0%} > {args.occlusion_limit:.0%})")

        orient_info: dict = {"flip": 0, "method": "disabled", "flip_decided": None,
                             "class": item.cls, "class_margin": 0.0,
                             "orient_margin": 0.0, "scores": {}}

        # unknown class (no detection): decide class visually, then align once
        if item.cls == "unknown" and not args.no_clip:
            ci = pick_orientation(crgb, calpha, "unknown", device=clip_dev,
                                  orient_margin=args.orient_margin,
                                  cls_margin=args.cls_margin)
            orient_info = ci
            if ci.get("flip"):
                crgb, calpha = apply_manual_flip(crgb, calpha, int(ci["flip"]))
            orient_scores_by_item[key].update(ci.get("scores") or {})
            if ci.get("class_margin", 0.0) < args.cls_margin or ci.get("class") not in ("cutlery", "hanger"):
                ambiguous.append(
                    f"class ambiguous (margin {ci.get('class_margin', 0.0):.2f} < {args.cls_margin})")
            else:
                item.cls = ci["class"]
                item.notes.append(f"class->{item.cls}")
        elif item.cls == "unknown":
            ambiguous.append("class undecidable (CLIP disabled)")

        crgb, calpha, geo = align_item(crgb, calpha, item.cls,
                                       rot_threshold_deg=args.rot_threshold)
        crgb, calpha = final_trim(crgb, calpha, margin=args.margin)

        if key in manual_flips:
            crgb, calpha = apply_manual_flip(crgb, calpha, manual_flips[key])
            orient_info["method"] = "manual"
            orient_info["flip"] = manual_flips[key]
            orient_info["flip_decided"] = True
        elif not args.no_clip and not ambiguous:
            oi = pick_orientation(crgb, calpha, item.cls, device=clip_dev,
                                  orient_margin=args.orient_margin,
                                  cls_margin=args.cls_margin)
            orient_info = oi
            if oi.get("flip"):
                crgb, calpha = apply_manual_flip(crgb, calpha, int(oi["flip"]))
            orient_scores_by_item[key].update(oi.get("scores") or {})
            if oi.get("class_switch"):
                item.cls = oi["class"]
                item.notes.append(f"class->{item.cls} (clip margin {oi['class_margin']:.2f})")
                crgb, calpha, geo = align_item(crgb, calpha, item.cls,
                                               rot_threshold_deg=args.rot_threshold)
                crgb, calpha = final_trim(crgb, calpha, margin=args.margin)
            if not oi.get("flip_decided"):
                if oi.get("method") == "clip-vs-heuristic-disagree":
                    ambiguous.append(
                        "orientation undecided: CLIP and shape heuristic disagree "
                        f"(CLIP margin {oi.get('orient_margin', 0.0):.2f})")
                else:
                    ambiguous.append(
                        f"orientation undecided (margin {oi.get('orient_margin', 0.0):.2f} "
                        f"< {args.orient_margin})")

        out_name = f"{stem}_{idx}_{item.cls}.png"
        status = "ambiguous" if ambiguous else "ok"
        reason = "; ".join(ambiguous)
        if status == "ok":
            save_png_rgba(out_dir / out_name, crgb, calpha, depth=args.depth)

        if args.review or status == "ambiguous":
            review_sheet(crgb, calpha, out_dir / "review" / f"{key}_review.png")

        # contact thumbnail (OpenCV returns 2-D for single-channel input)
        if crgb.shape[0] * crgb.shape[1] < 640 * 640:
            thumb_rgb, thumb_alpha = crgb, calpha
        else:
            thumb_rgb = np.asarray(_resize(crgb, 640), dtype=np.float32) / 255.0
            thumb_alpha = np.asarray(_resize(calpha, 640), dtype=np.float32)
        prefix = ("[AMBIGUOUS] " if ambiguous else "")
        thumbs.append((out_name, thumb_rgb, thumb_alpha, prefix))

        rows.append({
            "input": path.name, "item": idx, "class": item.cls,
            "source": item.source, "score": round(item.score, 3),
            "detections": len(detections),
            "measured_angle": round(geo.get("measured_angle", 0.0), 1),
            "applied_rotation": round(geo.get("applied_rotation", 0.0), 1),
            "flip": orient_info.get("flip", 0),
            "orient_method": orient_info.get("method"),
            "class_margin": round(float(orient_info.get("class_margin") or 0.0), 3),
            "orient_margin": round(float(orient_info.get("orient_margin") or 0.0), 3),
            "occlusion": round(occlusion, 3),
            "edge_clipped": int(item.edge_clipped),
            "output": out_name if status == "ok" else "",
            "status": status,
            "reason": reason,
            "notes": ";".join(item.notes),
            "seconds": round(time.time() - t0, 2),
        })

    contact_sheet(thumbs, out_dir / f"{stem}_contact.png")
    write_json(out_dir / f"{stem}.json", {
        "input": path.name, "exif_orientation": meta["exif_orientation"],
        "size": meta["size"], "size_after_exif": meta["size_after_exif"],
        "enhance": enh_info, "detections": [d.__dict__ for d in detections],
        "items": rows,
        "orient_scores": orient_scores_by_item,
    })
    return rows


def _enhance_hook(rgb: np.ndarray):
    from .enhance import enhance
    return enhance(rgb)


def _resize(arr: np.ndarray, max_side: int) -> np.ndarray:
    import cv2
    h, w = arr.shape[:2]
    scale = min(max_side / max(h, w), 1.0)
    nw, nh = int(round(w * scale)), int(round(h * scale))
    interp = cv2.INTER_AREA if arr.ndim == 2 else cv2.INTER_AREA
    return cv2.resize(arr, (nw, nh), interpolation=interp)


def main(argv=None) -> int:
    ensure_env_dirs()
    args = parse_args(argv)
    in_dir = args.input_dir if args.input_dir.is_absolute() else (ROOT / args.input_dir).resolve()
    out_dir = args.output_dir if args.output_dir.is_absolute() else (ROOT / args.output_dir).resolve()
    if not in_dir.is_dir():
        print(f"input dir not found: {in_dir}", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)

    manual_flips: dict[str, int] = {}
    for spec in args.orient:
        k, v = spec.rsplit("=", 1)
        manual_flips[k] = int(v)

    files = list_images(in_dir)
    if not files:
        print(f"no images found in {in_dir}")
        return 0

    from .detect import Detector, YOLOE_PE
    detector = Detector(backend=args.detector, device=resolve_device(args.device),
                        dino_model=args.dino_weights, yoloe_weights=args.yoloe_weights,
                        yoloe_pe=args.yoloe_pe or YOLOE_PE)
    segmenter = Segmenter(model=args.segmenter)

    done_keys = set()
    report_path = out_dir / "report.csv"
    all_rows: list[dict] = []
    if report_path.exists() and not args.force:
        import csv
        with report_path.open(newline="", encoding="utf-8") as fh:
            all_rows = list(csv.DictReader(fh))
            # ambiguous/error rows are retried on the next run (they need attention)
            ok_inputs = {r["input"] for r in all_rows if r.get("status") in ("ok", "no-object")}
            attention = {r["input"] for r in all_rows
                         if str(r.get("status", "")).startswith(("ambiguous", "error"))}
            done_keys = ok_inputs - attention

    # make-style freshness: skip only if the outputs are newer than both the
    # input file and the newest pipeline source (code changes trigger reprocess)
    code_mtime = 0.0
    if done_keys:
        code_mtime = max(p.stat().st_mtime for p in Path(__file__).parent.glob("*.py"))

    def outputs_fresh(path: Path) -> bool:
        in_mtime = path.stat().st_mtime
        out_pngs = [out_dir / r["output"] for r in all_rows
                    if r.get("input") == path.name and r.get("output")]
        out_pngs.append(out_dir / f"{path.stem}_contact.png")
        return all(p.exists() and p.stat().st_mtime > in_mtime
                   and p.stat().st_mtime > code_mtime for p in out_pngs)

    print(f"processing {len(files)} image(s) from {in_dir} -> {out_dir}")
    for i, path in enumerate(files, start=1):
        if path.name in done_keys and not args.force:
            if outputs_fresh(path):
                print(f"[{i}/{len(files)}] skip (fresh): {path.name}")
                continue
            print(f"[{i}/{len(files)}] reprocess (stale output): {path.name}")
        try:
            rows = process_image(path, out_dir, args, detector, segmenter, manual_flips)
            all_rows = [r for r in all_rows if r.get("input") != path.name] + rows
            n_ok = sum(1 for r in rows if r.get("status") == "ok")
            n_amb = sum(1 for r in rows if r.get("status") == "ambiguous")
            tag = f"{n_ok} item(s)"
            if n_amb:
                tag += f", {n_amb} AMBIGUOUS (no output - see report)"
            print(f"[{i}/{len(files)}] {path.name}: {tag}")
        except Exception as exc:  # keep batch alive
            import traceback
            traceback.print_exc()
            all_rows = [r for r in all_rows if r.get("input") != path.name]
            all_rows.append({"input": path.name, "status": f"error: {exc}"})
            print(f"[{i}/{len(files)}] ERROR {path.name}: {exc}")
        write_report_csv(report_path, all_rows)

    # drop stale item outputs from earlier runs (e.g. items that turned
    # ambiguous later would otherwise keep their old PNG around)
    ok_outputs = {r.get("output") for r in all_rows if r.get("status") == "ok"}
    for p in sorted(out_dir.glob("*.png")):
        if p.name in ok_outputs or p.stem.endswith("_contact"):
            continue
        p.unlink()
        print(f"removed stale output: {p.name}")

    review_needed = sorted({r["input"] for r in all_rows
                            if str(r.get("status", "")).startswith("ambiguous")})
    errors = sorted({r["input"] for r in all_rows
                     if str(r.get("status", "")).startswith("error")})
    if review_needed:
        print(f"\nREVIEW REQUIRED ({len(review_needed)}): ambiguous items, no PNG written:")
        for name in review_needed:
            print(f"  - {name}  (reason: {next((r.get('reason') for r in all_rows if r.get('input') == name and r.get('status') == 'ambiguous'), '')})")
        print("  -> inspect output/*_contact.png and output/review/*, then re-run with "
              "--orient STEM_N=180 and/or --cls-margin to resolve.")
    if errors:
        print(f"\nFAILED ({len(errors)}): {', '.join(errors)}")
    print(f"done. report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
