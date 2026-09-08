"""Persistent segmentation worker process.

Isolates onnxruntime (rembg) from torch in the parent process: on macOS both bundle
libomp and can crash when loaded together. The worker loads the model once and serves
requests: each line on stdin is JSON {"in": path.npy, "out": path.npy}; the input npy
holds the float32 RGB image (H,W,3 in [0,1]); the output npy gets the float32 alpha
(H,W in [0,1]) at full resolution. Everything is lossless (raw float32 .npy).
"""

from __future__ import annotations

import json
import os
import sys

from pipeline._env import ensure_env_dirs

ensure_env_dirs()


def main(default_model: str) -> int:
    import numpy as np
    from PIL import Image as PILImage
    from rembg import new_session, remove

    sessions: dict[str, object] = {}

    def get_session(name: str):
        if name not in sessions:
            sessions[name] = new_session(name)
        return sessions[name]

    session = get_session(default_model)
    print("READY", flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            if req.get("cmd") == "shutdown":
                break
            rgb = np.load(req["in"])
            img_u8 = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
            sess = get_session(req["model"]) if req.get("model") else session
            mask = remove(PILImage.fromarray(img_u8, "RGB"), session=sess, only_mask=True)
            alpha = np.asarray(mask, dtype=np.float32) / 255.0
            np.save(req["out"], alpha)
            print(json.dumps({"ok": True, "out": req["out"]}), flush=True)
        except Exception as exc:
            print(json.dumps({"ok": False, "error": str(exc)}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "birefnet-general"))
