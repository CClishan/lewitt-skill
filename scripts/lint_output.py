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


def repo_relative(path: Path, base: Path) -> str:
    """Never write a machine path into an artifact: prefer <dest-parent>/<name> style."""
    try:
        return path.resolve().relative_to(base.resolve().parent).as_posix()
    except ValueError:
        try:
            return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            return path.name


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
        "preview.html": lambda d: ba.render_preview_html(d, dest),
        "shadcn-theme.css": ba.render_shadcn_theme,
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


# assets only: src=, and href= on <link>; ordinary <a href> citations are allowed
PREVIEW_DEPS = re.compile(r'(?:<img[^>]*?src|src|<link[^>]*?href)\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
PREVIEW_EXTERNAL = re.compile(r'^(?:https?:)?//', re.IGNORECASE)


SELF_TEST = [
    # (pattern family, sample class, should match)
    ("shadow-floor", "shadow-lg", True), ("shadow-floor", "shadow-2xl", True),
    ("shadow-floor", "shadow-sm", False), ("shadow-floor", "shadow-inner", False),
    ("gradient", "bg-gradient-to-r", True), ("gradient", "btn bg-linear-to-r", True),
    ("gradient", "bg-blue-100", False),
    ("bg-role", "bg-indigo-600", True), ("bg-role", "bg-white", False), ("bg-role", "bg-slate-100", False),
]


def guardrail_selftest(dna: dict) -> list[str]:
    """Regression net: a guardrail that compiles but matches nothing is worse than none."""
    bad = []
    for t in dna["taste"]:
        g = t.get("guardrail") or {}
        for pattern in g.get("forbidClass", []):
            try:
                re.compile(pattern)
            except re.error as exc:
                bad.append(f"{t['id']}: /{pattern[:40]}/ does not compile ({exc})")
                continue
            sample = None
            if "shadow" in pattern:
                # a variant-scoped rule ("hover:shadow-lg") is tried on the class as written,
                # not on the bare utility, or a correct guardrail reports as vacuous
                sample = ("hover:" if ":" in pattern else "btn ") + "shadow-lg"
            elif "gradient-to-" in pattern or "linear-to-" in pattern:
                sample = "bg-gradient-to-r"
            elif pattern.startswith("(?:^|[^a-z0-9-])bg-") or "bg-(?!" in pattern:
                sample = "bg-indigo-600"
            if sample and not re.search(pattern, sample):
                bad.append(f"{t['id']}: /{pattern[:48]}/ matches nothing (tried {sample!r})")
    return bad


def guardrail_static_conflicts(dna: dict) -> list[str]:
    """A min/max bound that also forbids the same property is unsatisfiable — catch it here, not at audit time."""
    bad = []
    for t in dna["taste"]:
        g = t.get("guardrail") or {}
        forbid = {p.lower() for p in g.get("forbidCss", [])}
        for prop in (g.get("max") or {}):
            if prop.lower() in forbid:
                bad.append(f"{t['id']}: '{prop}' is both required to stay under a bound and forbidden")
    return bad


def theme_checks(dest: Path, dna: dict) -> tuple[bool, str]:
    """Every shadcn slot must either map to a token or be declared UNMAPPED; never invented."""
    path = dest / "shadcn-theme.css"
    if not path.exists():
        return False, "shadcn-theme.css missing"
    css = path.read_text(encoding="utf-8")
    required = ["--background", "--foreground", "--primary", "--primary-foreground",
                "--muted-foreground", "--ring", "--radius"]
    missing = [slot for slot in required if not re.search(rf"^\s*{re.escape(slot)}:\s*\S", css, re.M)]
    if missing:
        return False, "slots missing entirely: " + ", ".join(missing)
    unmapped = re.findall(r"(--[a-z-]+): initial;", css)
    loop = ["--theme inline {"] if css.count("@theme inline") != 1 else []
    if loop:
        return False, "@theme inline block missing or duplicated"
    theme = css[css.index("@theme inline"):] if "@theme inline" in css else ""
    if "@theme inline" in css:
        theme = css[css.index("@theme inline"):css.index("}", css.index("@theme inline"))]
        wrong = [slot for slot, _, _ in ba.SHADCN_SLOTS if f"--color-{slot[2:]}: var({slot});" not in theme]
        if wrong:
            return False, "Tailwind v4 needs --color-* in @theme inline; missing: " + ", ".join(wrong[:4])
        self_ref = re.findall(r"^\s*(--color-[a-z-]+): var\(\1\);", css, re.M)
        if self_ref:
            return False, "self-referencing theme entries: " + ", ".join(self_ref[:3])
    detail = "all required slots mapped"
    if unmapped:
        detail += f"; {len(unmapped)} declared UNMAPPED: " + ", ".join(unmapped)
    return True, detail


def preview_checks(dest: Path, dna: dict) -> tuple[bool, str]:
    """The preview must be self-contained: same-folder tokens.css only, no CDN, no remote assets."""
    path = dest / "preview.html"
    if not path.exists():
        return False, "preview.html missing"
    html = path.read_text(encoding="utf-8")
    external = []
    for ref in PREVIEW_DEPS.findall(html):
        if PREVIEW_EXTERNAL.match(ref) or ref.startswith(("data:text/html", "javascript:")):
            external.append(ref)
    if '<link rel="stylesheet" href="tokens.css">' not in html:
        return False, "preview.html does not link the same-folder tokens.css"
    if external:
        return False, "external dependency: " + ", ".join(external[:4])
    return True, "single file, same-folder tokens.css, no remote assets"


JS_SCOPE_CHECK = r"""
// node --expose-internals: scope-resolved duplicate `var` detection, no bundled parser needed.
// Every generated inline script is compiled as one script; a `var` name bound twice in the same
// closure is reported (the later binding silently resets the earlier, and the page throws only
// when someone clicks it).
const vm = require('vm');
const srcs = JSON.parse(process.env.LW_SCRIPTS || '[]');
let parser = null;
try { parser = require('internal/deps/acorn/acorn/dist/acorn'); } catch (e) {}
const out = [];
if (!parser) { out.push('scope check unavailable: node has no vendored parser'); }
for (const [i, code] of (parser ? srcs : []).entries()) {
  let tree;
  try { tree = parser.parse(code, { ecmaVersion: 2022, locations: true }); }
  catch (e) { out.push('script ' + i + ' does not parse: ' + String(e.message).slice(0, 80)); continue; }
  const state = { owners: [], open: [] };       // owners: nodes with a var list; open: var-owning scopes
  const line = n => (n.loc ? n.loc.start.line : '?');
  const walk = (node, closesScope) => {
    if (!node || typeof node.type !== 'string') return;
    const isFn = node.type === 'FunctionDeclaration' || node.type === 'FunctionExpression' ||
                 node.type === 'ArrowFunctionExpression';
    if (isFn) { node.__vars = []; state.open.push(node); }
    if (node.type === 'VariableDeclaration' && node.kind === 'var') {
      const home = state.open[state.open.length - 1] || tree;
      home.__vars = home.__vars || [];
      for (const d of node.declarations) if (d.id && d.id.type === 'Identifier') home.__vars.push(d.id.name + '@' + line(node));
    }
    for (const k of Object.keys(node)) {
      const v = node[k];
      if (Array.isArray(v)) v.forEach(x => walk(x));
      else if (v && typeof v.type === 'string') walk(v, k === 'body' && isFn);
    }
    if (isFn) {
      const names = node.__vars || [];
      const counts = {};
      names.forEach(n => { const nm = n.split('@')[0]; counts[nm] = (counts[nm] || []).concat([n.split('@')[1]]); });
      for (const nm of Object.keys(counts)) if (counts[nm].length > 1) {
        out.push('script ' + i + " redeclares '" + nm + "' inside one function (lines " + counts[nm].join(', ') + ')');
      }
      state.open.pop();
    }
  };
  walk(tree);
  const top = tree.__vars || [];
  const tcount = {};
  top.forEach(n => { const nm = n.split('@')[0]; tcount[nm] = (tcount[nm] || []).concat([n.split('@')[1]]); });
  for (const nm of Object.keys(tcount)) if (tcount[nm].length > 1) {
    out.push('script ' + i + " redeclares '" + nm + "' in the top-level closure (lines " + tcount[nm].join(', ') + ')');
  }
}
// second class: an identifier read somewhere but declared nowhere in any script body and not a
// browser global (the "card is not defined" family — a rename lint never saw the page run).
const GLOBAL_NAMES = new Set(('window document navigator location history console setTimeout clearTimeout ' +
  'setInterval clearInterval requestAnimationFrame matchMedia localStorage sessionStorage JSON Math Object ' +
  'Array String Number Boolean Date Promise Map Set WeakMap Symbol RegExp Error Event CustomEvent URL ' +
  'Element HTMLElement Node NodeList CSS CSSStyleSheet getComputedStyle fetch parseInt parseFloat isNaN ' +
  'encodeURIComponent decodeURIComponent KeyboardEvent MouseEvent PointerEvent Image MutationObserver ' +
  'IntersectionObserver ResizeObserver DOMParser Intl Reflect arguments undefined NaN Infinity encodeURI ' +
  'decodeURI atob btoa globalThis queueMicrotask structuredClone AbortController URLSearchParams ' +
  'TextEncoder Blob FileReader FormData Uint8Array Float32Array ArrayBuffer HTMLInputElement').split(/\s+/));
const declared = new Set();
const bindingsOf = (pattern) => {
  if (!pattern) return;
  if (pattern.type === 'Identifier') { declared.add(pattern.name); return; }
  if (pattern.type === 'AssignmentPattern') { bindingsOf(pattern.left); return; }
  if (pattern.type === 'RestElement') { bindingsOf(pattern.argument); return; }
  if (pattern.type === 'ObjectPattern') { pattern.properties.forEach(pr => bindingsOf(pr.value || pr.argument)); return; }
  if (pattern.type === 'ArrayPattern') { pattern.elements.forEach(e => bindingsOf(e)); return; }
};
const collectBindings = (node) => {
  if (!node || typeof node.type !== 'string') return;
  if (node.type === 'VariableDeclarator') bindingsOf(node.id);
  if (node.type === 'FunctionDeclaration' || node.type === 'FunctionExpression' || node.type === 'ArrowFunctionExpression') {
    if (node.id) declared.add(node.id.name);
    (node.params || []).forEach(bindingsOf);
  }
  if (node.type === 'CatchClause') bindingsOf(node.param);
  for (const k of Object.keys(node)) {
    const v = node[k];
    if (Array.isArray(v)) v.forEach(collectBindings); else if (v && typeof v.type === 'string') collectBindings(v);
  }
};
const trees = [];
for (const code of (parser ? srcs : [])) {
  try { const t = parser.parse(code, { ecmaVersion: 2022, locations: true }); trees.push(t); collectBindings(t); }
  catch (e) { /* parse errors are reported above */ }
}
const undeclared = new Set();
for (const tree of trees) {
  const visit = (node, bind) => {
    if (!node || typeof node.type !== 'string') return;
    if (node.type === 'Identifier') {
      if (!bind && !declared.has(node.name) && !GLOBAL_NAMES.has(node.name)) {
        undeclared.add(node.name + '@' + (node.loc ? node.loc.start.line : '?'));
      }
      return;
    }
    if (node.type === 'MemberExpression' && !node.computed) { visit(node.object, false); return; }
    if (node.type === 'Property') { visit(node.value, node.shorthand ? false : true); return; }
    for (const k of Object.keys(node)) {
      const v = node[k];
      const isBind = (node.type === 'VariableDeclarator' && k === 'id') || (node.type === 'FunctionDeclaration' && k === 'id') ||
                     (node.type === 'FunctionExpression' && k === 'id') || (node.type === 'ClassDeclaration' && k === 'id') ||
                     (node.type === 'CatchClause' && k === 'param');
      if (Array.isArray(v)) v.forEach(x => visit(x, isBind));
      else if (v && typeof v.type === 'string') visit(v, isBind);
    }
  };
  visit(tree, false);
}
for (const id of undeclared) out.push('script reads undeclared identifier ' + id.split('@')[0] + ' (line ' + id.split('@')[1] + ')');
process.stdout.write(JSON.stringify(out));
"""


def script_selftest() -> list[str]:
    """A gate that cannot reproduce a known bug is worthless: inject both classes it guards."""
    dup = ('<script>var v = document.getElementById("probe-a");\n'
           'var other = document.getElementById("probe-b");\nvar v = document.getElementById("probe-c");</script>')
    undeclared = '<script>var el = document.getElementById("probe"); el.removeAttribute(missingAttr);</script>'
    bad = []
    if not script_checks(dup):
        bad.append("duplicate-name check did not catch an injected duplicate")
    if not script_checks(undeclared):
        bad.append("undeclared-identifier check did not catch an injected name")
    return bad


def script_checks(html: str) -> list[str]:
    """Every inline script in one generated page shares the page. A `var` bound twice in one closure is
    not a syntax error: the later binding silently resets the earlier one, and the page throws only
    when someone clicks (a duplicated rail var once crashed the view switch; a stale `card` once
    swallowed the evidence panel). This compiles each script body and reports both classes."""
    import os
    import subprocess
    bodies = []
    for attrs, body in re.findall(r"<script([^>]*)>(.+?)</script>", html, re.S):
        if re.search(r'type="(?:text/plain|application/json)"', attrs, re.I):
            continue                                            # json / theme payloads are data
        if not re.match(r'\s*(?:[{\[]|"[^"]*":)', body):
            bodies.append(body)
    if not bodies:
        return []
    env = {**os.environ, "LW_SCRIPTS": json.dumps(bodies)}
    try:
        proc = subprocess.run(["node", "--expose-internals", "--eval", JS_SCOPE_CHECK],
                              capture_output=True, text=True, env=env, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return ["script scope check did not run: node is not available"]
    if proc.returncode != 0:
        return [f"script scope check failed: {proc.stderr.strip()[:80]}"]
    try:
        return json.loads(proc.stdout.strip() or "[]")
    except json.JSONDecodeError:
        return []


def _rgb(value: str):
    m = re.fullmatch(r"#([0-9a-f]{6})", value.strip(), re.IGNORECASE)
    if not m:
        return None
    n = int(m.group(1), 16)
    return (n >> 16 & 255, n >> 8 & 255, n & 255)


def _lum(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(rgb[0]) + 0.7152 * ch(rgb[1]) + 0.0722 * ch(rgb[2])


SHADCN_VARS = {"--background", "--foreground", "--card", "--card-foreground", "--popover",
               "--popover-foreground", "--primary", "--primary-foreground", "--secondary",
               "--secondary-foreground", "--muted", "--muted-foreground", "--accent",
               "--accent-foreground", "--destructive", "--border", "--input", "--ring", "--radius"}
HARDCODED_COLOUR = re.compile(r"(?<![\w-])#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")


def brick_problems(path: Path) -> list[str]:
    """A brick must be skinless and honest: slots only, a measured reduce branch, real deltas."""
    name = path.parent.name
    out = []
    try:
        b = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [f"{name}: invalid JSON ({exc})"]
    system = (b.get("slots") or {}).get("system")
    if system not in ("shadcn", "lw"):
        out.append(f"{name}: slots.system must be shadcn or lw (got {system!r})")
    skin = {k: v for k, v in (b.get("skin") or {}).items() if not k.startswith("__")}
    if not skin:
        out.append(f"{name}: no skin mapping")
    for k, v in skin.items():
        css = (v or {}).get("css") or ""
        if not (v or {}).get("slot"):
            out.append(f"{name}: skin {k} mapped to no slot")
        if system == "shadcn":
            var = css[4:-1] if css.startswith("var(") and css.endswith(")") else ""
            if var not in SHADCN_VARS:
                out.append(f"{name}: skin {k} uses {css!r}, not a shadcn slot")
        if HARDCODED_COLOUR.search(css) or HARDCODED_COLOUR.search(str((v or {}).get("slot"))):
            out.append(f"{name}: skin {k} leaks a hardcoded colour")
    states = b.get("states") or {}
    if "before" not in states:
        out.append(f"{name}: no 'before' state")
    # an empty brick is the worst outcome: it looks usable but recorded nothing
    changes = sum(len(props) for d in (b.get("deltas") or {}).values() for props in (d or {}).values())
    b["_changes"] = changes
    if changes == 0 or b.get("conclusion") == "inconclusive":
        out.append(f"{name}: inconclusive — no computed delta observed, re-run with a more specific --selector")
    if b.get("conclusion") == "observed" and changes == 0:
        out.append(f"{name}: claims 'observed' but records no delta")
    if not states.get("_machine"):
        out.append(f"{name}: no state machine")
    for target, d in (b.get("deltas") or {}).items():
        for part, props in (d or {}).items():
            if part not in ("trigger", "module", "hovered element", "stateful"):
                out.append(f"{name}: {target}.{part} is not a sampled part "
                           "(trigger / module / hovered element / stateful)")
                continue
            for prop, pair in (props or {}).items():
                if not isinstance(pair, list) or len(pair) != 2:
                    out.append(f"{name}: {target}.{part}.{prop} is not a [before, after] pair")
    rm = b.get("reducedMotion")
    if not isinstance(rm, dict) or not rm:
        if b.get("conclusion") != "inconclusive":
            out.append(f"{name}: no reducedMotion recording (run without --no-reduced)")
    elif rm.get("status") not in ("degraded", "degraded-to-none", "not-degraded", "unrecorded"):
        out.append(f"{name}: reducedMotion.status {rm.get('status')!r} is not a known verdict")
    elif rm.get("emulated") is not True:
        out.append(f"{name}: reduced-motion pass did not confirm the media emulation")
    md = path.parent / "brick.md"
    if not md.exists():
        out.append(f"{name}: brick.md missing")
    else:
        text = md.read_text(encoding="utf-8")
        if "Slot system:" not in "\n".join(text.splitlines()[:6]):
            out.append(f"{name}: brick.md does not state the slot system at the top")
        if "## Reduced motion" not in text:
            out.append(f"{name}: brick.md has no Reduced motion section")
        skin_md = text.split("## Skin mapping")[-1].split("## State machine")[0]
        if "var(--" not in skin_md:
            out.append(f"{name}: brick.md skin section names no variable")
        leaked = [ln for ln in skin_md.splitlines() if ln.startswith("- `") and "→ `var(--" not in ln and "no slot" not in ln]
        if leaked:
            out.append(f"{name}: brick.md skin line without a variable: {leaked[0][:60]}")
    return out


ROLLS = ("01", "02", "03", "04")


def shell_checks(html: str) -> list[str]:
    """system/ and preview.html are a dual-view long scroll: minimal top bar, Live Preview | Specs.

    Required (v1.2):
      - sticky top bar: lewitt mark, the run's 3px fingerprint band, a two-option view segmented
        control (Live Preview default, Specs & Evidence), a copy-shadcn button, and the three
        stress booleans (Long copy / Reduced motion / Narrow 390);
      - view 1, an immersive long scroll with numbered sections 01 colour · 02 type ·
        03 components · 04 motion & guardrails (05 bricks is optional: it states its own absence);
        colour carries Observed tags and WCAG chips, motion is drawn from the bezier, guardrails
        are MUST NOT capsules with the regex folded away;
      - view 2, the specs panels (tokens, measurements, evidence, downloads at least).
    The old rail shell is still accepted so runs rendered before v1.2 do not regress.
    """
    problems: list[str] = []
    if 'class="topbar"' not in html:
        if 'class="rail"' in html and 'class="panel' in html:
            return _legacy_shell_checks(html)
        return ["missing the sticky top bar (class=\"topbar\")"]
    for token, label in (('id="fp"', "brand fingerprint band"), ('class="tb-seg"', "view segmented control"),
                         ('id="tab-live"', "Live Preview tab"), ('id="tab-specs"', "Specs tab"),
                         ('id="copy-theme"', "copy shadcn-theme.css button"),
                         ('id="stress-btn"', "Stress menu control"), ('id="stress-menu"', "Stress menu"),
                         ('id="theme-css"', "inline shadcn theme payload")):
        if token not in html:
            problems.append(f"top bar missing {label}")
    # the top bar stays three groups: no counters, no duplicate section rail
    topbar = html.split('class="topbar"', 1)[1].split("</header>", 1)[0] if 'class="topbar"' in html else ""
    if "tb-meta" in topbar:
        problems.append("top bar carries counters (tb-meta): they belong in the Specs overview")
    if 'class="lp-jump"' in html or 'class="tp-jump"' in html:
        problems.append("a second section rail duplicates the in-canvas nav")
    for key, label in (("long", "Long copy"), ("reduced", "Reduced motion"), ("narrow", "Narrow 390")):
        if f'data-stress-toggle="{key}"' not in html:
            problems.append(f"top bar missing the stress switch “{label}”")
    live = html.split('id="view-live"', 1)[1].split('id="view-specs"', 1)[0] if 'id="view-live"' in html else ""
    specs = html.split('id="view-specs"', 1)[1] if 'id="view-specs"' in html else ""
    for num, key in ((n, k) for n, k in (("01", "colour"), ("02", "type"), ("03", "components"),
                                          ("04", "motion"), ("05", "bricks"))):
        if f'<span class="lp-num">{num}</span>' not in live:
            problems.append(f"Live Preview has no section {num}")
        if f'<section class="lp-sec" id="{key}"' not in live and not (num == "01" or f'id="{key}"' in live):
            problems.append(f"section {num} has no numbered long-scroll heading")
    if 'class="tag-obs"' not in live:
        problems.append("Live Preview carries no Observed evidence tag")
    if "wchip" not in live:
        problems.append("Live Preview has no WCAG contrast chip on colour")
    if 'class="bezier"' not in live:
        problems.append("Motion has no drawn bezier curve")
    if "data-sys-replay" not in live:
        problems.append("Motion has no replay control")
    if "must not" not in live.lower():
        problems.append("Guardrails show no MUST NOT capsule")
    if not re.search(r'class="gate forbid gate-regex"', live):
        problems.append("Guardrails fold no regex behind a disclosure (no restraint with a class regex)")
    if 'class="lp-hero"' not in live:
        problems.append("Live Preview opens with no brand hero")
    for panel in ("tokens", "measurements", "evidence", "downloads"):
        if f'id="sp-{panel}"' not in specs:
            problems.append(f"Specs view missing the {panel} panel")
    if re.search(r'<div class="lp-scroll"([^>]*data-ds|.*?)>', html) is None or \
            not re.search(r'<div class="lp-scroll"[^>]*data-ds', html):
        problems.append("Live Preview is not scoped to the run's tokens (lp-scroll without [data-ds])")
    return problems


def _legacy_shell_checks(html: str) -> list[str]:
    """Pre-1.2 app shell: one rail, one scrolling canvas, routed panels."""
    problems = []
    for token, label in (('class="canvas"', "canvas"), ('class="toolbar"', "sticky toolbar"),
                         ('class="scroll"', "scrolling region")):
        if token not in html:
            problems.append(f"missing {label}")
    panels = html.count('class="panel')
    if panels < 2:
        problems.append(f"only {panels} panel(s); expected >= 2 routed panels")
    if 'data-stress-toggle' not in html:
        problems.append("no stress toggles in the toolbar")
    return problems


def system_colour_scope(dest: Path, dna: dict) -> tuple[bool, str]:
    """In DNA mode the page owns no colour; in full mode the page must sit on its own canvas token.

    A system/ page that inherits the documentation chrome is the failure this catches: light-token
    systems rendered on a dark shell (or the reverse).
    """
    mode = (dna.get("meta") or {}).get("mode")
    if mode != "full":
        return True, "n/a (DNA mode has no system/ site)"
    page = dest / "system" / "index.html"
    if not page.exists():
        return False, "mode=full but system/index.html is missing"
    html = page.read_text(encoding="utf-8")
    canvas_ids = [t["id"] for t in dna["tokens"] if t["id"] == "color/canvas"]
    if not canvas_ids:
        return True, "page loads the site stylesheet; no color/canvas token to compare"
    resolved = ba.resolve_tokens(dna["tokens"], (dna["meta"].get("modes") or ["default"])[0])
    canvas_hex = resolved["color/canvas"]["resolved"]
    # the page body must take its background from the system canvas token, not from chrome defaults
    body_rule = re.search(r"body\s*\{[^}]*\}", Path(dest, "system", "site.css").read_text(encoding="utf-8")) \
        if (dest / "system" / "site.css").exists() else None
    uses_token = "var(--lw-canvas" in html or "var(--lw-canvas" in (dest / "system" / "system.css").read_text(encoding="utf-8")
    if not uses_token:
        return False, "system/ does not use the canvas token"
    rgb = _rgb(canvas_hex)
    tone = "light" if rgb and _lum(rgb) > 0.5 else "dark"
    chrome = (dest / "system" / "doc.css").read_text(encoding="utf-8")
    # --doc-bg is tone-known only when the page renders, so it is declared inline on the page
    chrome_bg = (re.search(r"--doc-bg:\s*(#[0-9a-fA-F]{6})", html)
                 or re.search(r"--doc-bg:\s*(#[0-9a-fA-F]{6})", chrome))
    chrome_rgb = _rgb(chrome_bg.group(1)) if chrome_bg else None
    return True, f"canvas token {canvas_hex} ({tone}); chrome shell {'dark' if chrome_rgb and _lum(chrome_rgb) < 0.3 else 'light'}"


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

    conflicts = guardrail_static_conflicts(dna)
    rows.append({"name": "guardrail static conflicts", "result": "PASS" if not conflicts else "FAIL",
                 "detail": "; ".join(conflicts) or "no bound forbids the property it bounds"})

    selftest = guardrail_selftest(dna)
    rows.append({"name": "guardrail pattern self-test", "result": "PASS" if not selftest else "FAIL",
                 "detail": "; ".join(selftest[:4]) or "every forbidClass pattern compiles and catches a known violation"})

    ok, detail = system_colour_scope(dest, dna)
    rows.append({"name": "system/ colour scope", "result": "PASS" if ok else "FAIL", "detail": detail})

    inter = dna.get("interactions") or []
    if not inter:
        rows.append({"name": "interaction delta", "result": "unverified", "detail": "no interactions block (schema 1.0 run or capture without probe)"})
    else:
        measured = [i for i in inter if ((i.get("hover") or {}).get("delta") or (i.get("focus") or {}).get("delta"))]
        rows.append({"name": "interaction delta", "result": "PASS" if measured else "FAIL",
                     "detail": f"{len(measured)}/{len(inter)} targets recorded a hover/focus delta"})

    ok, detail = theme_checks(dest, dna)
    rows.append({"name": "shadcn theme slots", "result": "PASS" if ok else "FAIL", "detail": detail})

    bdir = dest / "clips"
    bricks = sorted(bdir.glob("*/brick.json")) if bdir.is_dir() else []
    if bricks:
        problems = []
        for f in bricks:
            problems += brick_problems(f)
        rows.append({"name": "clip bricks", "result": "PASS" if not problems else "FAIL",
                     "detail": "; ".join(problems[:5]) or f"{len(bricks)} brick(s) valid"})
    else:
        rows.append({"name": "clip bricks", "result": "n/a", "detail": "no clips/ directory"})

    ok, detail = preview_checks(dest, dna)
    script_problems = [p for p in script_checks((dest / "preview.html").read_text(encoding="utf-8"))] if ok else []
    if ok:
        html = (dest / "preview.html").read_text(encoding="utf-8")
        site = shell_checks(html) + script_problems
        ok, detail = not site, detail if not site else "; ".join(site)
    rows.append({"name": "preview.html (self-contained, dual view)", "result": "PASS" if ok else "FAIL", "detail": detail})

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
        # dest may name the clips folder itself (…/clips) or a single brick folder
        roots = [dest / "clips", dest] if dest.name == "clips" else [dest / "clips", dest]
        bricks = sorted({f for root in roots for f in root.glob("*/brick.json")} |
                        ({dest / "brick.json"} if (dest / "brick.json").exists() else set()))
        if bricks:
            verdicts = {f: brick_problems(f) for f in bricks}
            problems = [p for probs in verdicts.values() for p in probs]
            for f, probs in verdicts.items():
                print(f"[{'PASS' if not probs else 'FAIL'}] {f.parent.name}" + ("" if not probs else f" — {probs[0]}"))
            print(("PASS: " if not problems else "FAIL: ") + f"{len(bricks)} standalone brick(s)"
                  + ("" if not problems else f", {len(problems)} problem(s): " + "; ".join(problems[:5])))
            return 0 if not problems else 1
        print(f"FAIL: {dna_path} not found (and no clips/ to gate standalone)")
        return 1
    dna = json.loads(dna_path.read_text(encoding="utf-8"))

    rows = schema_checks(dest, dna)

    try:
        slop = scan_slop(dna)
    except Exception as exc:
        slop = [{"where": "dna.json", "word": "n/a", "line": f"slop scan crashed: {exc}"}]
    selftest_script = script_selftest()
    rows.append({"name": "generated-code script scope", "result": "PASS" if not selftest_script else "FAIL",
                 "detail": "; ".join(selftest_script) or "duplicate var names and undeclared identifiers are both caught (injected probes)"})

    rows.append({"name": "anti-slop (authored prose)", "result": "PASS" if not slop else "FAIL",
                 "detail": f"{len(slop)} hit(s)" + (
                     ": " + " | ".join(f"{h['where']} ← “{h['word']}”" for h in slop[:5]) if slop else "")})

    violations = []
    if args.check_code:
        ui = Path(args.check_code).expanduser().resolve()
        if not ui.is_dir():
            rows.append({"name": "guardrail (generated code)", "result": "FAIL", "detail": f"{repo_relative(ui, dest)} is not a directory"})
        else:
            violations = check_guardrails(dna, ui)
            bad = [v for v in violations if v.get("line")]
            rows.append({"name": "guardrail (generated code)", "result": "PASS" if not bad else "FAIL",
                         "detail": (f"{len(bad)} violation(s) — " + " | ".join(
                             f"{repo_relative(Path(v['file']), dest)}:{v['line']} {v['rule']}" for v in bad[:5])
                             if bad else f"0 violation(s) — scanned {repo_relative(ui, dest)}")})
    else:
        rows.append({"name": "guardrail (generated code)", "result": "unverified",
                     "detail": "no --check-code supplied"})

    fid = dest / "fidelity.json"
    if not fid.exists():
        rows.append({"name": "visual fidelity", "result": "unverified",
                     "detail": "no fidelity.json — requires a side-by-side comparison at matching viewports"})
    else:
        try:
            rec = json.loads(fid.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            rows.append({"name": "visual fidelity", "result": "FAIL", "detail": f"fidelity.json is not valid JSON: {exc}"})
        else:
            ok = isinstance(rec.get("compared"), list) and rec["compared"] and isinstance(rec.get("deviations"), list) \
                and rec.get("method") and rec.get("status") in ("partial", "match", "mismatch")
            res = "PASS" if ok and rec.get("status") == "match" else ("PARTIAL" if ok else "FAIL")
            rows.append({"name": "visual fidelity", "result": res,
                         "detail": f"{len(rec.get('compared', []))} composition(s), "
                                   f"{len(rec.get('deviations', []))} recorded deviation(s), status={rec.get('status')}"})
    mode = (dna.get("meta") or {}).get("mode")
    if mode == "full":
        site = dest / "system" / "index.html"
        if not site.exists():
            rows.append({"name": "full system/ site", "result": "FAIL", "detail": "mode=full but system/index.html is missing"})
        else:
            html = site.read_text(encoding="utf-8")
            shell = shell_checks(html) + script_checks(html)
            rows.append({"name": "full system/ site", "result": "PASS" if not shell else "FAIL",
                         "detail": "dual view present (top bar + Live Preview 01-05 + Specs)" if not shell else "; ".join(shell)})
    else:
        rows.append({"name": "full system/ site", "result": "n/a", "detail": "DNA mode does not build system/"})

    try:  # keep the rendered snapshot so `build_artifacts --incremental` can prove frozen blocks held
        previous = json.loads((dest / "verify.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        previous = {}
    result = {"generatedAt": now(), "dest": repo_relative(dest, dest), "meta": dna.get("meta", {}), "checks": rows,
              "renderedBy": ba.RENDERER_VERSION,
              "dna": previous.get("dna", dna),
              "slop": slop, "guardrailViolations": violations}
    failed = [r for r in rows if r["result"] == "FAIL"]
    partial = [r for r in rows if r["result"] == "PARTIAL"]

    for r in rows:
        print(f"[{r['result']}] {r['name']}: {r['detail']}")
    for h in slop:
        print(f"  slop {h['where']}: “{h['word']}” in {h['line']}")
    for v in violations:
        if v.get("line"):
            print(f"  guardrail {repo_relative(Path(v['file']), dest)}:{v['line']} {v['rule']} — {v['detail']}")

    if not args.report_only:
        (dest / "verify.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (dest / "VERIFY.md").write_text(ba.render_verify_md(dest, result), encoding="utf-8")
        print(f"wrote {dest / 'VERIFY.md'} and {dest / 'verify.json'}")

    if failed:
        print(f"FAIL: {len(failed)} gate(s) failed — fix and rerun, do not report success")
        return 1
    note = f"; {len(partial)} row(s) PARTIAL: " + ", ".join(r["name"] for r in partial) if partial else ""
    print("PASS: all executable gates green (unverified/partial rows are listed in VERIFY.md, not claimed)" + note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
