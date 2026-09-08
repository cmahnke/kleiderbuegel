"""Splitting: detection boxes x mask connected components -> one alpha mask per item."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .detect import Detection


@dataclass
class Item:
    alpha: np.ndarray            # full-image-size float32 mask of this single item
    cls: str                     # 'cutlery' | 'hanger' | 'unknown'
    source: str                  # 'detection' | 'component' | 'component-forced-split'
    score: float                 # detection confidence if any
    label: str = ""
    edge_clipped: bool = False   # component touches the image edge (partial object)
    notes: list[str] = field(default_factory=list)


def _components(bin_mask: np.ndarray):
    import cv2
    m = (bin_mask > 0).astype(np.uint8)
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(m, connectivity=8)
    return labels, stats, centroids, n


def _box_of(mask: np.ndarray):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def _center_dist_to_box(px, py, box) -> float:
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    return float(np.hypot(px - cx, py - cy))


def _iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / float(area_a + area_b - inter)


def split_items(alpha: np.ndarray, detections: list[Detection],
                min_comp_area: int = 400,
                classify_whole=None) -> list[Item]:
    """Decompose the cleaned alpha into individual items.

    - A component claimed by several boxes is first checked WHOLE with
      `classify_whole` (CLIP): if it confidently says 'hanger', the scattered
      weak boxes lie on one hanger body -> one item, no split.
    - Otherwise, components claimed by several disjoint boxes (pairwise IoU
      < 0.3, each covering >= 0.2 of the component) are force-split by nearest
      box center (side-by-side cutlery). Overlapping duplicate boxes on ONE
      object are merged into a single item instead.
    - Mask components not covered by any box become extra items (detection
      misses). With no detections at all, all components become 'unknown'.
    """
    import cv2

    bin_mask = alpha >= 0.15
    if not bin_mask.any():
        return []

    labels, stats, centroids, n = _components(bin_mask)
    comps = []
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < min_comp_area:
            continue
        comps.append({
            "id": i,
            "area": area,
            "centroid": (float(centroids[i][0]), float(centroids[i][1])),
        })

    if not comps:
        return []

    items: list[Item] = []
    used_comp_ids: set[int] = set()

    if detections:
        claimed: dict[int, list[int]] = {}  # comp id -> detection indices
        for di, det in enumerate(detections):
            for c in comps:
                px, py = c["centroid"]
                if _center_dist_to_box(px, py, det.bbox) <= 0 or _box_intersects_centroid(det.bbox, px, py):
                    claimed.setdefault(c["id"], []).append(di)

        # components with no detection whose centroid lies inside: fall back to
        # largest-overlap assignment (box may be offset)
        for c in comps:
            if c["id"] in claimed:
                continue
            best, best_area = None, 0
            for di, det in enumerate(detections):
                x1, y1, x2, y2 = det.bbox
                comp_mask = labels == c["id"]
                inter = int(comp_mask[y1:y2, x1:x2].sum())
                if inter > best_area:
                    best, best_area = di, inter
            if best is not None and best_area > 0.15 * c["area"]:
                claimed.setdefault(c["id"], []).append(best)

        for det_idx, det in enumerate(detections):
            owning = [c for c in comps if det_idx in claimed.get(c["id"], [])]
            if not owning:
                continue
            if len(owning) == 1 and len(claimed.get(owning[0]["id"], [])) == 1:
                c = owning[0]
                item_mask = (labels == c["id"]).astype(np.float32) * alpha
                items.append(Item(item_mask, det.cls, "detection", det.score,
                                  det.label, notes=[f"comp{c['id']}"]))
                used_comp_ids.add(c["id"])
            else:
                # box contains several components -> each its own item
                multi_comp = len(owning) > 1
                for c in owning:
                    if multi_comp and len(claimed.get(c["id"], [])) == 1:
                        comp_mask = (labels == c["id"])
                        item_mask = comp_mask.astype(np.float32) * alpha
                        items.append(Item(item_mask, det.cls, "detection", det.score,
                                          det.label, notes=[f"comp{c['id']}"]))
                        used_comp_ids.add(c["id"])

        # components claimed by several boxes: merge or force-split
        for c in comps:
            if c["id"] in used_comp_ids or c["id"] not in claimed:
                continue
            claimers = claimed[c["id"]]
            comp_mask = (labels == c["id"])
            comp_area = float(comp_mask.sum())
            if len(claimers) == 1:
                continue  # handled in the per-detection loop above
            if classify_whole is not None and len(claimers) > 1:
                whole = classify_whole(comp_mask)
                if whole == "hanger":
                    # scattered weak boxes along ONE hanger body -> no split
                    best = max(claimers, key=lambda i: detections[i].score)
                    d = detections[best]
                    item_mask = comp_mask.astype(np.float32) * alpha
                    items.append(Item(item_mask, "hanger", "detection", d.score,
                                      d.label, notes=[f"comp{c['id']}",
                                                      f"merged-{len(claimers)}-boxes",
                                                      "whole-comp-clip=hanger"]))
                    used_comp_ids.add(c["id"])
                    continue
                if whole is None:
                    # uncertain -> do NOT split; let the orient stage decide the
                    # class of the whole component (fail-over-guess principle)
                    item_mask = comp_mask.astype(np.float32) * alpha
                    items.append(Item(item_mask, "unknown", "component", 0.0,
                                      notes=[f"comp{c['id']}",
                                             f"merged-{len(claimers)}-boxes",
                                             "whole-comp-clip=uncertain"]))
                    used_comp_ids.add(c["id"])
                    continue
                # whole == 'cutlery' -> fall through to split logic
            boxes = [detections[i].bbox for i in claimers]
            pairwise_ok = all(_iou(boxes[i], boxes[j]) < 0.3
                              for i in range(len(boxes))
                              for j in range(i + 1, len(boxes)))
            covers = []
            for x1, y1, x2, y2 in boxes:
                covers.append(comp_mask[y1:y2, x1:x2].sum() / comp_area)
            disjoint = pairwise_ok and all(cv_ >= 0.2 for cv_ in covers)
            best = max(claimers, key=lambda i: detections[i].score)
            if disjoint:
                # genuinely multiple objects -> force-split by nearest box center
                ys, xs = np.nonzero(comp_mask)
                d2 = np.stack([((xs - (detections[i].bbox[0] + detections[i].bbox[2]) / 2) ** 2 +
                                (ys - (detections[i].bbox[1] + detections[i].bbox[3]) / 2) ** 2)
                               for i in claimers], axis=0)
                nearest = np.argmin(d2, axis=0)
                for k, det_idx in enumerate(claimers):
                    sel = nearest == k
                    if sel.sum() < 50:
                        continue
                    m = np.zeros_like(comp_mask)
                    m[ys[sel], xs[sel]] = True
                    item_mask = m.astype(np.float32) * alpha
                    items.append(Item(item_mask, detections[det_idx].cls,
                                      "component-forced-split",
                                      detections[det_idx].score,
                                      detections[det_idx].label,
                                      notes=[f"comp{c['id']}", "split-by-box-center"]))
                    used_comp_ids.add(c["id"])
            else:
                # overlapping boxes on one object -> single item, best-scoring box
                d = detections[best]
                item_mask = comp_mask.astype(np.float32) * alpha
                items.append(Item(item_mask, d.cls, "detection", d.score, d.label,
                                  notes=[f"comp{c['id']}",
                                         f"merged-{len(claimers)}-boxes"]))
                used_comp_ids.add(c["id"])

        # leftover components (detection misses)
        for c in comps:
            if c["id"] in used_comp_ids:
                continue
            comp_mask = (labels == c["id"])
            cls = _infer_class(comp_mask)
            item_mask = comp_mask.astype(np.float32) * alpha
            items.append(Item(item_mask, cls, "component", 0.0,
                              notes=[f"comp{c['id']}", "no-detection"]))
    else:
        for c in comps:
            comp_mask = (labels == c["id"])
            cls = _infer_class(comp_mask)
            item_mask = comp_mask.astype(np.float32) * alpha
            items.append(Item(item_mask, cls, "component", 0.0,
                              notes=[f"comp{c['id']}"]))

    result = [it for it in items if it.alpha.sum() > 50]
    h, w = alpha.shape
    for it in result:
        ys, xs = np.nonzero(it.alpha > 0)
        it.edge_clipped = bool(ys.min() == 0 or xs.min() == 0
                               or ys.max() == h - 1 or xs.max() == w - 1)
    return result


def _box_intersects_centroid(box, px: float, py: float) -> bool:
    x1, y1, x2, y2 = box
    return x1 - 0.05 * (x2 - x1) <= px <= x2 + 0.05 * (x2 - x1) and \
        y1 - 0.05 * (y2 - y1) <= py <= y2 + 0.05 * (y2 - y1)


def _infer_class(comp_mask: np.ndarray) -> str:
    """No-detection components: class is decided visually by the orient stage (CLIP
    4-way scoring), so return 'unknown' here."""
    return "unknown"
