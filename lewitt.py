#!/usr/bin/env python3
"""lewitt — one entry for every command in SKILL.md.

The skill ships flat (SKILL.md + scripts at the top level), so the docs call this file directly:

    python3 "$SKILL/lewitt.py" <command> ...

    extract <url>          browser capture            -> scripts/capture.py
    render <run>           dna.json -> artifacts      -> scripts/build_artifacts.py
    check --dest <run>     gates                     -> scripts/lint_output.py
    clip --url <url> ...   lift one block            -> scripts/clip.py
    certify --url <url> --dest <run>                 -> scripts/cert.py
    setup                  playwright + chromium     -> scripts/setup.sh

`render`/`clip` without a command work too: `lewitt.py <path>` renders, and
`lewitt.py --url ... --find ...` clips. Every argument is passed through untouched.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

COMMANDS = {
    "extract": ("scripts/capture.py", "sense: capture a URL"),
    "render": ("scripts/build_artifacts.py", "dna.json -> taste.md, tokens.css, agent-rules.md, ..."),
    "check": ("scripts/lint_output.py", "run the gates"),
    "clip": ("scripts/clip.py", "lift one block or micro-interaction"),
    "certify": ("scripts/cert.py", "audit a running build against dna.json"),
}


def helptext() -> str:
    lines = ["usage: lewitt.py <command> [args...]", "", "commands:"]
    lines += [f"  {k:<9} {d}" for k, (_, d) in COMMANDS.items()]
    lines += ["  setup     install playwright + chromium (scripts/setup.sh)", ""]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(helptext())
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "setup":
        return subprocess.call(["bash", str(HERE / "scripts" / "setup.sh"), *rest])
    if cmd not in COMMANDS:
        # Back-compat: a bare path renders, --url clips.
        if cmd.startswith("-"):
            cmd, rest = "clip", argv
        elif Path(cmd).exists() or cmd.endswith(".json"):
            cmd, rest = "render", argv
        else:
            print(f"lewitt: unknown command {cmd!r}\n\n{helptext()}", file=sys.stderr)
            return 2
    script = HERE / COMMANDS[cmd][0]
    return subprocess.call([sys.executable, str(script), *rest])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
