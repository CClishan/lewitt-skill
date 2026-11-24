#!/usr/bin/env python3
"""lewitt — render every artifact from the single source of truth (dna.json).

SSOT contract (R3):
  dna.json is the ONLY authored file. Everything else is a deterministic render:
    taste.md            human-readable Design Map + Taste DNA
    tokens.css          :root variables + component aliases, scope [data-ds]
    tokens.resolved.json  flat resolved values for downstream tools
    agent-rules.md      rules block first, guardrails (Restraint) on top
    preview.html        single-file live specimens + motion replay + taste cards (links ./tokens.css)
    verify.json         machine gate results (report is rendered by `lint`)

Refuses to run in `--incremental` (frozen) mode unless the file is an explicit
target. Never invents values: literals come from tokens[] only.

Usage:
  python3 build_artifacts.py <dest_dir>                 # render all artifacts (+ schema)
  python3 build_artifacts.py <dest_dir> --incremental measurements,taste
                                                        # only rerun those blocks; freeze the rest
  python3 build_artifacts.py <dest_dir> --check         # schema only, write nothing
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import preview_template as _preview
except ImportError:  # imported as a package
    from . import preview_template as _preview
PREVIEW_CSS, PREVIEW_JS = _preview.PREVIEW_CSS, _preview.PREVIEW_JS


SHADCN_SLOTS = [
    ("--background", ["color/canvas", "color/background", "color/surface/canvas"], "canvas"),
    ("--foreground", ["color/text/primary", "color/text/heading", "color/text/body", "color/foreground"], "primary text"),
    ("--card", ["color/surface", "color/card", "color/surface/raised", "color/canvas-tint"], "raised surface"),
    ("--card-foreground", ["color/text/primary", "color/text/body"], "card text"),
    ("--popover", ["color/surface", "color/overlay", "color/card", "color/canvas"], "overlay surface"),
    ("--popover-foreground", ["color/text/primary", "color/text/body"], "overlay text"),
    ("--primary", ["color/action/bg", "color/action/primary", "color/brand", "color/accent"], "action fill"),
    ("--primary-foreground", ["color/action/fg", "color/on-brand", "color/text/on-action"], "action label"),
    ("--secondary", ["color/surface-subtle", "color/surface/muted", "color/well", "color/surface"], "secondary fill"),
    ("--secondary-foreground", ["color/text/primary", "color/text/body"], "secondary label"),
    ("--muted", ["color/surface-subtle", "color/well", "color/surface/muted", "color/surface"], "muted fill"),
    ("--muted-foreground", ["color/text/muted", "color/text/tertiary", "color/text/secondary"], "muted text"),
    ("--accent", ["color/surface-subtle", "color/action/bg", "color/brand"], "hover fill"),
    ("--accent-foreground", ["color/text/primary", "color/text/heading", "color/action/fg"], "hover label"),
    ("--destructive", ["color/danger", "color/error", "color/trend/down", "color/down"], "destructive action"),
    ("--border", ["color/border", "color/stroke", "color/divider", "color/canvas-tint"], "borders"),
    ("--input", ["color/border-strong", "color/stroke/strong", "color/border", "color/canvas-tint"], "input borders"),
    ("--ring", ["color/link", "color/focus", "color/action/bg", "color/brand"], "focus ring"),
]
# --radius is the control radius: inputs and buttons must not inherit a card-sized radius
SHADCN_RADIUS = [("--radius", ["radius/control", "radius/control-alt", "radius/button", "radius/card"])]


def _first_token(dna: dict, candidates: list[str], predicate=lambda t: True) -> str | None:
    ids = [t["id"] for t in dna["tokens"] if predicate(t)]
    for cand in candidates:
        if cand in ids:
            return cand
    return None


def render_theme_head(dna: dict, mode: str | None = None) -> str:
    """Theme slots derived from tokens only; nothing is invented."""
    mode = mode or (dna["meta"].get("modes") or ["default"])[0]
    resolved = resolve_tokens(dna["tokens"], mode)
    tokens = {t["id"]: t for t in dna["tokens"]}
    out = ["  @layer base {", "    :root {"]
    notes = []
    for slot, candidates, _label in SHADCN_SLOTS:
        tid = _first_token(dna, candidates, lambda t: t["type"] == "color")
        if tid:
            out.append(f"      {slot}: {resolved[tid]['resolved']}; /* {tid} */")
        else:
            notes.append(f"missing {slot}")
    out.append("    }")
    out.append("  }")
    return "\n".join(out) + ("\n  /* unmapped: " + ", ".join(notes) + " */" if notes else "")


def render_shadcn_theme(dna: dict) -> str:
    mode = (dna["meta"].get("modes") or ["default"])[0]
    resolved = resolve_tokens(dna["tokens"], mode)
    meta = dna["meta"]
    dark_roles = [t for t in dna["tokens"] if t["id"] == "color/canvas"]
    canvas = resolved["color/canvas"]["resolved"] if dark_roles else "#ffffff"
    rgb = _hex_rgb(canvas)
    scheme = "dark" if rgb and _relative_luminance(rgb) < 0.35 else "light"

    slots = []
    for slot, candidates, label in SHADCN_SLOTS:
        tid = _first_token(dna, candidates, lambda t: t["type"] == "color")
        slots.append((slot, tid, label))
    radius = None
    for cand in SHADCN_RADIUS[0][1]:
        if any(t["id"] == cand for t in dna["tokens"]):
            radius = cand
            break

    lines = [
        "@custom-variant dark (&:is(.dark *));",
        "",
        ":root {",
    ]
    unmapped = []
    for slot, tid, label in slots:
        if tid:
            lines.append(f"  {slot}: {resolved[tid]['resolved']}; /* {tid} — {label} */")
        else:
            unmapped.append(f"{slot} ({label})")
            lines.append(f"  {slot}: initial; /* UNMAPPED — no {label} token in dna.json */")
    if radius:
        lines.append(f"  {SHADCN_RADIUS[0][0]}: {resolved[radius]['resolved']}; /* {radius} */")
    else:
        unmapped.append("--radius")
        lines.append("  --radius: 0.625rem; /* UNMAPPED — shadcn default kept */")
    lines += [
        "}",
        "",
        "@theme inline {",
        *[f"  --color-{slot[2:]}: var({slot});" for slot, _, _ in SHADCN_SLOTS],
        "  --radius-sm: calc(var(--radius) - 4px);",
        "  --radius-md: calc(var(--radius) - 2px);",
        "  --radius-lg: var(--radius);",
        "  --radius-xl: calc(var(--radius) + 4px);",
        "}",
        "",
        "@layer base {",
        "  * { @apply border-border outline-ring/50; }",
        "  body { @apply bg-background text-foreground; }",
        "}",
        "",
    ]
    header = [
        "/* shadcn/ui + Tailwind v4 theme — generated by lewitt from dna.json (R3: do not hand-edit).",
        f"   source: {meta['source']} · extracted {str(meta.get('capturedAt', 'unknown'))[:10]} · colour scheme: {scheme}",
        "   Paste into globals.css after `@import \"tailwindcss\";`. Every value maps to a token id below.",
    ]
    if unmapped:
        header.append("   UNMAPPED slots (left as `initial` / shadcn default, never invented): " + ", ".join(unmapped))
    header[-1] += " */"
    return "\n".join(header + [""] + lines) + "\n"


def _hex_rgb(value: str):
    v = value.strip()
    if v.startswith("rgb("):
        parts = [p.strip() for p in v[4:-1].split(",")]
        try:
            return tuple(int(p) for p in parts[:3])
        except ValueError:
            return None
    if re.fullmatch(r"#[0-9a-fA-F]{6}", v):
        n = int(v[1:], 16)
        return (n >> 16 & 255, n >> 8 & 255, n & 255)
    return None


def _relative_luminance(rgb) -> float:
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(rgb[0]) + 0.7152 * ch(rgb[1]) + 0.0722 * ch(rgb[2])


def render_preview_html(dna: dict, dest: Path | None = None) -> str:
    shots = {
        "viewport.png", "viewport-2.png", "viewport-3.png", "viewport-4.png",
    }

    def exists(name: str) -> bool:
        if dest is None:
            return True
        return (dest / "capture" / name).exists()

    return _preview.render_preview_html(dna, resolver=resolve_tokens, exists=exists)

RENDERER_VERSION = "build_artifacts.py/v2"
BLOCKS = ("meta", "evidence", "measurements", "patterns", "taste", "tokens", "interactions")
REQUIRED_BLOCKS = ("meta", "evidence", "measurements", "patterns", "taste", "tokens")
STATUSES = ("observed", "inferred", "proposed", "unknown")
LAYERS = ("primitive", "semantic", "component")
TOKEN_TYPES = (
    "color", "dimension", "number", "duration", "fontFamily", "fontWeight",
    "shadow", "gradient", "easing", "string",
)
UNIT_TYPES = ("dimension", "duration")
# Any block can be rerun when the caller declares it. `evidence` is special: it is
# append-only (re-observations add ids) and `meta` is tooling-owned.
RERUNNABLE = ("evidence", "measurements", "patterns", "taste", "tokens", "interactions")
SCHEMA_VERSION = "1.1"
INTERACTION_PROPS = ("background-color", "color", "border-color", "box-shadow", "outline", "transform")

BANNED = re.compile(
    r"\b(clean|modern|sleek|visually appealing|user-friendly|intuitive|seamless|"
    r"elegant|minimalist|polished|refined|sophisticated|delightful|stunning|"
    r"beautiful|premium)\b",
    re.IGNORECASE,
)
QUOTE_MARKERS = ('"', "'", "“", "”", "‘", "’")


class SchemaError(Exception):
    pass


def err(errors: list[str], msg: str) -> None:
    errors.append(msg)


# ---------------------------------------------------------------- validation
def validate(dna: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(dna, dict):
        return ["root is not an object"]
    missing = [b for b in REQUIRED_BLOCKS if b not in dna]
    if missing:
        err(errors, f"missing root blocks: {missing}")
    extra = [k for k in dna if k not in BLOCKS and k != "schemaVersion" and not k.startswith("x-")]
    if extra:
        err(errors, f"unknown root blocks: {extra}")

    if not isinstance(dna.get("schemaVersion"), str) or not dna["schemaVersion"].startswith("1."):
        err(errors, "schemaVersion must be a string like \"1.1\" (see dna.schema.json)")

    meta = dna.get("meta") or {}
    for key in ("name", "source", "domain", "mode"):
        if not isinstance(meta.get(key), str) or not meta.get(key):
            err(errors, f"meta.{key} must be a non-empty string")
    if meta.get("mode") not in ("dna", "full"):
        err(errors, "meta.mode must be 'dna' or 'full'")
    if meta.get("incremental") is not None:
        inc = meta["incremental"]
        if not isinstance(inc, dict) or not isinstance(inc.get("targets"), list) or not isinstance(inc.get("frozen"), list):
            err(errors, "meta.incremental is tooling-owned: {targets[], frozen[], updatedAt}")
    if meta.get("captureIsolated") is False and not meta.get("isolationNote"):
        err(errors, "meta.captureIsolated=false requires meta.isolationNote (R1: state the session caveat)")
    if meta.get("crawl"):
        crawl = meta["crawl"]
        if not isinstance(crawl.get("pages"), list) or not crawl["pages"]:
            err(errors, "meta.crawl.pages must list the inspected pages")
        elif len(crawl["pages"]) > 4 and crawl.get("budget") != "user-expanded":
            err(errors, "meta.crawl.pages exceeds 1+3 budget; set meta.crawl.budget='user-expanded'")

    evidence = dna.get("evidence")
    ev_ids: set[str] = set()
    if not isinstance(evidence, list) or not evidence:
        err(errors, "evidence must be a non-empty list")
        evidence = []
    for e in evidence:
        if not isinstance(e, dict):
            err(errors, "evidence entries must be objects")
            continue
        eid = e.get("id")
        if not isinstance(eid, str) or not eid:
            err(errors, "evidence.id required")
            continue
        if eid in ev_ids:
            err(errors, f"duplicate evidence id: {eid}")
        ev_ids.add(eid)
        for key in ("url", "locator", "method", "capturedAt"):
            if not isinstance(e.get(key), str) or not e.get(key):
                err(errors, f"evidence[{eid}].{key} required")
        if not isinstance(e.get("viewport"), dict) or "width" not in e.get("viewport", {}):
            err(errors, f"evidence[{eid}].viewport {{width,height}} required")
        if not isinstance(e.get("values"), dict) or not e.get("values"):
            err(errors, f"evidence[{eid}].values must be a non-empty object")
        if e.get("status") not in STATUSES:
            err(errors, f"evidence[{eid}].status must be one of {STATUSES}")

    def check_refs(where: str, refs) -> None:
        if not isinstance(refs, list) or not refs:
            err(errors, f"{where} must reference at least one evidence id")
            return
        for r in refs:
            if r not in ev_ids:
                err(errors, f"{where} references unknown evidence id {r!r}")

    measurements = dna.get("measurements")
    if not isinstance(measurements, list) or not measurements:
        err(errors, "measurements must be a non-empty list")
        measurements = []
    m_ids: set[str] = set()
    for m in measurements:
        if not isinstance(m, dict):
            err(errors, "measurement entries must be objects")
            continue
        mid = m.get("id")
        if not isinstance(mid, str) or not mid:
            err(errors, "measurement.id required")
            continue
        if mid in m_ids:
            err(errors, f"duplicate measurement id: {mid}")
        m_ids.add(mid)
        if not isinstance(m.get("category"), str) or not m["category"]:
            err(errors, f"measurement[{mid}].category required")
        if not isinstance(m.get("value"), str) or not m["value"]:
            err(errors, f"measurement[{mid}].value must be a string with units (px/hex/ratio)")
        if m.get("status") not in STATUSES:
            err(errors, f"measurement[{mid}].status must be one of {STATUSES}")
        check_refs(f"measurement[{mid}].evidence", m.get("evidence"))

    patterns = dna.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        err(errors, "patterns must be a non-empty list")
        patterns = []
    p_ids: set[str] = set()
    for p in patterns:
        if not isinstance(p, dict):
            err(errors, "pattern entries must be objects")
            continue
        pid = p.get("id")
        if not isinstance(pid, str) or not pid:
            err(errors, "pattern.id required")
            continue
        if pid in p_ids:
            err(errors, f"duplicate pattern id: {pid}")
        p_ids.add(pid)
        for key in ("name", "rule"):
            if not isinstance(p.get(key), str) or not p[key]:
                err(errors, f"pattern[{pid}].{key} required")
        check_refs(f"pattern[{pid}].evidence", p.get("evidence"))
        if not isinstance(p.get("goal"), str) or not p["goal"]:
            err(errors, f"pattern[{pid}].goal required (function, not philosophy)")

    taste = dna.get("taste")
    if not isinstance(taste, list) or not taste:
        err(errors, "taste must be a non-empty list (3-4 principles)")
        taste = []
    t_ids: set[str] = set()
    restrains = 0
    for t in taste:
        if not isinstance(t, dict):
            err(errors, "taste entries must be objects")
            continue
        tid = t.get("id")
        if not isinstance(tid, str) or not tid:
            err(errors, "taste.id required")
            continue
        if tid in t_ids:
            err(errors, f"duplicate taste id: {tid}")
        t_ids.add(tid)
        for key in ("name", "trigger", "decision", "reason"):
            if not isinstance(t.get(key), str) or not t[key]:
                err(errors, f"taste[{tid}].{key} required")
        if not isinstance(t.get("chose"), str) or not t["chose"]:
            err(errors, f"taste[{tid}].chose required (the chosen direction)")
        if not isinstance(t.get("over"), str) or not t["over"]:
            err(errors, f"taste[{tid}].over required (the plausible rejected alternative)")
        if t["chose"].strip().lower() == t["over"].strip().lower():
            err(errors, f"taste[{tid}] chose and over are identical — not a trade-off")
        check_refs(f"taste[{tid}].evidence", t.get("evidence"))
        refs = t.get("patterns")
        if not isinstance(refs, list) or not refs:
            err(errors, f"taste[{tid}].patterns must cite at least one pattern id")
        else:
            for r in refs:
                if r not in p_ids:
                    err(errors, f"taste[{tid}] cites unknown pattern {r!r}")
        if t.get("status") not in STATUSES:
            err(errors, f"taste[{tid}].status must be one of {STATUSES}")
        if t.get("kind") == "restraint":
            restrains += 1
            g = t.get("guardrail")
            if not isinstance(g, dict) or not g:
                err(errors, f"taste[{tid}] is a restraint and MUST carry a guardrail (machine-readable)")
            else:
                validate_guardrail(errors, tid, g)
        elif t.get("kind") != "craft" and t.get("kind") != "system":
            err(errors, f"taste[{tid}].kind must be restraint|craft|system")
    if taste and restrains < 1:
        err(errors, "at least one taste principle must be kind=restraint (with guardrail)")

    interactions = dna.get("interactions")
    if interactions is not None:
        if not isinstance(interactions, list) or not interactions:
            err(errors, "interactions must be a non-empty list when present")
            interactions = []
        seen_loc = set()
        for it in interactions:
            if not isinstance(it, dict):
                err(errors, "interaction entries must be objects")
                continue
            loc = it.get("locator")
            if not isinstance(loc, str) or not loc:
                err(errors, "interaction.locator required")
                continue
            if loc in seen_loc:
                err(errors, f"duplicate interaction locator: {loc}")
            seen_loc.add(loc)
            if it.get("kind") not in ("button", "link", "card", "input"):
                err(errors, f"interaction[{loc}].kind must be button|link|card|input")
            if it.get("status") not in STATUSES:
                err(errors, f"interaction[{loc}].status must be one of {STATUSES}")
            check_refs(f"interaction[{loc}].evidence", it.get("evidence"))
            for phase in ("hover", "focus"):
                delta = (it.get(phase) or {}).get("delta", {})
                if not isinstance(delta, dict):
                    err(errors, f"interaction[{loc}].{phase}.delta must be an object")
                    continue
                for prop, pair in delta.items():
                    if prop not in INTERACTION_PROPS:
                        err(errors, f"interaction[{loc}].{phase}.delta.{prop} is not a diffed property {INTERACTION_PROPS}")
                    if not isinstance(pair, list) or len(pair) != 2:
                        err(errors, f"interaction[{loc}].{phase}.delta.{prop} must be [before, after]")
            recorded = [
                k for k in ("hover", "focus")
                if isinstance(it.get(k), dict) and isinstance(it[k].get("delta"), dict) and it[k]["delta"]
            ]
            if it.get("status") == "observed" and not recorded:
                err(errors, f"interaction[{loc}] is observed but records no hover/focus delta")

    tokens = dna.get("tokens")
    if not isinstance(tokens, list) or not tokens:
        err(errors, "tokens must be a non-empty list")
        tokens = []
    seen_ids: set[str] = set()
    seen_css: set[str] = set()
    by_id: dict[str, dict] = {}
    for tk in tokens:
        if not isinstance(tk, dict):
            err(errors, "token entries must be objects")
            continue
        tid = tk.get("id")
        if not isinstance(tid, str) or not tid:
            err(errors, "token.id required")
            continue
        if tid in seen_ids:
            err(errors, f"duplicate token id: {tid}")
        seen_ids.add(tid)
        by_id[tid] = tk
        css = tk.get("css")
        if not isinstance(css, str) or not re.fullmatch(r"--[a-z0-9-]+", css or ""):
            err(errors, f"token[{tid}].css must look like --kebab-case")
        elif css in seen_css:
            err(errors, f"duplicate token css name: {css}")
        else:
            seen_css.add(css)
        if tk.get("type") not in TOKEN_TYPES:
            err(errors, f"token[{tid}].type must be one of {TOKEN_TYPES}")
        if tk.get("layer") not in LAYERS:
            err(errors, f"token[{tid}].layer must be one of {LAYERS}")
        if tk.get("status") not in ("observed", "inferred", "proposed"):
            err(errors, f"token[{tid}].status must be observed|inferred|proposed (unknowns stay out)")
        if tk.get("status") in ("observed", "inferred") and not tk.get("evidence"):
            err(errors, f"token[{tid}] status={tk['status']} requires evidence")
        for eid in tk.get("evidence") or []:
            if eid not in ev_ids:
                err(errors, f"token[{tid}] references unknown evidence {eid!r}")
        values = tk.get("values")
        if not isinstance(values, dict) or not values:
            err(errors, f"token[{tid}].values must map mode -> literal|{{alias}}")
            continue
        for mode, v in values.items():
            if isinstance(v, dict):
                target = v.get("alias")
                if not isinstance(target, str):
                    err(errors, f"token[{tid}].values[{mode}] alias must be a string")
                elif target == tid:
                    err(errors, f"token[{tid}] aliases itself")
            elif isinstance(v, str):
                if not v:
                    err(errors, f"token[{tid}].values[{mode}] empty literal")
                elif tk.get("type") in UNIT_TYPES and not re.search(r"(px|rem|em|%|s|ms|ch)$", v):
                    err(errors, f"token[{tid}].values[{mode}] needs an explicit unit")
            else:
                err(errors, f"token[{tid}].values[{mode}] must be a string or {{alias}}")

    # alias integrity: target exists, same type, no cycle, all modes resolvable
    for tid, tk in by_id.items():
        vals = tk.get("values") or {}
        for mode, v in vals.items():
            if not isinstance(v, dict):
                continue
            target = v.get("alias")
            if target not in by_id:
                err(errors, f"token[{tid}] aliases missing token {target!r}")
                continue
            if by_id[target].get("type") != tk.get("type"):
                err(errors, f"token[{tid}] ({tk.get('type')}) aliases {target} of type {by_id[target].get('type')}")
            if mode not in (by_id[target].get("values") or {}):
                err(errors, f"token[{tid}] needs mode {mode!r} that {target} does not define")
            seen, cur, m = [], tid, mode
            while cur in by_id and cur not in seen:
                seen.append(cur)
                cv = (by_id[cur].get("values") or {}).get(m)
                if isinstance(cv, dict) and cv.get("alias") in by_id:
                    cur = cv["alias"]
                else:
                    break
            else:
                if cur in seen:
                    err(errors, f"alias cycle: {' -> '.join(seen + [cur])}")
    return errors


def validate_guardrail(errors: list[str], tid: str, g: dict) -> None:
    allowed = {"forbidCss", "requireCss", "forbidClass", "max", "note"}
    for k in g:
        if k not in allowed:
            err(errors, f"taste[{tid}].guardrail unknown key {k!r} (allowed: {sorted(allowed)})")
    for k in ("forbidCss", "requireCss", "forbidClass"):
        v = g.get(k, [])
        if not isinstance(v, list) or not all(isinstance(x, str) and x for x in v):
            err(errors, f"taste[{tid}].guardrail.{k} must be a list of non-empty strings")
    mx = g.get("max", {})
    if not isinstance(mx, dict):
        err(errors, f"taste[{tid}].guardrail.max must be an object")
    for prop, lim in mx.items():
        if not isinstance(lim, dict):
            err(errors, f"taste[{tid}].guardrail.max.{prop} must be {{value,unit}}")


# ---------------------------------------------------------------- resolve
def resolve_tokens(tokens: list[dict], mode: str) -> dict[str, dict]:
    by_id = {t["id"]: t for t in tokens}

    def resolve(tid: str, stack=()) -> str:
        if tid in stack:
            raise SchemaError(f"alias cycle at {tid}")
        v = by_id[tid]["values"].get(mode)
        if isinstance(v, dict):
            return resolve(v["alias"], stack + (tid,))
        return v

    return {t["id"]: {**t, "resolved": resolve(t["id"])} for t in tokens}


# ---------------------------------------------------------------- render
LABEL = {
    "observed": "Observed / 实测",
    "inferred": "Inferred / 推断",
    "proposed": "Proposed / 补全提案",
    "unknown": "Unknown / 未知",
}


def md(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _interaction_lines(dna: dict) -> list[str]:
    items = dna.get("interactions") or []
    if not items:
        return []
    out = ["## Interaction Delta (measured)", "",
           "Forced with a real mouse (CDP `Input.dispatchMouseEvent`) and `element.focus()`; only these "
           "properties are diffed: " + ", ".join("`" + p + "`" for p in INTERACTION_PROPS) + ".", ""]
    for it in items:
        out.append("### " + it["kind"] + " — `" + it["locator"] + "`")
        out.append("- Status: " + LABEL.get(it["status"], it["status"]) +
                   " · evidence: " + (", ".join(it.get("evidence") or []) or "—"))
        for phase in ("hover", "focus"):
            ph = it.get(phase) or {}
            delta = ph.get("delta") or {}
            if delta:
                changes = "; ".join("`" + k + "`: `" + str(v[0]) + "` → `" + str(v[1]) + "`" for k, v in delta.items())
                out.append("- **" + phase + "**: " + changes)
            else:
                note = ph.get("note") or ("measured, no computed change" if ph.get("measured", True) else "not measured")
                if note and note[0].islower() and not note.startswith("no "):
                    note = note[0].upper() + note[1:]
                out.append("- **" + phase + "**: none (" + note + ")")
        out.append("")
    return out


def render_taste_md(dna: dict) -> str:
    meta, res = dna["meta"], ""
    out: list[str] = []
    out.append(f"# {meta['name']} — Design DNA")
    out.append("")
    out.append(f"- Source: {meta['source']}")
    out.append(f"- Mode: {meta['mode']}  ·  Captured: {meta.get('capturedAt', 'unknown')}")
    pages = (meta.get("crawl") or {}).get("pages") or [meta["source"]]
    out.append(f"- Pages inspected: {len(pages)} ({', '.join(pages)})")
    inc = meta.get("incremental")
    if inc:
        out.append(f"- Incremental run: scope {', '.join(inc['targets'])}; frozen {', '.join(inc['frozen'])} (at {inc['updatedAt']})")
    iso = "isolated (fresh context)" if meta.get("captureIsolated") else "NOT isolated"
    out.append(f"- Browser capture: {iso}")
    if meta.get("isolationNote"):
        out.append(f"  - Caveat: {meta['isolationNote']}")
    if meta.get("viewport"):
        out.append(f"- Viewport: {meta['viewport']}")
    if meta.get("limitations"):
        out.append("- Limitations:")
        for lim in meta["limitations"]:
            out.append(f"  - {lim}")
    out.append("")

    out.append("## Design Map")
    out.append("")
    out.append("### Measurements")
    out.append("")
    out.append("| Category | Value | Status | Evidence |")
    out.append("| --- | --- | --- | --- |")
    for m in dna["measurements"]:
        out.append(f"| {md(m['category'])} | `{md(m['value'])}` | {LABEL[m['status']]} | {', '.join(m['evidence'])} |")
    out.append("")

    out.append("### Patterns")
    out.append("")
    for p in dna["patterns"]:
        out.append(f"**{p['name']}** — {p['rule']}")
        out.append(f"- Goal: {p['goal']}")
        out.append(f"- Evidence: {', '.join(p['evidence'])}")
        out.append("")

    out.append("### Tokens")
    out.append("")
    out.append("| Token | CSS var | Type | Layer | Status | Value |")
    out.append("| --- | --- | --- | --- | --- | --- |")
    for t in dna["tokens"]:
        modes = next(iter(t["values"].values()))
        shown = next(iter(t["values"].values())) if len(t["values"]) == 1 else t["values"]
        if isinstance(shown, dict):
            shown = f"→ {shown.get('alias')}"
        out.append(
            f"| `{md(t['id'])}` | `{t['css']}` | {t['type']} | {t['layer']} | {t['status']} | `{md(shown)}` |"
        )
    out.append("")
    out.append("---")
    out.append("")
    out.append("# Taste DNA")
    out.append("")
    for t in dna["taste"]:
        out.append(f"### {t['name']}")
        out.append(f"- **Kind**: {t['kind']}")
        out.append(f"- **Trigger**: {t['trigger']}")
        out.append(f"- **Decision**: {t['decision']}")
        out.append(f"- **Chose**: {t['chose']}   **Over**: {t['over']}")
        out.append(f"- **Reason**: {t['reason']}")
        out.append(f"- **Evidence**: {', '.join(t['evidence'])}  ·  patterns: {', '.join(t.get('patterns', []))}")
        out.append(f"- **Status**: {LABEL.get(t['status'], t['status'])}")
        if t["kind"] == "restraint":
            g = t.get("guardrail")
            out.append(f"- **Guardrail (enforced)**: `{json.dumps(g, ensure_ascii=False)}`" if g else "- **Guardrail (enforced)**: MISSING — schema gate must fail")
        out.append("")
    out.extend(_interaction_lines(dna))
    if meta.get("openQuestions"):
        out.append("## Open questions")
        out.append("")
        for q in meta["openQuestions"]:
            out.append(f"- {q}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def render_tokens_css(dna: dict) -> str:
    modes = dna["meta"].get("modes") or ["default"]
    out = [
        "/* Generated by lewitt from dna.json — do not edit by hand (R3: single source). */",
        "/* Scope: apply [data-ds] (and [data-ds-mode=\"<mode>\"] for non-default modes). */",
        "",
        ":root, [data-ds] {",
    ]
    res = resolve_tokens(dna["tokens"], modes[0])
    for t in dna["tokens"]:
        out.append(f"  {t['css']}: {res[t['id']]['resolved']}; /* {t['id']} · {t['status']} */")
    out.append("}")
    for mode in modes[1:]:
        out.append("")
        out.append(f'[data-ds][data-ds-mode="{mode}"], [data-ds-mode="{mode}"] {{')
        mres = resolve_tokens(dna["tokens"], mode)
        for t in dna["tokens"]:
            out.append(f"  {t['css']}: {mres[t['id']]['resolved']};")
        out.append("}")
    return "\n".join(out) + "\n"


def render_resolved_json(dna: dict) -> str:
    modes = dna["meta"].get("modes") or ["default"]
    payload = {"source": dna["meta"]["source"], "name": dna["meta"]["name"], "modes": {}, "tokens": []}
    resolved_by_mode = {m: resolve_tokens(dna["tokens"], m) for m in modes}
    for t in dna["tokens"]:
        payload["tokens"].append(
            {
                "id": t["id"],
                "css": t["css"],
                "type": t["type"],
                "layer": t["layer"],
                "status": t["status"],
                "evidence": t.get("evidence", []),
                "values": {m: resolved_by_mode[m][t["id"]]["resolved"] for m in modes},
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def render_agent_rules(dna: dict) -> str:
    meta = dna["meta"]
    out: list[str] = []
    out.append(f"# Design rules — {meta['name']}")
    out.append("")
    out.append(f"<!-- source: {meta['source']} · generated by lewitt from dna.json · do not edit -->")
    out.append("")
    out.append("## Hard constraints (from Restraint principles — check these first)")
    out.append("")
    guards = [t for t in dna["taste"] if t["kind"] == "restraint"]
    if not guards:
        out.append("- (none captured)")
    for t in guards:
        g = t["guardrail"]
        out.append(f"### MUST NOT — {t['name']}")
        out.append(f"_{t['decision']}_")
        out.append("")
        if g.get("forbidCss"):
            out.append(f"- Forbidden CSS properties: `{'`, `'.join(g['forbidCss'])}`")
        if g.get("requireCss"):
            out.append(f"- Required CSS properties: `{'`, `'.join(g['requireCss'])}`")
        if g.get("forbidClass"):
            out.append(f"- Forbidden class patterns: `{'`, `'.join(g['forbidClass'])}`")
        for prop, lim in (g.get("max") or {}).items():
            out.append(f"- Upper bound: `{prop}` ≤ {lim['value']}{lim.get('unit', '')}")
        out.append(f"- Why: {t['reason']}")
        if g.get("note"):
            out.append(f"- Note: {g['note']}")
        out.append("")
    out.append("## Design principles")
    out.append("")
    for t in dna["taste"]:
        out.append(f"### {t['name']} [{t['kind']}]")
        out.append(f"- {t['trigger']} → **{t['chose']}** over _{t['over']}_")
        out.append(f"- Because: {t['reason']}")
        out.append(f"- Evidence: {', '.join(t['evidence'])}")
        out.append("")
    out.append("## System rules")
    out.append("")
    for p in dna["patterns"]:
        out.append(f"- **{p['name']}**: {p['rule']}")
    out.append("")
    out.append("## Tokens (copy values from tokens.css; never retype numbers)")
    out.append("")
    out.append("Use the semantic and component layers; reach for a primitive only when no role fits.")
    out.append("")
    for layer, heading in (("semantic", "Semantic — roles to use"), ("component", "Component — reusable parts"),
                           ("primitive", "Primitives — raw values, last resort")):
        layer_tokens = [t for t in dna["tokens"] if t["layer"] == layer]
        if not layer_tokens:
            continue
        out.append(f"### {heading}")
        out.append("")
        for t in layer_tokens:
            out.append(f"- `var({t['css']})` — {t['id']} ({t['type']}, {t['status']})")
        out.append("")
    out.extend(_interaction_lines(dna))
    out.append("## Verification")
    out.append("")
    out.append("Live specimens and motion replay: `preview.html` (single file, opens in any browser).")
    out.append("")
    out.append("Run before shipping UI built from these rules:")
    out.append("")
    out.append("```sh")
    out.append("python3 scripts/lint_output.py --dest <dest_dir> --check-code <ui_dir>")
    out.append("```")
    out.append("")
    return "\n".join(out)


def render_verify_md(dest: Path, result: dict) -> str:
    meta = result.get("meta") or {}
    inc = meta.get("incremental")
    out: list[str] = [f"# VERIFY — {meta.get('name', dest.name)}", ""]
    out.append("Renders are deterministic re-encodings of `dna.json`: byte-equality proves the artifacts "
               "were not edited after rendering, not that every authored value is faithful. "
               "Fidelity stays `unverified` until a comparison is recorded.")
    if inc:
        out.append("")
        out.append(f"Last run: **incremental** — scope `{', '.join(inc['targets'])}`; "
                   f"frozen `{', '.join(inc['frozen'])}`.")
    out.append("")
    out.append("| Check | Result | Detail |")
    out.append("| --- | --- | --- |")
    for row in result["checks"]:
        out.append(f"| {md(row['name'])} | {row['result']} | {md(row.get('detail', ''))} |")
    out.append("")
    out.append(f"Generated at {result.get('generatedAt', 'unknown')}.")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------- CLI
def load_previous(dest: Path) -> dict | None:
    """Last rendered state (verify.json records which blocks were frozen)."""
    path = dest / "verify.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def load_dna(dest: Path) -> dict:
    path = dest / "dna.json"
    if not path.exists():
        sys.exit(f"FAIL: {path} not found — dna.json is the single source of truth")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"FAIL: dna.json is not valid JSON: {exc}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Render artifacts from dna.json (SSOT)")
    ap.add_argument("dest", help="output directory {dest}/{domain}/")
    ap.add_argument("--incremental", metavar="SCOPE",
                    help="comma list of blocks this run may change; everything else is frozen. "
                         "Any of: evidence,measurements,patterns,taste,tokens")
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    ap.add_argument("--export", default="all", choices=["all", "shadcn", "css"],
                    help="which generated stylesheets to write: all (default), shadcn-theme.css only, or tokens.css only")
    ap.add_argument("--print-theme", action="store_true", help="print shadcn-theme.css to stdout and exit")
    ap.add_argument("--force", action="store_true", help="allow tokens to change in incremental mode")
    ap.add_argument("--updated-at", default=None, help="ISO timestamp recorded in meta.incremental")
    args = ap.parse_args()

    dest = Path(args.dest).expanduser().resolve()
    dna = load_dna(dest)

    frozen: list[str] = []
    if args.incremental:
        blocks = [b.strip() for b in args.incremental.split(",") if b.strip()]
        bad = [b for b in blocks if b not in RERUNNABLE]
        if bad:
            sys.exit(f"FAIL: cannot rerun {bad}; the scope may only name {list(RERUNNABLE)} "
                     "(meta is tooling-owned and always frozen)")
        if not blocks:
            sys.exit("FAIL: empty --incremental scope")
        frozen = [b for b in BLOCKS if b not in blocks]
        dna["meta"]["incremental"] = {
            "targets": blocks,
            "frozen": frozen,
            "updatedAt": args.updated_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        previous = load_previous(dest)
        if previous:
            prev_dna = dict(previous.get("dna") or {})
            prev_dna.pop("meta", None)          # tooling owns meta.incremental; ignore it
            cur = dict(dna)
            cur.pop("meta", None)
            frozen = dna["meta"]["incremental"]["frozen"]
            moved = [b for b in frozen if b != "meta" and prev_dna.get(b) != cur.get(b)]
            if moved:
                sys.exit(
                    f"FAIL: frozen block(s) changed during an incremental run: {moved}. "
                    "Incremental runs may only modify "
                    f"{blocks}; rerun the whole pipeline, or restore these blocks from git."
                )
            # tokens follow the evidence they derive from: changing tokens while evidence
            # is frozen means the numbers moved without new proof. Declare evidence in scope,
            # or pass --force when you have the evidence but no re-observation (e.g. a colour
            # from the screenshot) and say why in meta.limitations.
            before = prev_dna.get("tokens")
            if (before is not None and before != dna.get("tokens")
                    and "evidence" not in blocks and not args.force):
                sys.exit(
                    "FAIL: tokens changed but the evidence block was frozen. "
                    "Add evidence to the scope (recommended), or pass --force and record "
                    "the reason in meta.limitations."
                )

    errors = validate(dna)
    if errors:
        print(f"FAIL: dna.json violates the contract ({len(errors)} error(s))")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK: dna.json schema valid ({len(dna['evidence'])} evidence, {len(dna['measurements'])} measurements, "
          f"{len(dna['patterns'])} patterns, {len(dna['taste'])} taste, {len(dna['tokens'])} tokens)",
          file=(sys.stderr if args.print_theme else sys.stdout))
    if args.check:
        return 0

    if args.incremental:
        (dest / "dna.json").write_text(json.dumps(dna, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  recorded scope in {dest / 'dna.json'} (meta.incremental)")

    if args.print_theme:
        print(render_shadcn_theme(dna), end="")
        return 0
    artifacts = {
        "taste.md": render_taste_md(dna),
        "tokens.resolved.json": render_resolved_json(dna),
        "agent-rules.md": render_agent_rules(dna),
        "preview.html": render_preview_html(dna, dest),
    }
    if args.export in ("all", "css"):
        artifacts["tokens.css"] = render_tokens_css(dna)
    if args.export in ("all", "shadcn"):
        artifacts["shadcn-theme.css"] = render_shadcn_theme(dna)
    for name, content in artifacts.items():
        (dest / name).write_text(content, encoding="utf-8")
        print(f"  wrote {dest / name} ({len(content)} bytes)")

    # record exactly what was rendered, so the next incremental run can prove the frozen
    # blocks did not move (and lint_output.py can gate on the same fact)
    prev = load_previous(dest) or {}
    record = {
        "generatedAt": (args.updated_at if args.incremental else None)
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "renderedBy": RENDERER_VERSION,
        "dna": dna,
        "checks": prev.get("checks", []),
        "note": "verify.json: `dna` is the exact state last rendered; rerun lint_output.py to refresh checks",
    }
    (dest / "verify.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # keep a readable VERIFY.md even before lint runs, so the incremental scope is never invisible
    checks = record["checks"] or [{"name": "gates", "result": "unverified", "detail": "run lint_output.py"}]
    (dest / "VERIFY.md").write_text(
        render_verify_md(dest, {"meta": dna.get("meta"), "checks": checks, "generatedAt": record["generatedAt"]}),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())


