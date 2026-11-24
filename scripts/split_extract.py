#!/usr/bin/env python3
"""Regenerate extract-dom.js + interaction-probe.js from extract.js (single measurement-side source)."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "extract.js").read_text()
marker = "// ---------- interaction probe (phase B) ----------"
if marker not in src:
    raise SystemExit("extract.js lost its interaction probe section")
dom, probe = src.split(marker, 1)
(HERE / "extract-dom.js").write_text(dom.strip() + "\n")
(HERE / "interaction-probe.js").write_text(marker + probe.rstrip() + "\n")
print("split ok: extract-dom.js", len(dom), "bytes; interaction-probe.js", len(probe), "bytes")
