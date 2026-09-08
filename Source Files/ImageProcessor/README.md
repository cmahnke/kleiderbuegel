# Cutlery & Coat Hanger Extractor

Batch pipeline for photos of cutlery and coat hangers: detects every item in each
photo, removes the background, and writes one transparent PNG per item, rotated
upright (cutlery vertical, hanger horizontal with the hook up). Items the pipeline
cannot decide confidently (hand occlusion, image-edge clipping, uncertain
orientation/class) are **not** written — they are reported as ambiguous instead of
guessed.

## Quick start

```bash
# 1. one-time: create .venv and install dependencies (needs Python 3.12)
./setup.sh

# 2. one-time: pre-download all models into models/ (~2.6 GB)
./.venv/bin/python download_models.py

# 3. put your photos here (HEIC or JPEG, any number of items per photo)
#    -> test_images/

# 4. run
./.venv/bin/python -m pipeline test_images output --review
```

Models also auto-download on first use if step 2 is skipped. Re-running the same
command resumes: already-finished images are skipped, edited code or new/changed
photos are processed.

## Results

| File | Content |
|---|---|
| `output/<stem>_<n>_<class>.png` | one transparent RGBA crop per item (8-bit, `--depth 16` optional) |
| `output/<stem>_contact.png` | thumbnail sheet of all items in that photo |
| `output/report.csv` | per-item record: class, scores, margins, status, reason |
| `output/review/<stem>_<n>_review.png` | side-by-side both-orientation sheet |
| `output/<stem>.json` | full metadata (detections, enhance info, orientation scores) |

## Ambiguous items ("REVIEW REQUIRED")

Ambiguous items get **no PNG** — check the reason (console or `report.csv`), then:

- **wrong orientation** → re-run with a manual flip:
  `--orient IMG_6133_1=0` (degrees are `0` or `180`, keyed by `<stem>_<item#>`)
- **class uncertain** → lower the gate: `--cls-margin 0.05`
- **hand occlusion / clipped at edge** → crop the photo or accept the loss

Then re-run; finished images are not recomputed.

## Useful flags

```
--detector yoloe|yolo-world|dino|yolo-custom   detector (default: yoloe, most accurate)
--segmenter birefnet-general|bria-rmbg|isnet-general-use
--conf 0.15          detection confidence
--margin 3           crop margin in px
--depth 16           16-bit PNG output
--no-exif-rotate     ignore EXIF orientation (metadata is only a hint by default)
--no-clip            disable CLIP orientation/class decisions (faster, less accurate)
--no-human           skip hand-mask subtraction (faster, hands will stick to items)
--occlusion-limit 0.35  max hand-occluded fraction of an item
--orient STEM_N=180  manual flip override (repeatable)
--force              reprocess everything
--debug              dump stage checkpoints to tmp/
```

## Requirements

- macOS on Apple Silicon (MPS) — developed and validated on M1 Max
- Python 3.12 (`brew install python@3.12`); `./setup.sh` falls back to `python3`
- ~50–65 s per photo on an M1 Max (segmentation runs on CPU by design — see
  PROGRESS.md "Known issues")

## Custom detector (optional)

If zero-shot detection misses your objects, `train.py` can fine-tune a YOLO model
on auto-labeled copies of your own photos and the pipeline can use it via
`--detector yolo-custom` — see `python train.py --help`.
