#!/usr/bin/env bash
# lewitt — pack any skill directory into an upload-ready zip (WorkBuddy / SKILL.md hosts).
#
#   bash scripts/pack-skill.sh <skill-dir> [--out <path>]
#
# Rules enforced (the open platform rejects packages that break them):
#   - zip root is <skill-name>/ ; levels are root / one directory / file, nothing deeper
#   - SKILL.md has the required frontmatter fields
#   - < 3 MB (the platform's hard limit)
set -euo pipefail

SRC="${1:?usage: pack-skill.sh <skill-dir> [--out <path>]}"
SRC="$(cd "$SRC" && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# The platform uses SKILL.md's `name:` as the package directory.
NAME="$(sed -n 's/^name: *//p' "$SRC/SKILL.md" 2>/dev/null | head -1 | tr -d "\"'")"
NAME="${NAME:-$(basename "$SRC")}"
OUT="${3:-$(dirname "$SRC")/$NAME.zip}"
[ "${2:-}" = "--out" ] && OUT="$3"
mkdir -p "$STAGE/$NAME"
rsync -a --exclude .DS_Store --exclude __pycache__ --exclude '*.pyc' \
  --exclude node_modules --exclude .git --exclude dist "$SRC/" "$STAGE/$NAME/"

python3 - "$STAGE/$NAME" "$OUT" <<'PY'
import pathlib, sys, yaml
root, out = pathlib.Path(sys.argv[1]), sys.argv[2]
probs = []
for p in root.rglob("*"):
    depth = len(p.relative_to(root).parts)
    if p.is_file() and depth > 2:
        probs.append(f"too deep: {p.relative_to(root)}")
    if p.is_dir() and depth > 1:
        probs.append(f"nested dir: {p.relative_to(root)}")
skill = root / "SKILL.md"
if not skill.exists():
    probs.append("missing SKILL.md")
else:
    text = skill.read_text()
    if not text.startswith("---"):
        probs.append("SKILL.md has no frontmatter")
    else:
        d = yaml.safe_load(text.split("---", 2)[1]) or {}
        need = ["name", "display_name", "display_name_en", "description",
                "description_zh", "description_en", "version", "author"]
        probs += [f"frontmatter missing: {k}" for k in need if not d.get(k)]
        for key in ("examples_zh", "examples_en"):
            v = d.get(key)
            if v is not None and not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
                probs.append(f"{key} must be a list of strings")
if probs:
    sys.exit("FAIL:\n  " + "\n  ".join(probs))
PY

rm -f "$OUT"
cd "$STAGE"
zip -qr "$OUT" "$NAME"
SIZE=$(stat -f%z "$OUT" 2>/dev/null || stat -c%s "$OUT")
if [ "$SIZE" -ge 3145728 ]; then
  echo "FAIL: $(($SIZE / 1024)) KB >= 3 MB" >&2
  exit 1
fi
echo "$OUT ($(($SIZE / 1024)) KB, $(unzip -l "$OUT" | tail -1 | awk '{print $2}') files)"
