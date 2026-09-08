"""Which-end-is-up + class decisions: CLIP (visual) with heuristic fallback.

Never uses metadata. Works on the axis-aligned RGBA item; chooses 0 vs 180 deg,
verifies/re-decides the class (cutlery vs hanger), and reports decision margins
so the pipeline can FAIL ambiguous items instead of guessing.
"""

from __future__ import annotations

import sys

import numpy as np

_CLIP_NAME = "openai/clip-vit-large-patch14-336"
_clip_model = None
_clip_processor = None
_clip_device = None

_CUTLERY_WORDS = ["fork", "knife", "spoon", "piece of cutlery"]

_CLASS_PROMPTS: dict[str, tuple[list[str], list[str]]] = {
    "cutlery": (
        [f"a photo of a {w} standing upright with its head pointing up and handle at the bottom"
         for w in _CUTLERY_WORDS],
        [f"a photo of a {w} upside down with its head pointing down and handle at the top"
         for w in _CUTLERY_WORDS],
    ),
    "hanger": (
        ["a photo of a coat hanger with the hook at the top",
         "a coat hanger hanging normally, hook pointing up",
         "a wooden coat hanger standing upright with its metal hook at the top",
         "a clothes hanger oriented correctly with the hook on top"],
        ["a photo of a coat hanger upside down with the hook at the bottom",
         "a coat hanger hanging upside down, hook pointing down",
         "a wooden coat hanger standing upside down with its metal hook at the bottom",
         "a clothes hanger oriented upside down with the hook at the bottom"],
    ),
}


def _load_clip(device: str):
    global _clip_model, _clip_processor, _clip_device
    if _clip_model is not None:
        return
    import torch
    from transformers import CLIPModel, CLIPProcessor
    _clip_processor = CLIPProcessor.from_pretrained(_CLIP_NAME)
    _clip_model = CLIPModel.from_pretrained(_CLIP_NAME).to(device).eval()
    _clip_device = device
    _ = torch


def clip_class_scores(rgb: np.ndarray, alpha: np.ndarray, device: str
                      ) -> dict[str, tuple[float, float]]:
    """Per class: (score orientation 0, score orientation 180). Uses both image
    variants consistently (variant 0 with 'up' prompts + variant 1 with 'down')."""
    import torch
    from PIL import Image as PILImage

    variants = [rgb, rgb[::-1, ::-1]]
    imgs = []
    for v in variants:
        a = np.clip(alpha[..., None], 0.0, 1.0)
        comp = np.clip(v * a + 1.0 * (1.0 - a), 0.0, 1.0)
        imgs.append(PILImage.fromarray(
            np.clip(comp * 255.0 + 0.5, 0, 255).astype(np.uint8), "RGB"))

    texts: list[str] = []
    spans: dict[str, tuple[int, int]] = {}
    for cls, (up, down) in _CLASS_PROMPTS.items():
        spans[cls] = (len(texts), len(texts) + len(up) + len(down))
        texts.extend(up + down)

    _load_clip(device)
    inputs = _clip_processor(text=texts, images=imgs, return_tensors="pt",
                             padding=True).to(_clip_device)
    with torch.no_grad():
        out = _clip_model(**inputs)
    logits = out.logits_per_image.float().cpu().numpy()  # [2 variants, n_texts]

    scores: dict[str, tuple[float, float]] = {}
    for cls, (s0, s1) in spans.items():
        n_up = (s1 - s0) // 2
        up = float(logits[0, s0:s0 + n_up].mean() + logits[1, s0 + n_up:s1].mean())
        down = float(logits[0, s0 + n_up:s1].mean() + logits[1, s0:s0 + n_up].mean())
        scores[cls] = (up, down)
    return scores


