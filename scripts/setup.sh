#!/usr/bin/env bash
# lewitt — one-time capture dependency setup.
#
# Installs playwright into <skill>/node_modules so a fresh clone works on any machine
# (capture.py looks there first, after LEWITT_PW_DIR).
#
#   bash scripts/setup.sh            # install/refresh playwright + chromium
#   bash scripts/setup.sh --check    # report what would be used, install nothing
#
# Env:
#   LEWITT_PW_DIR   install elsewhere (dir that will hold node_modules/playwright)
#   PLAYWRIGHT_BROWSERS_PATH  honoured by playwright itself
set -euo pipefail

SKILL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${LEWITT_PW_DIR:-$SKILL_ROOT}"
MODE="${1:-install}"

need() { command -v "$1" >/dev/null 2>&1 || { echo "lewitt: '$1' is required" >&2; exit 1; }; }
need node
need npm

# The platform package keeps node_modules out of the upload, and a read-only skill dir cannot hold
# them either: fall back to a per-user cache outside the skill when the skill dir is not writable.
if [ "${1:-}" != "--check" ] && [ "$TARGET" = "$SKILL_ROOT" ] && ! { mkdir -p "$TARGET" && [ -w "$TARGET" ]; } 2>/dev/null; then
  TARGET="${XDG_CACHE_HOME:-$HOME/.cache}/lewitt"
  echo "skill dir is not writable; installing into $TARGET instead"
fi

probe() {
  node -e '
    const dir = process.argv[1];
    try {
      const p = require(dir + "/node_modules/playwright");
      const v = require(dir + "/node_modules/playwright/package.json").version;
      const bin = p.chromium.executablePath();
      const fs = require("fs");
      console.log("playwright " + v + " at " + dir);
      console.log(fs.existsSync(bin) ? "browser: " + bin : "browser: MISSING (" + bin + ")");
    } catch (e) { console.log("not usable: " + e.message.split("\n")[0]); process.exit(1); }
  ' "$TARGET"
}

echo "lewitt setup — target: $TARGET"
if probe 2>/dev/null; then
  echo "already ready."
  [ "$MODE" = "--check" ] && exit 0
else
  [ "$MODE" = "--check" ] && { probe || true; exit 1; }
  echo "installing playwright into $TARGET ..."
  mkdir -p "$TARGET"
  ( cd "$TARGET" && [ -f package.json ] || printf '{"private":true}\n' > package.json
    npm install --no-audit --no-fund playwright@latest )
fi

echo "ensuring a matching chromium build ..."
( cd "$TARGET" && npx playwright install chromium )

probe
cat <<EOF

ready. lewitt finds it automatically, unless you point it elsewhere:
  export LEWITT_PW_DIR=$TARGET
EOF
