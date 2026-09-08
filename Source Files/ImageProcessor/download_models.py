"""Pre-download all models into <project>/models/ so first pipeline run is fast."""

from __future__ import annotations

import sys

from pipeline._env import ensure_env_dirs

ensure_env_dirs()


def step(msg: str) -> None:
    print(f"\n=== {msg} ===", flush=True)


def main() -> int:
    ok = True

    step("torch / MPS check")
    try:
        import torch
        print("torch", torch.__version__, "| mps available:", torch.backends.mps.is_available())
        if torch.backends.mps.is_available():
            x = torch.randn(8, 8, device="mps")
            _ = (x @ x).sum().item()
            print("MPS matmul OK")
    except Exception as exc:
        print(f"WARN torch/MPS: {exc}")
        ok = False

    step("onnxruntime check")
    try:
        import onnxruntime as ort
        print("onnxruntime", ort.__version__, "| providers:", ort.get_available_providers())
    except Exception as exc:
        print(f"WARN onnxruntime: {exc}")
        ok = False

    step("detector: YOLO-World v2 s")
    try:
        from pipeline.detect import _ensure_ultralytics_weights
        w = _ensure_ultralytics_weights("yolov8s-worldv2.pt")
        print("weights:", w)
    except Exception as exc:
        print(f"WARN yolo-world: {exc}")
        ok = False

    step("segmenter: rembg birefnet-general (primary) + bria-rmbg (fallback)")
    try:
        from rembg import new_session
        for model in ("birefnet-general", "bria-rmbg"):
            s = new_session(model)
            print("session ready:", model, "->", s)
            del s
    except Exception as exc:
        print(f"WARN rembg: {exc}")
        ok = False

    step("orientation: CLIP ViT-B/32")
    try:
        from transformers import CLIPModel, CLIPProcessor
        CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        print("CLIP ready")
    except Exception as exc:
        print(f"WARN clip: {exc}")
        ok = False

    print("\nDONE", "OK" if ok else "WITH WARNINGS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
