#!/usr/bin/env bash
# Creates a Python 3.12 venv and installs all dependencies.
set -euo pipefail
cd "$(dirname "$0")"

PY=python3.12
if ! command -v "$PY" >/dev/null 2>&1; then
  PY=python3
  if ! "$PY" -c 'import sys; assert sys.version_info[:2] == (3,12)' 2>/dev/null; then
    echo "python3.12 not found (brew install python@3.12)" >&2; exit 1
  fi
fi

if [ ! -d .venv ]; then
  "$PY" -m venv .venv
  ./.venv/bin/pip install --upgrade pip wheel setuptools
fi
./.venv/bin/pip install -r requirements.txt
echo "OK: .venv ready — run ./.venv/bin/python download_models.py"
