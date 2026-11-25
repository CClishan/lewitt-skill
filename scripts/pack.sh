#!/usr/bin/env bash
# lewitt — build the shareable skill zip (WorkBuddy and any other SKILL.md host).
#
#   bash scripts/pack.sh     # -> dist/lewitt-<version>.zip
#
# The zip is flat — root files + one level of scripts/ and references/ — because the open platform
# rejects deeper nesting and nothing else is allowed at level 2. Layout:
#
#   lewitt/  SKILL.md  lewitt.py  dna.schema.json  README.md  README.zh-CN.md  LICENSE  Makefile
#            scripts/   *.py *.js setup.sh
#            references/ *.md
#
# Not shipped: runs/ (examples live in the repo), evals/ (repo-only), docs/ screenshots,
# node_modules (setup.sh installs it), caches.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(sed -n 's/^version: *//p' "$ROOT/SKILL.md" | head -1 | tr -d "\"'")"
OUT="$ROOT/dist/lewitt-${VERSION:-dev}.zip"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$STAGE/lewitt/scripts" "$STAGE/lewitt/references"
cp "$ROOT"/{SKILL.md,lewitt.py,dna.schema.json,README.md,README.zh-CN.md,LICENSE,Makefile} "$STAGE/lewitt/"
cp "$ROOT"/scripts/*.{py,js,sh} "$STAGE/lewitt/scripts/"
cp "$ROOT"/references/*.md "$STAGE/lewitt/references/"
chmod +x "$STAGE"/lewitt/lewitt.py "$STAGE"/lewitt/scripts/setup.sh

# Gate 1 — layout: exactly root / level-2 dir / file, nothing deeper.
python3 - "$STAGE/lewitt" <<'PY'
import sys, pathlib
root = pathlib.Path(sys.argv[1])
bad = [str(p.relative_to(root)) for p in root.rglob("*")
       if len(p.relative_to(root).parts) > 2 and not p.is_dir()]
bad += [str(p.relative_to(root)) for p in root.rglob("*")
        if p.is_dir() and len(p.relative_to(root).parts) > 1]
if bad:
    sys.exit("layout: nesting too deep: " + ", ".join(bad[:5]))
PY

# Gate 2 — frontmatter has every field the platform requires.
python3 - "$STAGE/lewitt/SKILL.md" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]).read().split("---")[1])
need = ["name", "display_name", "display_name_en", "description", "description_zh",
        "description_en", "version", "author"]
missing = [k for k in need if not d.get(k)]
if missing:
    sys.exit("frontmatter: missing " + ", ".join(missing))
PY

# Gate 3 — the entry point resolves and the scripts still run offline.
python3 "$STAGE/lewitt/lewitt.py" --help >/dev/null
for f in "$STAGE"/lewitt/scripts/*.py; do python3 -c 'import ast,sys; ast.parse(open(sys.argv[1]).read())' "$f"; done
rm -rf "$STAGE"/lewitt/scripts/__pycache__

mkdir -p "$ROOT/dist"
rm -f "$OUT"
cd "$STAGE"
zip -qr "$OUT" lewitt
echo "$OUT"
