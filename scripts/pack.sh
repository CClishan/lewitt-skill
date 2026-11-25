#!/usr/bin/env bash
# lewitt — build the shareable skill zip (WorkBuddy and any other SKILL.md host).
#
#   bash scripts/pack.sh          # -> dist/lewitt-<version>.zip
#
# The zip root is `lewitt/` itself, so unzipping it into a skills folder is already the install.
# Skipped: .git, node_modules (created by setup.sh), docs/ screenshots, caches.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(sed -n 's/^version: *//p' "$ROOT/SKILL.md" | head -1 | tr -d "\"'")"
OUT="$ROOT/dist/lewitt-${VERSION:-dev}.zip"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$STAGE/lewitt"
tar -C "$ROOT" -cf - \
  --exclude=.git --exclude=node_modules --exclude=docs --exclude=dist --exclude=__pycache__ \
  --exclude=.DS_Store --exclude='*.pyc' --exclude=.dd --exclude=.playwright-cli \
  SKILL.md README.md README.zh-CN.md LICENSE Makefile dna.schema.json \
  scripts references evals runs \
  | tar -C "$STAGE/lewitt" -xf -

# Offline smoke test on the staged copy: the scripts must run and the bundled dna.json must pass.
python3 "$STAGE/lewitt/scripts/lint_output.py" --dest "$STAGE/lewitt/runs/stripe.com" >/dev/null

mkdir -p "$ROOT/dist"
rm -f "$OUT"
cd "$STAGE"
zip -qr "$OUT" lewitt
echo "$OUT"
