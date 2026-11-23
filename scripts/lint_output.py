#!/usr/bin/env python3
"""lewitt — mechanical gates. No mental scanning (R2).

Three gates, one command:
  1. schema     dna.json contract (delegates to build_artifacts.validate)
  2. slop       banned phrases in authored prose, normalized before matching
  3. guardrail  Restraint constraints vs the code you generated (--check-code)

Usage:
  python3 lint_output.py --dest <dest_dir>                      # gates 1+2, writes VERIFY.md
  python3 lint_output.py --dest <dest_dir> --check-code <dir>   # + gate 3 against generated UI
  python3 lint_output.py --dest <dest_dir> --report-only        # print, don't write

Exit codes: 0 pass, 1 fail.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_artifacts as ba  # noqa: E402

# Words that describe nothing. Matched case-insensitively after normalization;
# quoted foils ("they could have gone 'clean and modern', but…") are exempt.
SLOP = [
    "clean", "modern", "sleek", "visually appealing", "user-friendly", "intuitive",
    "seamless", "elegant", "minimalist", "polished", "refined", "sophisticated",
    "delightful", "stunning", "beautiful", "premium",
]
FOIL = re.compile(r"(could have|instead of|rather than|over a|有人会|本可以选择|而没有)", re.IGNORECASE)

CSS_EXTS = {".css", ".scss", ".sass", ".less"}
MARKUP_EXTS = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "__pycache__"}
FREE_UNITS = {"px", "pt", "rem", "em", "%", "ch", "vh", "vw", "ms", "s"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- gate 2
def scan_slop(dna: dict) -> list[dict]:
    hits: list[dict] = []
    targets: list[tuple[str, str]] = []
    for m in dna.get("measurements", []):
        targets.append((f"measurements[{m.get('id')}].value", str(m.get("value", ""))))
    for p in dna.get("patterns", []):
        for k in ("name", "rule", "goal"):
            targets.append((f"patterns[{p.get('id')}].{k}", str(p.get(k, ""))))
    for t in dna.get("taste", []):
        for k in ("name", "trigger", "decision", "reason", "chose", "over"):
            targets.append((f"taste[{t.get('id')}].{k}", str(t.get(k, ""))))
    for where, text in targets:
        for word in SLOP:
            for m in re.finditer(rf"\b{re.escape(word)}\b", text, re.IGNORECASE):
                line_start = text.rfind("\n", 0, m.start()) + 1
                line_end = text.find("\n", m.end())
                line = text[line_start : line_end if line_end != -1 else len(text)]
                if FOIL.search(line) or line.strip().startswith((">", "'", '"', "“", "‘")):
                    continue
                hits.append({"where": where, "word": word, "line": line.strip()[:160]})
    return hits


# ---------------------------------------------------------------- gate 3
def collect_code_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in CSS_EXTS | MARKUP_EXTS:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        files.append(p)
    return files


def parse_decl(text: str) -> tuple[str, str] | None:
    if ":" not in text:
        return None
    prop, value = text.split(":", 1)
    prop = prop.strip().lower()
    value = value.strip().rstrip(";").strip()
    if not prop or not value:
        return None
    return prop, value


def declarations(path: Path) -> list[tuple[int, str, str]]:
    """Layout-agnostic declarations.

    CSS/SCSS: every `prop: value` inside rule blocks and at-rules, comments stripped.
    Markup:   style="…" and style={{ … }} literals only.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    out: list[tuple[int, str, str]] = []
    if path.suffix.lower() in CSS_EXTS:
        stripped = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
        for ln, raw in enumerate(stripped.splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("@") and ":" not in line.split("{")[0]:
                continue
            for part in line.split(";"):
                if "{" in part:
                    part = part.split("{", 1)[1]
                if "}" in part:
                    part = part.split("}", 1)[0]
                d = parse_decl(part)
                if d:
                    out.append((ln, d[0], d[1]))
        return out
    for ln, raw in enumerate(text.splitlines(), 1):
        if "style" not in raw:
            continue
        for block in re.findall(r"style\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|\{\{([^}]*)\}\})", raw):
            body = next((b for b in block if b), "")
            for part in re.split(r"[;,]", body):
                d = parse_decl(part)
                if d:
                    out.append((ln, d[0], d[1]))
    return out


def css_classes(path: Path) -> list[tuple[int, list[str]]]:
    if path.suffix.lower() not in MARKUP_EXTS:
        return []
    out = []
    for ln, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for attr in re.findall(r"class(?:Name)?\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|\{`([^`]*)`\})", raw):
            body = next((a for a in attr if a), "")
            if body:
                out.append((ln, body.split()))
    return out


def parse_length(value: str) -> tuple[float, str] | None:
    m = re.fullmatch(r"(-?\d*\.?\d+)\s*(px|rem|em|pt|%)?", value.strip().lower())
    if not m:
        return None
    unit = m.group(2) or "px"
    return float(m.group(1)), unit


def shadow_lengths(value: str) -> list[tuple[float, str]]:
    """Every geometric length in a shadow. Colour channels are excluded.

    Cap = 0  => pure hairline rings (no offset, no blur, no spread).
    Cap = 32 => a telemetry-style soft float is still allowed.

    `0 0 0 1px #23252A`         -> [0, 0, 0, 1]
    `inset 0 0 0 1px rgba(...)` -> [0, 0, 0, 1]
    `0 4px 12px rgba(0,0,0,.3)` -> [0, 4, 12]
    """
    bare = re.sub(r"(rgba?|hsla?)\([^)]*\)", " ", value.lower()).replace("inset", " ")
    bare = re.sub(r"#[\da-f]{3,8}\b", " ", bare)  # hex colours are not lengths
    lengths = []
    for m in re.finditer(r"(-?\d*\.?\d+)(px|rem|em)?", bare):
        lengths.append((float(m.group(1)), m.group(2) or "px"))
    return lengths


def to_px(num: float, unit: str) -> float:
    return num * 16 if unit in ("rem", "em") else num * (4 / 3) if unit == "pt" else num


def check_guardrails(dna: dict, ui_dir: Path) -> list[dict]:
    violations: list[dict] = []
    files = collect_code_files(ui_dir)
    if not files:
        return [{"where": str(ui_dir), "rule": "no code files found", "detail": "nothing to check"}]
    for taste in dna["taste"]:
        if taste.get("kind") != "restraint":
            continue
        g = taste.get("guardrail") or {}
        forbid_css = [p.lower() for p in g.get("forbidCss", [])]
        require_css = [p.lower() for p in g.get("requireCss", [])]
        forbid_cls = [re.compile(p) for p in g.get("forbidClass", [])]
        maxes = {k.lower(): v for k, v in (g.get("max") or {}).items()}

        for f in files:
            for ln, prop, value in declarations(f):
                if any(prop == b or prop.startswith(b + "-") for b in forbid_css):
                    violations.append(
                        {"file": str(f), "line": ln, "principle": taste["id"],
                         "rule": f"forbidCss: {prop}", "detail": f"{prop}: {value}"}
                    )
                if prop in maxes and value.lower().strip() != "none":
                    lim = maxes[prop]
                    unit = lim.get("unit", "px")
                    if prop.startswith("box-shadow"):
                        bad = [v for v in shadow_lengths(value) if to_px(abs(v[0]), v[1]) > float(lim["value"])]
                        for off, u in bad:
                            if True:
                                violations.append(
                                    {"file": str(f), "line": ln, "principle": taste["id"],
                                     "rule": f"max {prop} length ≤ {lim['value']}{unit}",
                                     "detail": f"{prop}: {value}"}
                                )
                                break
                        continue
                    got = parse_length(value)
                    if got and unit in FREE_UNITS and got[1] == unit:
                        if got[0] > float(lim["value"]):
                            violations.append(
                                {"file": str(f), "line": ln, "principle": taste["id"],
                                 "rule": f"max {prop} ≤ {lim['value']}{unit}",
                                 "detail": f"{prop}: {value}"}
                            )
            for ln, classes in css_classes(f):
                for pattern in forbid_cls:
                    for cls in classes:
                        if pattern.search(cls):
                            violations.append(
                                {"file": str(f), "line": ln, "principle": taste["id"],
                                 "rule": f"forbidClass: /{pattern.pattern}/", "detail": cls}
                            )
        for prop in require_css:
            found = any(p == prop for f in files for _, p, _ in declarations(f))
            if not found:
                violations.append(
                    {"file": str(ui_dir), "line": 0, "principle": taste["id"],
                     "rule": f"requireCss: {prop}",
                     "detail": "property never declared in generated code"}
                )
    return violations


# ---------------------------------------------------------------- gate 1
def drift_check(dest: Path, dna: dict) -> tuple[list[str], list[str]]:
    """Byte-equal artifacts + no block moved since the snapshot in verify.json."""
    """Compare renders against (a) the current dna.json and (b) the state last rendered."""
    drift: list[str] = []
    expected = {
        "taste.md": ba.render_taste_md,
        "tokens.css": ba.render_tokens_css,
        "tokens.resolved.json": ba.render_resolved_json,
        "agent-rules.md": ba.render_agent_rules,
    }
    for name, fn in expected.items():
        p = dest / name
        if not p.exists():
            drift.append(f"{name} missing")
            continue
        try:
            want = fn(dna)
        except Exception as exc:  # a broken renderer must never masquerade as a pass
            drift.append(f"{name} render failed: {exc}")
            continue
        if p.read_text(encoding="utf-8") != want:
            drift.append(f"{name} drifted from dna.json (edited by hand, or render not rerun)")
    rendered = None
    try:
        record = json.loads((dest / "verify.json").read_text(encoding="utf-8"))
        rendered = record.get("dna")
        if record.get("renderedBy") != ba.RENDERER_VERSION:
            drift.append("VERIFY: last render used an older script; rerun build_artifacts.py")
    except (OSError, json.JSONDecodeError):
        pass
    changed: list[str] = []
    if isinstance(rendered, dict):
        changed = [b for b in ba.BLOCKS if b != "meta" and rendered.get(b) != dna.get(b)]
        if changed:
            drift.append(f"authored blocks changed after the last render: {changed} — rerun build_artifacts.py")
    return drift, changed


def frozen_violations(dna: dict, changed: list[str]) -> list[str]:
    inc = (dna.get("meta") or {}).get("incremental") or {}
    frozen = inc.get("frozen") or []
    return [f"{b} changed but was frozen by the last incremental run" for b in changed if b in frozen]


def schema_checks(dest: Path, dna: dict) -> list[dict]:
    rows: list[dict] = []
    errors = ba.validate(dna)
    rows.append({"name": "dna.json contract", "result": "PASS" if not errors else "FAIL",
                 "detail": "; ".join(errors[:5]) if errors else "SSOT valid (evidence/measurements/patterns/taste/tokens)"})
    scan_slop_safe = not errors

    render_errors: list[str] = []
    try:
        ba.resolve_tokens(dna["tokens"], (dna["meta"].get("modes") or ["default"])[0])
    except ba.SchemaError as exc:
        render_errors.append(str(exc))
    rows.append({"name": "token resolution", "result": "PASS" if not render_errors else "FAIL",
                 "detail": "; ".join(render_errors) or "all aliases resolve, no cycles"})

    drift, changed = drift_check(dest, dna)
    rows.append({"name": "single source (R3)", "result": "PASS" if not drift else "FAIL",
                 "detail": "; ".join(drift) or "all artifacts are deterministic renders of dna.json, no post-render edits"})

    frozen_moves = frozen_violations(dna, changed)
    inc = (dna.get("meta") or {}).get("incremental") or {}
    scope = f" — scope {inc.get('targets')}, frozen {inc.get('frozen')}" if inc else ""
    rows.append({"name": "incremental freeze", "result": "PASS" if not frozen_moves else "FAIL",
                 "detail": "; ".join(frozen_moves) or "no frozen block changed since the last render" + scope})

    missing_refs = []
    ev_ids = {e["id"] for e in dna.get("evidence", [])}
    if not ev_ids:
        missing_refs.append("no evidence ledger")
    rows.append({"name": "evidence coverage", "result": "PASS" if not missing_refs else "WARN",
                 "detail": "; ".join(missing_refs) or f"{len(ev_ids)} evidence entries cited"})

    inc = (dna.get("meta") or {}).get("incremental")
    expected_row = [t for t in dna.get("taste", []) if t.get("kind") == "restraint"]
    guarded = [t for t in expected_row if isinstance(t.get("guardrail"), dict) and t["guardrail"]]
    rows.append({"name": "restraint guardrails", "result": "PASS" if len(guarded) == len(expected_row) and expected_row else "FAIL",
                 "detail": f"{len(guarded)}/{len(expected_row)} restraint principles carry machine-readable guardrails" +
                           (f"; incremental targets={inc['targets']} frozen={inc['frozen']}" if inc else "")})
    return rows


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True, help="output directory {dest}/{domain}/")
    ap.add_argument("--check-code", help="directory of generated UI to check against guardrails")
    ap.add_argument("--report-only", action="store_true", help="do not write VERIFY.md / verify.json")
    args = ap.parse_args()

    dest = Path(args.dest).expanduser().resolve()
    dna_path = dest / "dna.json"
    if not dna_path.exists():
        print(f"FAIL: {dna_path} not found")
        return 1
    dna = json.loads(dna_path.read_text(encoding="utf-8"))

    rows = schema_checks(dest, dna)

    try:
        slop = scan_slop(dna)
    except Exception as exc:
        slop = [{"where": "dna.json", "word": "n/a", "line": f"slop scan crashed: {exc}"}]
    rows.append({"name": "anti-slop (authored prose)", "result": "PASS" if not slop else "FAIL",
                 "detail": f"{len(slop)} hit(s)" + (
                     ": " + " | ".join(f"{h['where']} ← “{h['word']}”" for h in slop[:5]) if slop else "")})

    violations = []
    if args.check_code:
        ui = Path(args.check_code).expanduser().resolve()
        if not ui.is_dir():
            rows.append({"name": "guardrail (generated code)", "result": "FAIL", "detail": f"{ui} is not a directory"})
        else:
            violations = check_guardrails(dna, ui)
            bad = [v for v in violations if v.get("line")]
            rows.append({"name": "guardrail (generated code)", "result": "PASS" if not bad else "FAIL",
                         "detail": f"{len(bad)} violation(s)" + (
                             ": " + " | ".join(f"{Path(v['file']).name}:{v['line']} {v['rule']}" for v in bad[:5]) if bad else f"scanned {ui}")})
    else:
        rows.append({"name": "guardrail (generated code)", "result": "unverified",
                     "detail": "no --check-code supplied"})

    rows.append({"name": "visual fidelity", "result": "unverified", "detail": "requires specimen comparison at matching viewports"})
    mode = (dna.get("meta") or {}).get("mode")
    if mode == "full":
        site = dest / "system" / "index.html"
        rows.append({"name": "full system/ site", "result": "PASS" if site.exists() else "FAIL",
                     "detail": "system/index.html present" if site.exists() else "mode=full but system/index.html is missing"})
    else:
        rows.append({"name": "full system/ site", "result": "n/a", "detail": "DNA mode does not build system/"})

    try:  # keep the rendered snapshot so `build_artifacts --incremental` can prove frozen blocks held
        previous = json.loads((dest / "verify.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        previous = {}
    result = {"generatedAt": now(), "dest": str(dest), "meta": dna.get("meta", {}), "checks": rows,
              "renderedBy": ba.RENDERER_VERSION,
              "dna": previous.get("dna", dna),
              "slop": slop, "guardrailViolations": violations}
    failed = [r for r in rows if r["result"] == "FAIL"]

    for r in rows:
        print(f"[{r['result']}] {r['name']}: {r['detail']}")
    for h in slop:
        print(f"  slop {h['where']}: “{h['word']}” in {h['line']}")
    for v in violations:
        if v.get("line"):
            print(f"  guardrail {v['file']}:{v['line']} {v['rule']} — {v['detail']}")

    if not args.report_only:
        (dest / "verify.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (dest / "VERIFY.md").write_text(ba.render_verify_md(dest, result), encoding="utf-8")
        print(f"wrote {dest / 'VERIFY.md'} and {dest / 'verify.json'}")

    if failed:
        print(f"FAIL: {len(failed)} gate(s) failed — fix and rerun, do not report success")
        return 1
    print("PASS: all executable gates green (unverified rows are listed in VERIFY.md, not claimed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
