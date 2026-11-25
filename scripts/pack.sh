#!/usr/bin/env bash
# lewitt — build the shareable skill zip (WorkBuddy and any other SKILL.md host).
#
#   bash scripts/pack.sh            # -> dist/lewitt-<version>.zip   (slim, default)
#   bash scripts/pack.sh --full     # all four runs/ with screenshots (for the repo only)
#
# The zip root is `lewitt/` itself, so unzipping it into a skills folder is already the install.
# Slim pack keeps one run (runs/stripe.com) and strips what a reader does not need: capture
# DOM dumps, the run's own preview.html/system pages (re-rendered from dna.json), fidelity
# screenshots and clip shots. Target: well under the open platform's 3 MB upload limit.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(sed -n 's/^version: *//p' "$ROOT/SKILL.md" | head -1 | tr -d "\"'")"
FULL=0
[ "${1:-}" = "--full" ] && FULL=1
SUFFIX=""; if [ $FULL = 1 ]; then SUFFIX="-full"; fi
OUT="$ROOT/dist/lewitt-${VERSION:-dev}${SUFFIX}.zip"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$STAGE/lewitt"
tar -C "$ROOT" -cf - \
  --exclude=.git --exclude=node_modules --exclude=docs --exclude=dist --exclude=__pycache__ \
  --exclude='.DS_Store' --exclude='*/__pycache__' --exclude='*.pyc' --exclude=.dd --exclude=.playwright-cli \
  SKILL.md README.md README.zh-CN.md LICENSE Makefile dna.schema.json \
  scripts references evals runs \
  | tar -C "$STAGE/lewitt" -xf -

if [ $FULL = 0 ]; then
  rm -rf "$STAGE/lewitt/runs"
  mkdir -p "$STAGE/lewitt/runs"
  rsync -a --exclude .DS_Store --exclude __pycache__ "$ROOT/runs/stripe.com" "$STAGE/lewitt/runs/"
  find "$STAGE/lewitt/runs" -name dom.json -o -name 'dom-*.json' -o -name fullpage.png -o -name rebuild.png \
    -o -path '*/clips/*/shots/*' | xargs rm -f
  # PNG screenshots -> JPEG keeps the evidence viewable without the size.
  python3 - "$STAGE/lewitt" <<'PY'
import sys, pathlib
from PIL import Image
root = pathlib.Path(sys.argv[1])
for p in list(root.rglob("*.png")):
    try:
        Image.open(p).convert("RGB").save(p.with_suffix(".jpg"), quality=72, optimize=True)
        p.unlink()
    except Exception:
        pass
PY
fi

# Offline smoke test on the staged copy: scripts run, the bundled dna.json passes every gate
# (renders are rebuilt first, so the stripped pages are regenerated from the SSOT).
python3 "$STAGE/lewitt/scripts/build_artifacts.py" "$STAGE/lewitt/runs/stripe.com" >/dev/null
python3 "$STAGE/lewitt/scripts/lint_output.py" --dest "$STAGE/lewitt/runs/stripe.com" >/dev/null
rm -rf "$STAGE"/lewitt/scripts/__pycache__   # created by the smoke test

mkdir -p "$ROOT/dist"
rm -f "$OUT"
cd "$STAGE"
zip -qr "$OUT" lewitt
echo "$OUT"
