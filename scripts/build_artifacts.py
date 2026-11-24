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


# ============================================================================ system/ (full mode)
SITE_CSS = """
/* site.css — what the system/ page adds on top of the neutral chrome. The system's own colour
   only appears inside [data-ds]; everything else is chrome. */

/* ---- typography seen from the catalogue */
.type-row { display: grid; grid-template-columns: 220px minmax(0, 1fr); border-top: 1px solid var(--n-line); }
.type-row:last-child { border-bottom: 1px solid var(--n-line); }
.type-params { padding: 20px 24px 20px 0; border-right: 1px solid var(--n-line); }
.type-params .mono { color: var(--n-ink); display: block; margin-bottom: 8px; }
.type-params dl { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 3px 14px; font: 11.5px/1.5 var(--n-mono); }
.type-params dt { color: var(--n-faint); }
.type-params dd { margin: 0; color: var(--n-ink); text-align: right; }
.type-specimen { padding: 20px 0 20px 32px; overflow: hidden; }
.type-specimen .spec { display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  color: var(--n-ink); letter-spacing: -.02em; line-height: 1.1; }

/* ---- colour catalogue */
.sw { display: grid; grid-template-columns: repeat(auto-fill, minmax(188px, 1fr)); gap: 0;
  border: 1px solid var(--n-line); border-right: 0; border-bottom: 0; }
.swatch { border-right: 1px solid var(--n-line); border-bottom: 1px solid var(--n-line); background: var(--n-panel); }
.swatch .fill { height: 96px; border-bottom: 1px solid var(--n-line); }
.swatch .line { display: flex; justify-content: space-between; gap: 8px; padding: 10px 12px 0;
  font: 12px/1.3 var(--n-mono); }
.swatch .line .hex { color: var(--n-mute); }
.swatch .sub { padding: 4px 12px 12px; }
.pairs { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1px;
  background: var(--n-line); border: 1px solid var(--n-line); }
.pair { background: var(--n-panel); padding: 18px 20px; }
.pair .sample { padding: 14px 16px; border-radius: 2px; font-size: 14px; }
.pair .pmeta { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-top: 12px; }
.pair .pmeta .mono { color: var(--n-mute); font-size: 11px; }

/* ---- shape */
.grid-2 { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 1px;
  background: var(--n-line); border: 1px solid var(--n-line); }
.shape { background: var(--n-panel); padding: 20px; }
.shape .obj { height: 72px; background: var(--n-hover); border: 1px solid var(--n-line-strong); }
.shape .cap { display: flex; justify-content: space-between; gap: 8px; margin-top: 12px; font: 12px/1.4 var(--n-mono); }
.shape .cap .v { color: var(--n-mute); text-align: right; word-break: break-all; }

/* ---- compositions and fields sit on the system surface inside a stage */
.comp { padding: 0; }
.comp .stage-body { padding: 0; }
.comp [data-ds] { padding: 0; }

/* ---- taste cards */
.taste { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 1px;
  background: var(--n-line); border: 1px solid var(--n-line); }
.tcard { background: var(--n-panel); padding: 24px; display: grid; gap: 12px; }
.tcard .head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.tcard h4 { margin: 0; font-size: 15px; font-weight: 500; }
.tcard .ab { display: grid; grid-template-columns: 1fr 22px 1fr; gap: 10px; align-items: center; font-size: 13px; }
.tcard .ab .v { padding: 10px 12px; border: 1px solid var(--n-line-strong); border-radius: 2px; background: var(--n-bg); }
.tcard .ab .over { color: var(--n-mute); text-decoration: line-through; }
.tcard .ab .vs { text-align: center; color: var(--n-faint); font: 11px/1 var(--n-mono); }
.tcard .why { margin: 0; font-size: 13px; color: var(--n-mute); }

/* ---- motion */
.motion { display: grid; grid-template-columns: 196px minmax(0, 1fr) 120px; align-items: center;
  border-top: 1px solid var(--n-line); }
.motion:last-child { border-bottom: 1px solid var(--n-line); }
.motion .plot { padding: 16px 24px 16px 0; border-right: 1px solid var(--n-line); display: flex; align-items: center; }
.motion .mid { padding: 16px 24px; }
.motion .mid .ease { color: var(--n-mute); font: 11px/1.5 var(--n-mono); margin-top: 4px; word-break: break-all; }
.motion .act { padding: 16px 0; text-align: right; }
.track { height: 2px; background: var(--n-line-strong); margin-top: 14px; position: relative; }
.track .dot { position: absolute; top: -5px; left: 0; width: 12px; height: 12px; border-radius: 50%; background: var(--n-ink); }

@media (max-width: 900px) {
  .type-row { grid-template-columns: 1fr; }
  .type-params { border-right: 0; border-bottom: 1px solid var(--n-line); padding-right: 0; }
  .type-specimen { padding-left: 0; }
  .motion { grid-template-columns: 1fr; }
  .motion .plot { border-right: 0; }
}
"""


