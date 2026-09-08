"""Object detection: YOLO-World (primary, MPS) with optional Grounding-DINO (HF).

Prompts cover coat hangers and cutlery; labels are normalised to 'cutlery' | 'hanger'.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ._env import DETECTORS_DIR, ensure_env_dirs

ensure_env_dirs()

PROMPTS: list[str] = [
    "coat hanger",
    "clothes hanger",
    "wooden coat hanger",
    "wooden clothes hanger",
    "fork",
    "knife",
    "spoon",
    "cutlery",
]
CUTLERY_WORDS = {"fork", "knife", "spoon", "cutlery", "cutlery item", "silverware"}
HANGER_WORDS = {"coat hanger", "clothes hanger", "hanger"}


@dataclass
class Detection:
    bbox: tuple[int, int, int, int]  # xyxy, original image coords
    label: str  # raw prompt label
    cls: str    # 'cutlery' | 'hanger' | 'unknown'
    score: float


def normalize_class(label: str) -> str:
    l = label.lower()
    if any(w in l for w in CUTLERY_WORDS):
        return "cutlery"
    if any(w in l for w in HANGER_WORDS):
        return "hanger"
    return "unknown"


def _ensure_ultralytics_weights(filename: str) -> Path:
    target = DETECTORS_DIR / filename
    if not target.exists():
        from ultralytics.utils.downloads import attempt_download_asset
        attempt_download_asset(str(target))
    return target


CUSTOM_WEIGHTS = DETECTORS_DIR / "custom_cutlery_hanger.pt"
YOLOE_PE = DETECTORS_DIR / "yoloe-pe.npz"


class Detector:
    def __init__(self, backend: str = "yolo-world", device: str = "auto",
                 dino_model: str = "IDEA-Research/grounding-dino-tiny",
                 yoloe_weights: str = "yoloe-26x-seg.pt",
                 yoloe_pe: Path | None = None):
        self.backend = backend
        if device == "auto":
            import torch
            device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.device = device
        self._yolo = None
        self._dino = None
        self._dino_name = dino_model
        self._yoloe = None
        self._yoloe_name = yoloe_weights
        self._yoloe_pe = yoloe_pe

    # ---------- YOLO-World ----------
    def _load_yolo(self):
        if self._yolo is not None:
            return
        import torch
        from ultralytics import YOLOWorld
        weights = _ensure_ultralytics_weights("yolov8s-worldv2.pt")
        model = YOLOWorld(str(weights), verbose=False)
        model.set_classes(PROMPTS)
        self._yolo = model

    def _detect_yolo(self, rgb: np.ndarray, conf: float, imgsz: int) -> list[Detection]:
        self._load_yolo()
        img_u8 = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
        bgr = np.ascontiguousarray(img_u8[..., ::-1])  # ultralytics expects BGR numpy
        results = self._yolo.predict(bgr, conf=conf, imgsz=imgsz, device=self.device,
                                     verbose=False, retina_masks=False)
        out: list[Detection] = []
        for r in results:
            names = r.names
            for box, cls_id, score in zip(r.boxes.xyxy.cpu().numpy(),
                                          r.boxes.cls.cpu().numpy().astype(int),
                                          r.boxes.conf.cpu().numpy()):
                label = names.get(cls_id, str(cls_id))
                x1, y1, x2, y2 = [int(round(v)) for v in box]
                out.append(Detection((x1, y1, x2, y2), label, normalize_class(label), float(score)))
        return out

    # ---------- YOLOE26 (open-vocabulary, successor to YOLO-World) ----------
    def _load_yoloe(self):
        if self._yoloe is not None:
            return
        import torch  # noqa: F401
        from ultralytics import YOLOE
        pe_path = self._yoloe_pe or YOLOE_PE
        if not pe_path.exists():
            raise FileNotFoundError(
                f"YOLOE prompt embeddings missing: {pe_path} — build them with "
                f"`python -m pipeline.calibrate <exemplars.json>` first "
                f"(text prompts alone are unreliable on this model)")
        model = YOLOE(str(_ensure_ultralytics_weights(self._yoloe_name)), verbose=False)
        model.load_prompt_embeddings(str(pe_path))
        self._yoloe = model

    def _detect_yoloe(self, rgb: np.ndarray, conf: float, imgsz: int,
                      with_masks: bool = False):
        self._load_yoloe()
        img_u8 = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
        # NOTE: RGB on purpose (not BGR): the prompt embeddings are calibrated in
        # the flipped domain (calibrate._preprocess); the predictor's BGR->RGB
        # flip then presents every image in that same domain. Empirically this
        # pairing scores ~0.9 vs ~0.5 for the BGR pairing on our photos.
        results = self._yoloe.predict(img_u8, conf=conf, imgsz=imgsz, device=self.device,
                                      verbose=False, retina_masks=with_masks)
        dets: list[Detection] = []
        masks: list[np.ndarray] = []
        for r in results:
            names = r.names
            raw_masks = None
            if with_masks and r.masks is not None:
                raw_masks = r.masks.data.cpu().numpy().astype(bool)
            for j, (box, cls_id, score) in enumerate(zip(r.boxes.xyxy.cpu().numpy(),
                                                         r.boxes.cls.cpu().numpy().astype(int),
                                                         r.boxes.conf.cpu().numpy())):
                label = names.get(cls_id, str(cls_id))
                x1, y1, x2, y2 = [int(round(v)) for v in box]
                dets.append(Detection((x1, y1, x2, y2), label, normalize_class(label), float(score)))
                if raw_masks is not None:
                    m = raw_masks[j]
                    masks.append(m[:rgb.shape[0], :rgb.shape[1]])
        if with_masks:
            return dets, masks
        return dets

    # ---------- YOLO (plain fine-tuned) ----------
    def _load_yolo_custom(self):
        if self._yolo is not None:
            return
        import torch
        from ultralytics import YOLO
        if not CUSTOM_WEIGHTS.exists():
            raise FileNotFoundError(
                f"no custom weights at {CUSTOM_WEIGHTS} — run `python train.py` first")
        self._yolo = YOLO(str(CUSTOM_WEIGHTS), verbose=False)

    def _detect_yolo_custom(self, rgb: np.ndarray, conf: float, imgsz: int) -> list[Detection]:
        self._load_yolo_custom()
        img_u8 = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
        bgr = np.ascontiguousarray(img_u8[..., ::-1])
        results = self._yolo.predict(bgr, conf=conf, imgsz=imgsz, device=self.device,
                                     verbose=False)
        out: list[Detection] = []
        for r in results:
            names = r.names
            for box, cls_id, score in zip(r.boxes.xyxy.cpu().numpy(),
                                          r.boxes.cls.cpu().numpy().astype(int),
                                          r.boxes.conf.cpu().numpy()):
                label = names.get(cls_id, str(cls_id))
                x1, y1, x2, y2 = [int(round(v)) for v in box]
                out.append(Detection((x1, y1, x2, y2), label, normalize_class(label), float(score)))
        return out

    # ---------- Grounding DINO (optional fallback) ----------
    def _load_dino(self):
        if self._dino is not None:
            return
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
        proc = AutoProcessor.from_pretrained(self._dino_name)
        model = AutoModelForZeroShotObjectDetection.from_pretrained(self._dino_name)
        model.to(self.device)
        model.eval()
        self._dino = (proc, model)

    def _detect_dino(self, rgb: np.ndarray, conf: float) -> list[Detection]:
        import torch
        from PIL import Image as PILImage
        self._load_dino()
        proc, model = self._dino
        img_u8 = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
        pil = PILImage.fromarray(img_u8, "RGB")
        text = ". ".join(PROMPTS) + "."
        inputs = proc(images=pil, text=text, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = model(**inputs)
        results = proc.post_process_grounded_object_detection(
            outputs, input_ids=inputs.input_ids,
            threshold=conf, text_threshold=0.25,
            target_sizes=[pil.size[::-1]])[0]
        out: list[Detection] = []
        for box, score, label in zip(results["boxes"].cpu().numpy(),
                                     results["scores"].cpu().numpy(),
                                     results["text_labels"]):
            x1, y1, x2, y2 = [int(round(v)) for v in box]
            out.append(Detection((x1, y1, x2, y2), str(label), normalize_class(str(label)), float(score)))
        return out

    # ---------- public ----------
    def detect(self, rgb: np.ndarray, conf: float = 0.15, imgsz: int = 1024) -> list[Detection]:
        if self.backend == "dino":
            dets = self._detect_dino(rgb, conf)
        elif self.backend == "yolo-custom":
            dets = self._detect_yolo_custom(rgb, conf, imgsz)
        elif self.backend == "yoloe":
            dets = self._detect_yoloe(rgb, conf, imgsz)
        else:
            dets = self._detect_yolo(rgb, conf, imgsz)
        return _nms_dedupe(dets)

    def detect_with_masks(self, rgb: np.ndarray, conf: float = 0.15,
                          imgsz: int = 1024):
        """yoloe backend: detections + full-resolution retina masks (seg comparison)."""
        dets, masks = self._detect_yoloe(rgb, conf, imgsz, with_masks=True)
        kept_d, kept_m = [], []
        for d, m in sorted(zip(dets, masks), key=lambda dm: dm[0].score, reverse=True):
            if all(_iou(d.bbox, k.bbox) < 0.55 for k in kept_d):
                kept_d.append(d)
                kept_m.append(m)
        return kept_d, kept_m


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1, ix2, iy2 = max(ax1, bx1), max(ay1, by1), min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / max(area_a + area_b - inter, 1e-6)


def _nms_dedupe(dets: list[Detection], iou_thr: float = 0.55) -> list[Detection]:
    dets = sorted(dets, key=lambda d: d.score, reverse=True)
    kept: list[Detection] = []
    for d in dets:
        if all(_iou(d.bbox, k.bbox) < iou_thr for k in kept):
            kept.append(d)
    return kept