def heuristic_pick_upright(alpha: np.ndarray, cls: str | None) -> tuple[int, bool]:
    """Shape fallback. Returns (flip_deg, decided). Only decides when the silhouette
    top/bottom thirds differ clearly (hook end of a hanger is much narrower)."""
    import cv2
    bin_mask = (alpha >= 0.5).astype(np.uint8)
    h = bin_mask.shape[0]
    if h < 12:
        return 0, False
    widths = bin_mask.sum(axis=1).astype(np.float32)
    k = max(2, h // 6)
    top, bot = float(widths[:k].mean()), float(widths[-k:].mean())
    if cls == "hanger" and abs(top - bot) > 0.35 * max(top, bot):
        # hook up -> top clearly narrower than the bottom bar
        return (0 if top < bot else 180), True
    return 0, False


def _probs(scores: dict[str, tuple[float, float]]) -> dict[str, dict[str, float]]:
    """Softmax over the 4 (class, orientation) logits -> calibrated probabilities."""
    flat = {f"{c}:{o}": s for c, (up, dn) in scores.items()
            for o, s in (("up", up), ("down", dn))}
    vals = np.array([flat[k] for k in flat], dtype=np.float64)
    e = np.exp(vals - vals.max())
    probs = e / e.sum()
    out: dict[str, dict[str, float]] = {c: {"up": 0.0, "down": 0.0}
                                        for c in scores}
    for (key, _), p in zip(flat.items(), probs):
        c, o = key.split(":")
        out[c][o] = float(p)
    return out


def _vote(flip_clip: int, clip_decided: bool,
          flip_h: int, h_decided: bool) -> tuple[int, bool, str]:
    """CLIP vs shape-heuristic vote.

    Agreement or a single decisive vote wins; confident disagreement is a
    fail-ambiguous signal (the caller drops the item rather than guessing).
    The heuristic is only decisive for hangers, so cutlery keeps CLIP-only.
    """
    if clip_decided and h_decided:
        if flip_clip == flip_h:
            return flip_clip, True, "clip+heuristic"
        return flip_clip, False, "clip-vs-heuristic-disagree"
    if clip_decided:
        return flip_clip, True, "clip"
    if h_decided:
        return flip_h, True, "heuristic"
    return flip_clip, False, "undecided"


def pick_orientation(rgb: np.ndarray, alpha: np.ndarray, cls: str,
                     device: str = "cpu",
                     orient_margin: float = 0.05,
                     cls_margin: float = 0.15) -> dict:
    """Decide 0 vs 180 flip (and class when cls is 'unknown').

    Also verifies the detector's class against CLIP (4-way scoring) and reports
    margins so the caller can reject ambiguous items. For hangers the shape
    heuristic ALWAYS votes: it disagreed confidently with CLIP on real photos
    that CLIP got wrong, so confident disagreement -> undecided (no output).
    """
    try:
        raw = clip_class_scores(rgb, alpha, device)
        used_clip = True
    except Exception as exc:
        print(f"[orient] CLIP unavailable, using shape heuristic: {exc!r}",
              file=sys.stderr)
        used_clip = False
        raw = {}

    if not used_clip:
        flip, decided = heuristic_pick_upright(alpha, cls)
        return {"rgb": rgb, "alpha": alpha, "flip": flip, "flip_decided": decided,
                "method": "heuristic", "scores": {}, "class": cls,
                "class_switch": False, "class_margin": 0.0,
                "orient_margin": 0.0}

    probs = _probs(raw)
    classes = sorted(probs)
    p_class = {c: probs[c]["up"] + probs[c]["down"] for c in classes}

    # class decision: winner vs runner-up
    ranked = sorted(classes, key=lambda c: -p_class[c])
    winner = ranked[0]
    class_margin = (p_class[winner] - p_class[ranked[1]]) if len(ranked) > 1 else 1.0

    if cls == "unknown":
        # orientation within the CLIP winner, cross-voted with the shape heuristic
        p_up, p_dn = probs[winner]["up"], probs[winner]["down"]
        orient_m = abs(p_up - p_dn)
        flip_clip = 0 if p_up >= p_dn else 180
        flip_h, hdec = heuristic_pick_upright(alpha, winner)
        flip, decided, method = _vote(flip_clip, orient_m >= orient_margin,
                                      flip_h, hdec)
        return {"rgb": rgb, "alpha": alpha, "flip": flip, "flip_decided": decided,
                "method": method, "scores": probs, "class": winner,
                "class_switch": False, "class_margin": class_margin,
                "orient_margin": orient_m}

    # known class: keep detector class unless CLIP contradicts it confidently
    class_switch = (winner != cls and class_margin >= cls_margin)
    final_cls = winner if class_switch else cls
    # orientation within the FINAL class, cross-voted with the shape heuristic
    p_up, p_dn = probs[final_cls]["up"], probs[final_cls]["down"]
    orient_m = abs(p_up - p_dn)
    flip_clip = 0 if p_up >= p_dn else 180
    flip_h, hdec = heuristic_pick_upright(alpha, final_cls)
    flip, decided, method = _vote(flip_clip, orient_m >= orient_margin,
                                  flip_h, hdec)
    return {"rgb": rgb, "alpha": alpha, "flip": flip, "flip_decided": decided,
            "method": method, "scores": probs, "class": final_cls,
            "class_switch": class_switch, "class_margin": class_margin,
            "orient_margin": orient_m}


def apply_manual_flip(rgb: np.ndarray, alpha: np.ndarray, flip_deg: int):
    if flip_deg % 360 == 180:
        return rgb[::-1, ::-1].copy(), alpha[::-1, ::-1].copy()
    return rgb, alpha