def render_site_files(dna: dict, dest: Path) -> dict[str, str]:
    """system/index.html + doc.css + system.js + site.css, all rendered from dna.json."""
    import site_render as sr
    import visual_base as vb

    meta = dna["meta"]
    mode = (meta.get("modes") or ["default"])[0]
    resolved = resolve_tokens(dna["tokens"], mode)
    canvas = next((resolved[t["id"]]["resolved"] for t in dna["tokens"] if t["id"] == "color/canvas"), None)
    tone = vb.tone_of(canvas)
    pages = meta.get("crawl", {}).get("pages") or [meta["source"]]
    esc = sr._esc
    panels: dict[str, str] = {}

    def stage(title, inner, *, meta_note="", note="", tight=False):
        head = (f'<div class="stage-head"><span>{title}</span><span>{meta_note}</span></div>'
                if title or meta_note else "")
        tail = f'<div class="stage-note">{note}</div>' if note else ""
        cls = "stage-body tight" if tight else "stage-body"
        return (f'<div class="stage">{head}<div class="{cls}"><div data-ds>{inner}</div></div>{tail}</div>')

    def badge(status: str) -> str:
        return f'<span class="badge {esc(status)}">{esc(status)}</span>'

    # ---------------------------------------------------------------- overview
    taste0 = dna["taste"][0]
    panels["overview"] = f"""
<h1>{esc(meta.get('name', ''))} — extracted design system</h1>
<p class="lede">{esc(meta['source'])} · captured {esc(str(meta.get('capturedAt', ''))[:19])} · every specimen below
reads <code>../tokens.css</code>, a deterministic render of <code>dna.json</code>.</p>
<div class="note"><strong>{esc(taste0['name'])}</strong> — {esc(taste0['reason'])}</div>
<h2>By the numbers</h2>
{sr.spec_table(["", "Value", "Reads"], [
    ["Tokens", str(len(dna["tokens"])), "semantic → component → primitive"],
    ["Evidence", str(len(dna["evidence"])), "every value cites an id"],
    ["Pages", str(len(pages)), "entry plus representative subpages"],
    ["Interactions", str(len(dna.get("interactions") or [])), "measured with real pointer and focus input"],
])}
<h2>Limitations</h2>
<ul>{''.join(f"<li>{esc(x)}</li>" for x in meta.get("limitations", []))}</ul>
"""

    # ---------------------------------------------------------------- colour
    def swatches(layer: str) -> str:
        toks = [t for t in dna["tokens"] if t["type"] == "color" and t["layer"] == layer]
        if not toks:
            return ""
        cells = "".join(
            f'<div class="swatch"><div class="fill" style="background:{esc(resolved[t["id"]]["resolved"])}"></div>'
            f'<div class="line"><span data-copy="{esc(resolved[t["id"]]["resolved"])}">{esc(t["id"])}</span>'
            f'<span class="hex" data-copy="var(--{esc(t["css"].lstrip("-"))})">{esc(resolved[t["id"]]["resolved"])}</span></div>'
            f'<div class="sub">{badge(t["status"])}</div></div>' for t in toks)
        return f'<h3>{layer} · {len(toks)}</h3><div class="sw">{cells}</div>'

    pairs = [("heading / canvas", "color/text/heading", "color/canvas", "display copy"),
             ("body / canvas", "color/text/body", "color/canvas", "paragraphs"),
             ("body / subtle", "color/text/body", "color/surface-subtle", "cards, raised rows"),
             ("action-fg / action-bg", "color/action/fg", "color/action/bg", "primary button"),
             ("link / canvas", "color/link", "color/canvas", "inline links")]
    pair_cells = ""
    for label, fg_id, bg_id, where in pairs:
        fg, bg = resolved.get(fg_id, {}).get("resolved"), resolved.get(bg_id, {}).get("resolved")
        if not fg or not bg:
            continue
        text, grade = vb.wcag_badge(fg, bg)
        pair_cells += (f'<div class="pair"><div class="sample" style="background:{esc(bg)};color:{esc(fg)}">{esc(label)}</div>'
                       f'<div class="pmeta"><span class="mono">{esc(where)}</span>'
                       f'<span class="chip {grade}">{esc(text)}</span></div></div>')
    panels["colour"] = f"""
<h1>Colour</h1>
<p class="lede">Roles before primitives. Ratios are computed from the two token values, not sampled from a screenshot.</p>
{swatches("semantic")}{swatches("component")}{swatches("primitive")}
<h2>Pairs in use</h2>
<div class="pairs">{pair_cells}</div>
"""

    # ---------------------------------------------------------------- typography + type scale
    def type_rows() -> str:
        return "".join(
            f'<div class="type-row"><div class="type-params">'
            f'<span class="mono" data-copy="var(--{esc(t["css"].lstrip("-"))})">{esc(t["id"])}</span>'
            f'<dl><dt>size</dt><dd>{esc(resolved[t["id"]]["resolved"])}</dd>'
            f'<dt>weight</dt><dd>{esc(resolved.get("weight/light", {}).get("resolved", "—"))}</dd></dl></div>'
            f'<div class="type-specimen"><span class="spec" style="font-size:{esc(resolved[t["id"]]["resolved"])};'
            f'font-weight:{esc(resolved.get("weight/light", {}).get("resolved", 400))};'
            f'letter-spacing:{esc(resolved.get("tracking/hero", {}).get("resolved", "normal"))}">'
            f'Financial infrastructure to grow your revenue</span></div></div>'
            for t in dna["tokens"] if t["type"] == "dimension" and t["id"].startswith("type/"))

    weight_rows = "".join(
        f'<div class="type-row"><div class="type-params"><span class="mono" data-copy="var(--{esc(t["css"].lstrip("-"))})">'
        f'{esc(t["id"])}</span><dl><dt>weight</dt><dd>{esc(resolved[t["id"]]["resolved"])}</dd></dl></div>'
        f'<div class="type-specimen"><span class="spec" style="font-size:32px;font-weight:{esc(resolved[t["id"]]["resolved"])}">'
        f'Financial infrastructure to grow your revenue</span></div></div>'
        for t in dna["tokens"] if t["type"] == "fontWeight")
    panels["typography"] = f"""
<h1>Typography</h1>
<p class="lede">Parameters on the left, the specimen on the right at its real size. Web fonts are not shipped;
the specimen uses the declared stack and falls back where the face is missing.</p>
{type_rows()}
<h2>Weights</h2>
{weight_rows}
"""
    panels["type-scale"] = f"""
<h1>Type Scale</h1>
<p class="lede">The full stack in reading order, drawn from the tokens exactly as a build would.</p>
{stage("type scale · ratios between steps",
       ''.join(f'<div style="font-size:{esc(resolved[t["id"]]["resolved"])};line-height:1.12;'
               f'font-weight:{esc(resolved.get("weight/light", {}).get("resolved", 400))};'
               f'letter-spacing:{esc(resolved.get("tracking/hero", {}).get("resolved", "normal"))};'
               f'margin:0 0 18px;color:var(--lw-text-heading)">Financial infrastructure</div>'
               for t in dna["tokens"] if t["type"] == "dimension" and t["id"].startswith("type/")),
       meta_note="on var(--lw-canvas)")}
"""

    # ---------------------------------------------------------------- shape
    radius_cells = "".join(
        f'<div class="shape"><div class="obj" style="border-radius:{esc(resolved[t["id"]]["resolved"])}"></div>'
        f'<div class="cap"><span data-copy="var(--{esc(t["css"].lstrip("-"))})">{esc(t["id"])}</span>'
        f'<span class="v">{esc(resolved[t["id"]]["resolved"])}</span></div></div>'
        for t in dna["tokens"] if t["type"] == "dimension" and t["id"].startswith("radius/"))
    shadow_cells = "".join(
        f'<div class="shape"><div class="obj" style="box-shadow:{esc(resolved[t["id"]]["resolved"])};border-color:transparent"></div>'
        f'<div class="cap"><span data-copy="var(--{esc(t["css"].lstrip("-"))})">{esc(t["id"])}</span>'
        f'<span class="v">{esc(resolved[t["id"]]["resolved"])}</span></div></div>'
        for t in dna["tokens"] if t["type"] == "shadow")
    panels["shape"] = f"""
<h1>Radius &amp; Depth</h1>
<p class="lede">Corners and layer separation as tokenised values.</p>
<div class="grid-2">{radius_cells}{shadow_cells or '<div class="shape"><div class="cap"><span>no shadow tokens</span><span class="v">layers are separated with 1px borders</span></div></div>'}</div>
"""

    # ---------------------------------------------------------------- components
    def button_matrix() -> str:
        cells = ""
        for label, cls, extra in (("default", "ds-btn--primary", ""), ("hover", "ds-btn--primary is-hover", "forced"),
                                  ("focus-visible", "ds-btn--primary is-focus", "forced"),
                                  ("active", "ds-btn--primary is-active", "forced"),
                                  ("disabled", "ds-btn--primary", "disabled")):
            attr = " disabled" if extra == "disabled" else ""
            cells += (f'<figure><div class="mono" style="color:var(--lw-text-muted);margin-bottom:6px">{label}'
                      + (f' · {extra}' if extra else "") + f'</div>'
                      f'<button class="ds-btn {cls}"{attr}>Get started</button></figure>')
        return f'<div class="matrix">{cells}</div>'

    def skin_supports(*classes: str) -> bool:
        path = dest / "system" / "system.css"
        if not path.exists():
            return False
        css = path.read_text(encoding="utf-8")
        return all(re.search(r"\." + re.escape(c) + r"(?![\w-])", css) for c in classes)

    def input_matrix() -> str:
        if not skin_supports("ds-input", "ds-field"):
            return ('<p class="lede" style="margin:0">This run recorded no form controls, so the skin ships no '
                    'input component. STATES below shows what was observed instead.</p>')
        cells = ""
        for label, cls, extra, invalid in (("default", "", "", False), ("hover", "is-hover", "forced", False),
                                           ("focus-visible", "is-focus", "forced", False),
                                           ("invalid", "is-invalid", "state", True), ("disabled", "", "disabled", False)):
            attr = " disabled" if extra == "disabled" else (' aria-invalid="true"' if invalid else "")
            cells += (f'<figure><div class="mono" style="color:var(--lw-text-muted);margin-bottom:6px">{label}'
                      + (f' · {extra}' if extra else "") + f'</div>'
                      f'<label class="ds-field"><span>Email</span>'
                      f'<input class="ds-input {cls}" placeholder="you@company.com"{attr}></label></figure>')
        return f'<div class="matrix">{cells}</div>'

    panels["components"] = f"""
<h1>Components &amp; States</h1>
<p class="lede">Every state is a real browser state; forced samples are labelled as such. The toolbar above
stresses the demos while you look at them.</p>
{stage("Button · default, hover, focus-visible, active, disabled", button_matrix(),
       meta_note="reads ../tokens.css", note="Hover and focus are real: move the pointer or press Tab.")}
{('<h2>Input</h2>' + stage("Input · default, hover, focus-visible, invalid, disabled", input_matrix(),
        note="Blur validation is live on this page: type into the live field below.")) if skin_supports("ds-input") else ''}
<h2>Cards &amp; links</h2>
{stage("Card surfaces", '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px">'
       '<div class="ds-card" style="padding:18px">Default card</div>'
       '<div class="ds-card ds-card--tint" style="padding:18px">Tint card</div>'
       '<div class="ds-card ds-card--float" style="padding:18px">Float card</div></div>'
       '<p style="margin:18px 0 0"><a class="ds-link" href="#components">Read the docs</a> · '
       '<a class="ds-link" href="#specs">view evidence</a></p>')}
"""

    # ---------------------------------------------------------------- compositions
    probes = ["Financial infrastructure to grow your revenue",
              "Accept payments and move money globally with a single integration",
              "Transparent pricing that scales with volume"]
    panels["compositions"] = f"""
<h1>Compositions</h1>
<p class="lede">Assembled only from the components above and the tokens in <code>../tokens.css</code>. Copy is
sample text, never the source's.</p>
<h2>Marketing hero</h2>
{stage("hero · display type, one action", '<div class="ds-scope" style="padding:48px">'
       + "".join(f'<h2 class="ds-hero ds-stressable" style="font-size:var(--lw-type-h2);margin:0 0 18px">{p}</h2>' for p in probes)
       + '<button class="ds-btn ds-btn--primary">Get started</button></div>',
       meta_note="display · 3 lengths", note="Long copy in the toolbar re-cuts these lines.")}
<h2>Pricing rows</h2>
{stage("pricing · three tiers", '<div class="ds-scope" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;padding:32px">'
       + "".join(f'<div class="ds-card" style="padding:20px"><div class="ds-caption">Tier</div>'
                 f'<div class="ds-price">{p}</div><button class="ds-btn ds-btn--secondary" style="margin-top:12px">Choose</button></div>'
                 for p in ("2.9% + 30¢", "1.5%", "Custom")) + '</div>',
       note="Card, caption and button states all come from the same tokens.")}
"""

    # ---------------------------------------------------------------- field states
    panels["states"] = (f"""
<h1>Field States</h1>
<p class="lede">The same input in five states, so a reviewer can compare without hovering anything.</p>
{stage("input states", '<div class="ds-scope" style="display:grid;gap:18px;padding:32px;max-width:420px">'
       + "".join(f'<label class="ds-field"><span>{label}</span>'
                 f'<input class="ds-input {cls}" placeholder="you@company.com"{attr}></label>'
                 for label, cls, attr in (("default", "", ""), ("hover (forced)", "is-hover", ""),
                                          ("focus-visible (forced)", "is-focus", ""),
                                          ("invalid", "is-invalid", ' aria-invalid="true"'),
                                          ("disabled", "", " disabled")))
       + '</div>', note="aria-invalid drives the invalid style, not a colour class.")}
""" if skin_supports("ds-input") else f"""
<h1>Field States</h1>
<p class="lede">No form controls were observed in this run, so this run has no field states to show.</p>
{stage("recorded states", '<div class="ds-scope" style="padding:24px"><button class="ds-btn ds-btn--primary" style="margin:0 8px 8px 0">Sign Up</button><button class="ds-btn ds-btn--secondary" style="margin:0 8px 8px 0">Log In</button><button class="ds-btn ds-btn--ghost">Deposit</button></div>',
       meta_note="buttons · observed", note="Only the controls below exist as tokens in this run.")}
""")

    # ---------------------------------------------------------------- motion
    easings = [t for t in dna["tokens"] if t["type"] == "easing"]
    durations = [t for t in dna["tokens"] if t["type"] == "duration"]
    easing_spec = resolved[easings[0]["id"]]["resolved"] if easings else "cubic-bezier(0.25, 0.1, 0.25, 1)"
    motion_rows = ""
    for t in durations:
        dur = resolved[t["id"]]["resolved"]
        dot_id = "dot-" + t["id"].split("/")[-1]
        motion_rows += (f'<div class="motion"><div class="plot">{vb.bezier_svg(easing_spec)}</div>'
                        f'<div class="mid"><div class="mono" data-copy="var(--{esc(t["css"].lstrip("-"))})">{esc(t["id"])} · {esc(dur)}</div>'
                        f'<div class="ease">{esc(easing_spec)}</div><div class="track"><span class="dot" id="{dot_id}"></span></div></div>'
                        f'<div class="act"><button class="tb-btn" data-sys-replay="{dot_id}" data-dur="{esc(dur)}" '
                        f'data-ease="{esc(easing_spec)}">Replay</button></div></div>')
    for t in easings:
        motion_rows += (f'<div class="motion"><div class="plot">{vb.bezier_svg(resolved[t["id"]]["resolved"])}</div>'
                        f'<div class="mid"><div class="mono" data-copy="var(--{esc(t["css"].lstrip("-"))})">{esc(t["id"])}</div>'
                        f'<div class="ease">{esc(resolved[t["id"]]["resolved"])}</div></div>'
                        f'<div class="act">{badge(t["status"])}</div></div>')
    inter_rows = "".join(
        f'<h3>{esc(i.get("kind"))} <span class="mono" style="color:var(--n-mute)">{esc(i.get("locator", "")[:48])}</span></h3>'
        + "".join(f'<p class="mono">{ph}: ' + ("; ".join(f"{esc(k)}: {esc(v[0])} → {esc(v[1])}" for k, v in (i[ph].get("delta") or {}).items())
                                                  or esc(i[ph].get("note", "no computed change"))) + "</p>"
                  for ph in ("hover", "focus") if isinstance(i.get(ph), dict))
        for i in (dna.get("interactions") or []))
    panels["motion"] = f"""
<h1>Motion</h1>
<p class="lede">Each curve is plotted from the token's own cubic-bezier. Replay runs the real duration.</p>
{motion_rows or '<p class="lede">No duration or easing tokens in this run.</p>'}
<h2>Interaction deltas</h2>
<p class="lede">Forced with a real CDP mouse and element.focus(); values come from <code>dna.json &gt; interactions</code>.</p>
{inter_rows or '<p class="lede">No interaction deltas recorded for this run.</p>'}
"""

    # ---------------------------------------------------------------- fidelity
    fid_panel = f"""
<h1>Fidelity vs Source</h1>
<p class="lede">The capture on the left, the rebuild on the right, at equal width. Differences stay visible
rather than claimed away.</p>
<div style="display:flex;justify-content:flex-end;margin:0 0 12px">
  <button class="tb-btn" id="compare-toggle" aria-pressed="true">Side by side</button>
</div>
<div class="compare" id="compare">
  <img src="../capture/viewport.png" alt="captured source page">
  <div class="layer b"><img src="../capture/viewport.png" alt=""></div>
  <div class="handle"></div>
  <span class="lab l">source · capture/viewport.png</span><span class="lab r">split compare</span>
  <input id="split" type="range" min="0" max="100" value="50" aria-label="compare source and rebuild">
</div>
<div class="sbs" id="sbs" hidden>
  <figure><img src="../capture/viewport.png" alt="captured source page" style="width:100%"><figcaption>source</figcaption></figure>
  <figure><div class="stage" style="border:0"><div class="stage-body" style="min-height:200px"><div data-ds style="padding:16px">
  the rebuild lives in <code>#compositions</code> and <code>#components</code> on this page</div></div></div>
  <figcaption>rebuild · this page</figcaption></figure>
</div>
<p class="note">Type rendering cannot be matched because the source face is not shipped. Fidelity stays
<strong>PARTIAL</strong> in VERIFY.md until every recorded deviation is closed.</p>
"""
    panels["fidelity"] = fid_panel

    # ---------------------------------------------------------------- system & taste
    def caps(guard: dict) -> str:
        if not guard:
            return ""
        out = "".join(f'<span class="rule-cap forbid">forbid · {esc(p)}</span>' for p in guard.get("forbidCss") or [])
        if guard.get("forbidClass"):
            out += f'<span class="rule-cap forbid">forbid · {len(guard["forbidClass"])} class pattern(s)</span>'
        out += "".join(f'<span class="rule-cap max">max · {esc(p)} ≤ {esc(b.get("value"))}{esc(b.get("unit", ""))}</span>'
                       for p, b in (guard.get("max") or {}).items())
        return f'<div>{out}</div>'

    taste_cards = "".join(
        f'<article class="tcard"><div class="head">{badge(t["status"])}'
        f'<span class="mono" style="color:var(--n-faint)">{esc(t["kind"])} · {esc(", ".join(t["evidence"]))}</span></div>'
        f'<h4>{esc(t["name"])}</h4>'
        f'<div class="ab"><div class="v">{esc(t["chose"])}</div><div class="vs">over</div>'
        f'<div class="v over">{esc(t["over"])}</div></div>'
        f'<p class="why">{esc(t["reason"])}</p>{caps(t.get("guardrail") or {})}'
        + (f'<details><summary>Machine rule</summary><pre>{esc(json.dumps(t["guardrail"], indent=1, ensure_ascii=False))}</pre></details>'
           if t.get("guardrail") else "")
        + '</article>' for t in dna["taste"])
    patterns = "".join(f'<h3>{esc(p["name"])}</h3><p><strong>{esc(p["rule"])}</strong></p>'
                       f'<p class="mono" style="color:var(--n-mute)">{esc(p["goal"])} · {esc(", ".join(p["evidence"]))}</p>'
                       for p in dna["patterns"])
    panels["system"] = f"""
<h1>System &amp; Taste</h1>
<p class="lede">The decision in words, the rule it compiles to, and the machine pattern behind it.</p>
<div class="taste">{taste_cards}</div>
<h2>Patterns</h2>
{patterns}
"""

    # ---------------------------------------------------------------- specs
    token_rows = "".join(
        f'<tr><td><span class="mono" data-copy="var(--{esc(t["css"].lstrip("-"))})">{esc(t["css"])}</span></td>'
        f'<td class="mono">{esc(t["id"])}</td><td>{esc(t["layer"])}</td><td>{esc(t["type"])}</td>'
        f'<td><span class="mono" data-copy="{esc(resolved[t["id"]]["resolved"])}">{esc(resolved[t["id"]]["resolved"])}</span></td>'
        f'<td>{badge(t["status"])}</td></tr>' for t in dna["tokens"])
    measure_rows = "".join(
        f'<tr><td>{esc(m["category"])}</td><td>{esc(m["value"])}</td><td>{badge(m["status"])}</td>'
        f'<td class="mono">{esc(", ".join(m["evidence"]))}</td></tr>' for m in dna["measurements"])
    evidence_rows = "".join(
        f'<tr><td class="mono">{esc(e["id"])}</td><td class="mono">{esc(e["url"].replace("https://", ""))}</td>'
        f'<td>{esc(e["locator"])}</td><td class="mono">{esc(e["method"])}</td><td>{badge(e["status"])}</td>'
        f'<td class="mono">{esc(", ".join(f"{k}={v}" for k, v in e["values"].items()))}</td></tr>' for e in dna["evidence"])

    def code_block(filename: str) -> str:
        path = dest / filename
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8")
        return (f'<div class="code" style="margin:0 0 20px"><div class="code-head"><span>{esc(filename)}</span>'
                f'<button class="mini-btn" data-copy="{esc(text)}">Copy</button></div>'
                f'<pre>{esc(text)}</pre></div>')

    panels["specs"] = f"""
<h1>Evidence &amp; Downloads</h1>
<div class="subtabs" role="tablist" aria-label="Specs">
  <button role="tab" id="tab-downloads" aria-controls="sub-downloads" aria-selected="true" tabindex="0">Downloads</button>
  <button role="tab" id="tab-code" aria-controls="sub-code" aria-selected="false" tabindex="-1">Code</button>
  <button role="tab" id="tab-tokens" aria-controls="sub-tokens" aria-selected="false" tabindex="-1">Tokens</button>
  <button role="tab" id="tab-measurements" aria-controls="sub-measurements" aria-selected="false" tabindex="-1">Measurements</button>
  <button role="tab" id="tab-evidence" aria-controls="sub-evidence" aria-selected="false" tabindex="-1">Evidence ({len(dna["evidence"])})</button>
</div>
<div class="tabpanel" id="sub-downloads" role="tabpanel" aria-labelledby="tab-downloads">
  <div class="dl">{''.join(f'<a class="mini-btn" href="../{f}" download>{f}</a>' for f in ("tokens.css", "shadcn-theme.css", "agent-rules.md", "taste.md", "VERIFY.md", "tokens.resolved.json"))}</div>
  <h3>Pages inspected</h3><ul>{''.join(f'<li><a href="{esc(p)}" rel="noreferrer">{esc(p)}</a></li>' for p in pages)}</ul>
  <h3>Limitations</h3><ul>{''.join(f"<li>{esc(x)}</li>" for x in meta.get("limitations", []))}</ul>
</div>
<div class="tabpanel" id="sub-code" role="tabpanel" aria-labelledby="tab-code" hidden>
  {code_block("tokens.css")}{code_block("shadcn-theme.css")}{code_block("agent-rules.md")}
</div>
<div class="tabpanel" id="sub-tokens" role="tabpanel" aria-labelledby="tab-tokens" hidden>
  {sr.spec_table(["CSS var", "Token", "Layer", "Type", "Value", "Status"], [])}
  <table><thead><tr><th>CSS var</th><th>Token</th><th>Layer</th><th>Type</th><th>Value</th><th>Status</th></tr></thead>
  <tbody>{token_rows}</tbody></table>
</div>
<div class="tabpanel" id="sub-measurements" role="tabpanel" aria-labelledby="tab-measurements" hidden>
  <table><thead><tr><th>Category</th><th>Value</th><th>Status</th><th>Evidence</th></tr></thead><tbody>{measure_rows}</tbody></table>
</div>
<div class="tabpanel" id="sub-evidence" role="tabpanel" aria-labelledby="tab-evidence" hidden>
  <table><thead><tr><th>ID</th><th>URL</th><th>Locator</th><th>Method</th><th>Status</th><th>Values</th></tr></thead>
  <tbody>{evidence_rows}</tbody></table>
</div>
"""

    html = sr.app_shell(dna, resolved, panels, pages=len(pages))
    # the promise that every specimen reads the run's tokens
    html = html.replace('<link rel="stylesheet" href="site.css">',
                        '<link rel="stylesheet" href="site.css">\n<style>:root { --doc-bg: '
                        + vb.TONES[tone]["bg"] + '; }</style>')
    js = sr.ROUTER_JS + """
// replay dots for the system/ motion panel
(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function msFrom(d) { var m = /([0-9.]+)\\s*(ms|s)/i.exec(String(d)); return m ? (m[2].toLowerCase() === 's' ? parseFloat(m[1]) * 1000 : parseFloat(m[1])) : 300; }
  Array.prototype.forEach.call(document.querySelectorAll('[data-sys-replay]'), function (btn) {
    var dot = document.getElementById(btn.getAttribute('data-sys-replay'));
    if (!dot) return;
    var dur = btn.getAttribute('data-dur'), ease = btn.getAttribute('data-ease');
    btn.addEventListener('click', function () {
      dot.style.transition = 'none'; dot.style.transform = 'translateX(0)'; void dot.offsetWidth;
      if (reduce) return;
      dot.style.transition = 'transform ' + dur + ' ' + ease;
      dot.style.transform = 'translateX(calc(100% - 12px))';
    });
  });
})();
"""
    evidence = json.dumps({"source": meta["source"], "capturedAt": meta.get("capturedAt"),
                           "evidence": dna["evidence"], "measurements": dna["measurements"]},
                          ensure_ascii=False, indent=2) + "\n"
    return {
        "system/index.html": html,
        "system/doc.css": vb.base_css(tone, scope=":root") + "\n" + sr.CHROME_CSS,
        "system/site.css": SITE_CSS,
        "system/system.js": js,
        "system/evidence.json": evidence,
        "system/system.css": (dest / "system" / "system.css").read_text(encoding="utf-8")
        if (dest / "system" / "system.css").exists() else "",
    }


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
    full = (dna.get("meta") or {}).get("mode") == "full"
    if args.export in ("all", "css"):
        artifacts["tokens.css"] = render_tokens_css(dna)
    if args.export in ("all", "shadcn"):
        artifacts["shadcn-theme.css"] = render_shadcn_theme(dna)
    if full:
        # the reference site is a render too: it must not drift from dna.json (R3)
        (dest / "system").mkdir(exist_ok=True)
        artifacts.update(render_site_files(dna, dest))
    for name, content in artifacts.items():
        if name.endswith("system/system.css"):
            continue          # hand-authored component skin, kept as-is
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


