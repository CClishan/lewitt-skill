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


# lewitt token ids are authored either with slashes (`color/text/primary`, Stripe) or with a dash
# (BEM / `.text-size` systems write `color/text-primary`, Steno.ai). These two forms are paired
# exactly — no fuzzy matching — so a slot never maps to an id its author did not write.
_DASHED = [
    "color/text/primary", "color/text/heading", "color/text/body", "color/text/muted",
    "color/text/secondary", "color/text/tertiary", "color/brand",
]


def _any(*ids: str) -> list[str]:
    out: list[str] = []
    for i in ids:
        out.append(i)
        if i in _DASHED:
            out.append(i.replace("color/", "color/", 1).replace("/", "-", 1))   # color/text-body
    return list(dict.fromkeys(out))


# the two spellings of one token are interchangeable candidates: (slashed, dashed)
def _pair(slashed: str, dashed: str) -> list[str]:
    return [slashed, dashed]


TEXT_UP = _pair("color/text/primary", "color/text-primary") + _pair("color/text/heading", "color/text-heading")
TEXT_BODY = _pair("color/text/body", "color/text-body")
TEXT_MUTED = (_pair("color/text/muted", "color/text-muted") + _pair("color/text/tertiary", "color/text-tertiary")
              + _pair("color/text/secondary", "color/text-secondary"))

SHADCN_SLOTS = [
    ("--background", ["color/canvas", "color/background", "color/surface/canvas"], "canvas"),
    ("--foreground", TEXT_UP + TEXT_BODY, "primary text"),
    ("--card", ["color/surface", "color/card", "color/surface/raised", "color/canvas-tint"], "raised surface"),
    ("--card-foreground", TEXT_UP + TEXT_BODY, "card text"),
    ("--popover", ["color/surface", "color/overlay", "color/card", "color/canvas"], "overlay surface"),
    ("--popover-foreground", TEXT_UP + TEXT_BODY, "overlay text"),
    ("--primary", ["color/action/bg", "color/action/primary", "color/brand", "color/accent"], "action fill"),
    ("--primary-foreground", ["color/action/fg", "color/on-brand", "color/text/on-action"], "action label"),
    ("--secondary", ["color/surface-subtle", "color/surface/muted", "color/well", "color/surface"], "secondary fill"),
    ("--secondary-foreground", TEXT_UP + TEXT_BODY, "secondary label"),
    ("--muted", ["color/surface-subtle", "color/well", "color/surface/muted", "color/surface"], "muted fill"),
    ("--muted-foreground", TEXT_MUTED, "muted text"),
    ("--accent", ["color/surface-subtle", "color/action/bg", "color/brand"], "hover fill"),
    ("--accent-foreground", TEXT_UP + ["color/action/fg"], "hover label"),
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


def _has_alpha(value: str) -> bool:
    v = (value or "").strip().lower()
    return v.startswith(("rgba(", "hsla(")) or (v.startswith("#") and len(v) == 9) or v == "transparent"


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
        # a slot whose value has alpha sits on an unknown fill in another project: fall back to the
        # next opaque candidate (a text-role slot must not arrive as rgba(…, 0.70))
        picked = None
        for cand in candidates:
            tok = next((x for x in dna["tokens"] if x["id"] == cand and x["type"] == "color"), None)
            if not tok:
                continue
            value = resolved[cand]["resolved"]
            if _has_alpha(value) and "-foreground" in slot and picked is None:
                continue
            picked = cand
            break
        slots.append((slot, picked, label))
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

    return _preview.render_preview_html(dna, resolver=resolve_tokens, exists=exists, root=dest)

RENDERER_VERSION = "build_artifacts.py/v2"
BLOCKS = ("meta", "evidence", "measurements", "patterns", "taste", "tokens", "interactions", "specimens")
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
RERUNNABLE = ("evidence", "measurements", "patterns", "taste", "tokens", "interactions", "specimens")
SCHEMA_VERSION = "1.1"
INTERACTION_PROPS = ("background-color", "color", "border-color", "box-shadow", "outline", "transform")
SPECIMEN_KEYS = {"hero", "stats", "cards", "table", "form", "backdrop", "brandSvg", "typeSpecimens"}
SPECIMEN_HERO_KEYS = {"eyebrow", "headline", "subhead", "primaryCta", "secondaryCta"}
SPECIMEN_CARD_KEYS = {"title", "price", "per", "note", "cta", "featured"}
SPECIMEN_FIELD_KEYS = {"label", "placeholder", "invalid"}

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

    specimens = dna.get("specimens")
    if specimens is not None:
        if not isinstance(specimens, dict):
            err(errors, "specimens must be an object")
            specimens = {}
        unknown = [k for k in specimens if k not in SPECIMEN_KEYS]
        if unknown:
            err(errors, f"specimens has unknown keys {unknown} (allowed: {sorted(SPECIMEN_KEYS)})")
        hero = specimens.get("hero")
        if hero is not None:
            if not isinstance(hero, dict) or not isinstance(hero.get("headline"), str) or not hero["headline"].strip():
                err(errors, "specimens.hero must be an object with a non-empty headline")
            else:
                for k in hero:
                    if k not in SPECIMEN_HERO_KEYS:
                        err(errors, f"specimens.hero.{k} is not a known key (allowed: {sorted(SPECIMEN_HERO_KEYS)})")
                    elif not isinstance(hero[k], str) or not hero[k].strip():
                        err(errors, f"specimens.hero.{k} must be a non-empty string")
        stats = specimens.get("stats")
        if stats is not None:
            if not isinstance(stats, list) or not stats or len(stats) > 4:
                err(errors, "specimens.stats must be a list of 1-4 {value,label} rows")
                stats = []
            for i, st in enumerate(stats):
                if not isinstance(st, dict) or not isinstance(st.get("value"), str) or not st["value"].strip() \
                        or not isinstance(st.get("label"), str) or not st["label"].strip():
                    err(errors, f"specimens.stats[{i}] must be {{value,label}} strings")
        cards = specimens.get("cards")
        if cards is not None:
            if not isinstance(cards, list) or not cards or len(cards) > 3:
                err(errors, "specimens.cards must be a list of 1-3 cards (pricing tiers or core features)")
                cards = []
            featured = 0
            for i, c in enumerate(cards):
                if not isinstance(c, dict):
                    err(errors, f"specimens.cards[{i}] must be an object")
                    continue
                for k in ("title", "price", "note"):
                    if not isinstance(c.get(k), str) or not c[k].strip():
                        err(errors, f"specimens.cards[{i}].{k} must be a non-empty string")
                for k in c:
                    if k not in SPECIMEN_CARD_KEYS:
                        err(errors, f"specimens.cards[{i}].{k} is not a known key (allowed: {sorted(SPECIMEN_CARD_KEYS)})")
                if c.get("featured"):
                    featured += 1
            if featured > 1:
                err(errors, "specimens.cards marks more than one featured card (at most one inverted tier)")
        table = specimens.get("table")
        if table is not None:
            if not isinstance(table, dict) or not isinstance(table.get("columns"), list) \
                    or not isinstance(table.get("rows"), list):
                err(errors, "specimens.table must be {columns[], rows[]}")
            else:
                cols = len(table["columns"])
                if cols < 2 or cols > 5:
                    err(errors, "specimens.table.columns must hold 2-5 column names")
                if len(table["rows"]) < 2 or len(table["rows"]) > 4:
                    err(errors, "specimens.table.rows must hold 2-4 sample rows")
                for i, row in enumerate(table["rows"]):
                    if not isinstance(row, list) or len(row) != cols or not all(isinstance(c, str) for c in row):
                        err(errors, f"specimens.table.rows[{i}] must be {cols} strings (one per column)")
        backdrop = specimens.get("backdrop")
        if backdrop is not None:
            if not isinstance(backdrop, dict):
                err(errors, "specimens.backdrop must be an object mapping section -> canvas|surface|action")
            else:
                allowed = {"nav", "hero", "colour", "type", "components", "motion", "bricks"}
                for k, v in backdrop.items():
                    if k not in allowed:
                        err(errors, f"specimens.backdrop.{k} is not a known section (allowed: {sorted(allowed)})")
                    elif v not in ("canvas", "surface", "action"):
                        err(errors, f"specimens.backdrop.{k} must name a role: canvas | surface | action")
        brand = specimens.get("brandSvg")
        if brand is not None:
            if not isinstance(brand, str) or not brand.strip().startswith("<svg"):
                err(errors, "specimens.brandSvg must be an inline <svg> string")
            elif re.search(r"href=|url\(|@import|<script|<image", brand, re.IGNORECASE):
                err(errors, "specimens.brandSvg must be self-contained: no href, url(), script or <image>")
        type_spec = specimens.get("typeSpecimens")
        if type_spec is not None and not isinstance(type_spec, dict):
            err(errors, "specimens.typeSpecimens must be an object mapping type token ids to specimen copy")
        form = specimens.get("form")
        if form is not None:
            if not isinstance(form, dict) or not isinstance(form.get("fields"), list) or not form["fields"]:
                err(errors, "specimens.form must carry at least one field")
            else:
                for i, f in enumerate(form["fields"]):
                    if not isinstance(f, dict) or not isinstance(f.get("label"), str) or not f["label"].strip():
                        err(errors, f"specimens.form.fields[{i}].label required")
                    for k in f:
                        if k not in SPECIMEN_FIELD_KEYS:
                            err(errors, f"specimens.form.fields[{i}].{k} is not a known key")

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


def render_bricks_data(dest: Path) -> list[dict]:
    """Lift the compilable slice of each clips/*/brick.json for the preview's Clipped Bricks block."""
    out = []
    for path in sorted((dest / "clips").glob("*/brick.json")):
        try:
            b = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        skin = {k: v for k, v in (b.get("skin") or {}).items() if not k.startswith("__")}
        shots = sorted((path.parent / "shots").glob("*.png"))
        states = {k: v for k, v in (b.get("states") or {}).items() if not k.startswith("_")}
        trigger = (b.get("source") or {}).get("triggerBox") or [0, 0, 0, 0]
        out.append({
            "slug": path.parent.name,
            "action": b.get("action"),
            "system": (b.get("slots") or {}).get("system"),
            "source": b.get("source") or {},
            "conclusion": b.get("conclusion"),
            "signalCount": b.get("signalCount"),
            "skin": skin,
            "reducedMotion": b.get("reducedMotion") or {},
            "deltas": {k: v for k, v in (b.get("deltas") or {}).items() if v},
            "timing": ((states.get("during") or {}).get("trigger") or {}).get("transition") or "",
            "radius": ((states.get("before") or {}).get("trigger") or {}).get("border-radius") or "",
            # the screenshots are 1440x900 viewport frames; the block sits at the trigger's y
            "crop": max(0, int(trigger[1]) - 28) if len(trigger) == 4 else 0,
            # time order, never alphabetical (after.png < before.png): the state machine reads forward
            "shots": _state_order([p.name for p in shots if "-reduced" not in p.name
                                   and p.name not in ("before_target.png", "_before_target.png")]),
            "shotsReduced": [p.name for p in shots if "-reduced" in p.name],
            "label": (b.get("source") or {}).get("triggerText") or path.parent.name,
            "capturedAt": b.get("capturedAt"),
        })
    return out


def colour_role(own_id: str, resolved: dict) -> str:
    """What this colour does on the page:
       text     — body / heading / link / muted copy: graded against the canvas
       status   — trend, success/error text: graded against its surface (canvas or dark section)
       on-fill  — a label or mark on a filled control: graded against that fill, never the canvas
       fill     — a surface or control fill: a swatch, no ratio (it does not carry a label)
    """
    own = own_id
    if re.match(r"color/(text|link)", own):
        return "text"
    if re.match(r"color/(trend|up|down|success|danger|error|warning)", own):
        return "status"
    if re.match(r"color/(action/fg|on-|text/on)", own):
        return "on-fill"
    return "fill"


def colour_ground(own_id: str, resolved: dict) -> tuple[str, str]:
    """(ground, role) — see colour_role(); the ground is the colour the role is measured against."""
    role = colour_role(own_id, resolved)
    by = resolved
    if role in ("text", "status"):
        for g in ("color/canvas", "color/surface", "color/well", "color/canvas-tint"):
            if g in by:
                return by[g]["resolved"], role
    if role == "on-fill":
        for g in ("color/action/bg", "color/brand"):
            if g in by:
                return by[g]["resolved"], role
    return (by[own_id]["resolved"] if own_id in by else "#ffffff"), role


def shadow_floor(dna: dict) -> float | None:
    """The tightest box-shadow cap among the taste guardrails (px), or None when none bounds it."""
    floors = [value for t in dna["taste"] if (t.get("kind") == "restraint")
              for value in [((t.get("guardrail") or {}).get("max") or {}).get("box-shadow")]
              if value]
    if not floors:
        return None
    return min(float(f.get("value", 0)) for f in floors)


def render_bricks(root: Path | None) -> list[dict]:
    return render_bricks_data(root) if root is not None else []


BRICK_STATE_ORDER = ("before", "during", "settled", "after", "restored", "after_target")


def _state_order(names: list[str]) -> list[str]:
    """Shots in the order the recording happened: before → during → settled → after → restored."""
    def rank(n: str) -> int:
        stem = n[:-4] if n.endswith(".png") else n
        return BRICK_STATE_ORDER.index(stem) if stem in BRICK_STATE_ORDER else len(BRICK_STATE_ORDER)
    return sorted(names, key=lambda n: (rank(n), n))


def render_site_files(dna: dict, dest: Path) -> dict[str, str]:
    """system/index.html + doc.css + system.js + site.css — every byte a render of dna.json."""
    import site_render as sr
    import visual_base as vb

    meta = dna["meta"]
    mode = (meta.get("modes") or ["default"])[0]
    resolved = resolve_tokens(dna["tokens"], mode)
    canvas = next((resolved[t["id"]]["resolved"] for t in dna["tokens"] if t["id"] == "color/canvas"), None)
    tone = vb.tone_of(canvas)
    pages = meta.get("crawl", {}).get("pages") or [meta["source"]]
    esc = sr._e
    read = sr.reads(resolved)
    text = sr.specimen_text(dna)
    bricks = render_bricks(dest)

    # ---------------------------------------------------------------- Observed tag -> evidence ids
    TAG_KEYS = {
        "palette": re.compile(r"color|palette|swatch|canvas|ink|surface|brand|up|down|purple|gold|grey|grey"),
        "typography": re.compile(r"font|type|weight|heading|size|dist|h1|h2|h3|body|display|styles"),
        "motion": re.compile(r"motion|ease|duration|transition|frame"),
        "material": re.compile(r"radius|radii|shadow|depth|ring|hairline|btn|button"),
    }

    def obs(kind: str, label: str = "+ Observed") -> str:
        return f'<button class="tag-obs" data-obs="{esc(kind)}">{esc(label)}</button>'

    def font_family() -> str:
        for tid in ("font/body", "font/sans", "font/ui"):
            if tid in resolved:
                return str(resolved[tid]["resolved"]).split(",")[0].strip().strip("\"'")
        return "the declared stack"

    # ---------------------------------------------------------------- 01 colour
    group_scene = {
        "semantic": "roles: where ink, surface and action may appear",
        "component": "inside a control: fill, label, ring, depth",
        "primitive": "the raw palette behind the roles",
    }

    canvas_v = (resolved.get("color/canvas") or {}).get("resolved")
    if not canvas_v:
        canvas_v = next(t["values"][mode] for t in dna["tokens"] if t["id"] == "color/canvas") \
            if any(t["id"] == "color/canvas" for t in dna["tokens"]) else "#FFFFFF"

    def swatch_group(layer: str) -> str:
        toks = [t for t in dna["tokens"] if t["type"] == "color" and t["layer"] == layer]
        if not toks:
            return ""
        cells = []
        for t in toks:
            v = resolved[t["id"]]["resolved"]
            ground, role = colour_ground(t["id"], resolved)
            if role == "fill":
                chip, grade = "fill · solid", ""       # a swatch is the colour; it does not carry a label
            elif ground == v:
                chip, grade = "canvas · ground", ""
            else:
                label, grade = vb.wcag_badge(v, ground)
                chip = f"{role.replace('-', ' ')} · {label}"
            cells.append(
                f'<div class="swatch"><div class="fill{" is-translucent" if ("rgba" in v or (len(v) == 9 and v.startswith("#")) or v in ("transparent",) or v.endswith(("B3", "80", "1A", "4D", "E6")) and len(v) == 9) else ""}" style="background:{esc(v)}"></div>'
                f'<div class="meta"><span class="tok" data-copy="var(--{esc(t["css"].lstrip("-"))})" role="button" '
                f'tabindex="0">{esc(t["id"])}</span><span class="hex" data-copy="{esc(v)}">{esc(v)}</span></div>'
                f'<div class="sub"><span class="wchip {grade}">{esc(chip)}</span></div></div>')
        return (f'<div class="lp-group"><h3><span>{esc(layer)}</span>'
                f'<span class="scene">{esc(group_scene[layer])} · {len(toks)}</span>'
                f'{obs("palette") if layer == "semantic" else ""}</h3>'
                f'<div class="sw">{"".join(cells)}</div></div>')

    pair_defs = [("heading / canvas", "color/text/heading", "color/canvas", "display copy"),
                 ("primary / canvas", "color/text/primary", "color/canvas", "headlines and labels"),
                 ("body / canvas", "color/text/body", "color/canvas", "paragraphs"),
                 ("secondary / canvas", "color/text/secondary", "color/canvas", "supporting rows"),
                 ("muted / surface", "color/text/tertiary", "color/surface", "captions on raised rows"),
                 ("muted / well", "color/text/muted", "color/well", "captions on the deepest surface"),
                 ("action-fg / action-bg", "color/action/fg", "color/action/bg", "primary button"),
                 ("link / canvas", "color/link", "color/canvas", "inline links")]
    prow = ""
    for label, fg_id, bg_id, where in pair_defs:
        fg, bg = resolved.get(fg_id, {}).get("resolved"), resolved.get(bg_id, {}).get("resolved")
        if not fg or not bg:
            continue
        wcag, grade = vb.wcag_badge(fg, bg)
        sample = "Aa 0123 0123456789"
        prow += (f'<div class="prow"><div class="sample" style="background:{esc(bg)};color:{esc(fg)}">'
                 f'<span class="cap-label">{esc(label)}</span>{esc(sample)}</div>'
                 f'<div class="pmeta"><span>{esc(where)}</span>'
                 f'<span class="wchip {grade}">{esc(wcag)}</span></div></div>')
    n_colors = len([t for t in dna["tokens"] if t["type"] == "color"])
    live_colour = f"""
<div class="lp-sheet"><span class="lp-num">01</span><h2 class="lp-title">Colour Palette</h2>
<span class="rule"></span><span class="count">{n_colors} colours</span></div>
<p class="lp-lede">Roles first, primitives last. Each chip is computed from the two token values, not sampled
from a screenshot; the canvas itself is shown as “canvas itself” rather than compared with itself.</p>
<div class="lp-groups">{swatch_group("semantic")}{swatch_group("component")}{swatch_group("primitive")}</div>
<div class="pairs"><h3>Pairs in use</h3>{prow}</div>"""

    # ---------------------------------------------------------------- 02 type
    type_tokens = [t for t in dna["tokens"] if t["type"] == "dimension" and t["id"].startswith("type/")]
    scale_params = "".join(f'<span>{esc(t["id"].replace("type/", ""))} {esc(resolved[t["id"]]["resolved"])}</span>'
                           for t in type_tokens)
    live_type = f"""
<div class="lp-sheet"><span class="lp-num">02</span><h2 class="lp-title">Typography Scale</h2>
<span class="rule"></span><span class="count">{len(type_tokens)} steps</span></div>
<p class="lp-lede">The run's own headline set at every step, at real size, in {esc(font_family())} and its
fallback stack — the face itself is not shipped.</p>
<div class="type-scale-params">{scale_params}</div>
{sr.type_rows(dna["tokens"], resolved, text, tag_prefix="1")}"""

    # ---------------------------------------------------------------- 03 components
    hero = text["hero"]
    cta = hero.get("primaryCta") or "Primary action"
    state_chips = "".join(
        f'<button class="state-chip" data-state="{cls}" data-state-group="btn" aria-pressed="'
        f'{"true" if cls == "" else "false"}">{esc(label)}{" · forced" if forced else ""}</button>'
        for label, cls, forced in (("default", "", False), ("hover", "is-hover", True),
                                   ("focus-visible", "is-focus", True), ("active", "is-active", True)))
    form = text["form"] or {}
    fields = form.get("fields") or []
    if fields:
        f0 = fields[0]
        form_html = (
            '<div class="lp-form">'
            + (f'<div class="cap">{esc(form.get("title"))}</div>' if form.get("title") else "")
            + f'<label class="ds-field"><span>{esc(f0["label"])}</span>'
              f'<input class="ds-input" id="demo-email" type="email" placeholder="{esc(f0.get("placeholder", ""))}" '
              f'data-invalid="{esc(f0.get("invalid", "Enter a valid value"))}" autocomplete="off">'
              f'<span class="field-note" id="demo-email-note" aria-live="polite"></span></label>'
            + f'<div><button class="ds-btn ds-btn--primary" type="button">{esc(form.get("submit") or "Continue")}</button></div>'
            + '</div>')
        form_block = f'<div class="block"><div class="cap"><span>Form field</span></div>{form_html}</div>'
    else:
        form_block = ""

    cards = text["cards"]
    tier_html, tier_cap = "", ""
    if cards:
        tiers = "".join(
            f'<div class="tier{" featured" if c.get("featured") else ""}">'
            f'<span class="kind">{esc(c["title"])}</span>'
            f'<span class="price">{esc(c["price"])}'
            + (f'<small>{esc(c["per"])}</small>' if c.get("per") else "")
            + f'</span><span class="note">{esc(c["note"])}</span>'
            + (f'<button class="ds-btn ds-btn--primary" type="button">{esc(c.get("cta") or cta)}</button>'
               if c.get("cta") else "")
            + '</div>' for c in cards)
        tier_html = f'<div class="pricing">{tiers}</div>'
        tier_cap = "pricing tiers" if any(c.get("per") for c in cards) else "core cards"

    table = text["table"]
    table_html, table_cap = "", ""
    if table:
        trend_cols = {j for j, c in enumerate(table["columns"])
                      if re.search(r"trend|change|24h|return|move", c, re.IGNORECASE)}
        head = "".join(f"<th>{esc(c)}</th>" for c in table["columns"])
        rows = ""
        for row in table["rows"]:
            cells = ""
            for j, v in enumerate(row):
                attr = ""
                if j == 1 and len(table["columns"]) == 4 and row[1].strip().endswith("%"):
                    attr = f' data-trend="{"down" if v.strip().startswith("-") else "up"}"'
                elif j in trend_cols:
                    attr = f' data-trend="{esc("down" if v.strip().startswith("-") else "up")}"'
                cells += f"<td{attr}>{esc(v)}</td>"
            rows += f"<tr>{cells}</tr>"
        table_html = f'<div class="lp-tbl"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
        table_cap = table.get("caption") or "sample rows"

    inter_rows = ""
    for it in (dna.get("interactions") or [])[:2]:
        hover = (it.get("hover") or {}).get("delta") or {}
        focus = (it.get("focus") or {}).get("delta") or {}
        pick = next(iter(hover.items()), next(iter(focus.items()), None))
        if pick:
            k, pair = pick
            inter_rows += (f'<div class="row"><span>{esc(it["kind"])} · {"hover" if hover else "focus"} →</span>'
                           f'<b>{esc(k)} {esc(str(pair[0])[:22])} → {esc(str(pair[1])[:22])}</b></div>')
    inter_block = (f'<div class="block"><div class="cap"><span>Measured interaction</span>'
                   f'<span>real pointer</span></div><div class="rows">{inter_rows}</div></div>'
                   if inter_rows else "")
    radii = sorted({resolved[t["id"]]["resolved"] for t in dna["tokens"] if t["id"].startswith("radius/")},
                   key=lambda r: (len(r), r))[:3]
    float_line = ('<div class="ds-card ds-card--float">Float card · the run\'s float shadow, because no '
                  'restraint caps it.</div>'
                  if (shadow_floor(dna) is None or shadow_floor(dna) >= 4) else
                  '<div class="ds-card">Shadow specimen withheld: this run\'s restraint caps box-shadow '
                  'below 4px, so depth is a hairline here.</div>')
    live_components = f"""
<div class="lp-sheet"><span class="lp-num">03</span><h2 class="lp-title">Components &amp; Cards</h2>
<span class="rule"></span><span class="count">real states, not screenshots</span></div>
<p class="lp-lede">Controls read the run's action tokens. Click a state chip to force a state; hover and
focus-visible remain live.</p>
<div class="lp-comp-grid">
  <div class="col">
    <div class="block"><div class="cap"><span>Button</span>{obs("material")}</div>
      <div class="btn-row"><button class="ds-btn ds-btn--primary" id="demo-btn" type="button">{esc(cta)}</button>
      {f'<button class="ds-btn ds-btn--secondary" type="button">{esc(hero["secondaryCta"])}</button>' if hero.get("secondaryCta") else ""}</div>
      <div class="state-row" role="group" aria-label="forced button states">{state_chips}</div>
      <p class="lp-figcaption">Forced samples sit next to live states; neither replaces the other.</p>
    </div>
    {form_block}{inter_block}
  </div>
  <div class="col">
    {f'<div class="block"><div class="cap"><span>Cards</span><span>{esc(tier_cap)}</span></div>{tier_html}</div>' if tier_html else ""}
    {f'<div class="block"><div class="cap"><span>Sample rows</span><span>{esc(table_cap)}</span></div>{table_html}</div>' if table_html else ""}
    <div class="block"><div class="cap"><span>Surfaces</span><span>radius {esc(" / ".join(radii)) or "none recorded"}</span></div>
      <div class="ds-card">Default card · body copy sits on the surface token.</div>
      <div class="ds-card ds-card--tint">Tint card · the quieter surface.</div>
      {float_line}
    </div>
  </div>
</div>"""

    # ---------------------------------------------------------------- 04 motion & guardrails
    easings = [t for t in dna["tokens"] if t["type"] == "easing"]
    durations = [t for t in dna["tokens"] if t["type"] == "duration"]
    rows = []
    for i, t in enumerate(durations):
        dur = resolved[t["id"]]["resolved"]
        spec = resolved[easings[i % len(easings)]["id"]]["resolved"] if easings else "cubic-bezier(0.4, 0, 0.2, 1)"
        rows.append(
            f'<div class="motion"><div class="plot">{vb.bezier_svg(spec, 168, 88)}</div>'
            f'<div class="mid"><div class="mono" data-copy="var(--{esc(t["css"].lstrip("-"))})" role="button" '
            f'tabindex="0">{esc(t["id"])} · {esc(dur)}</div>'
            f'<div class="track"><span class="dot" id="sym-{i}-dot"></span></div></div>'
            f'<div class="act"><label for="sym-{i}-range">Replay</label>'
            f'<input type="range" id="sym-{i}-range" class="motion-range" min="0" max="1000" value="0" '
            f'aria-label="scrub {esc(t["id"])}">'
            f'<button class="tp-btn" data-sys-replay="sym-{i}-dot" data-dur="{esc(dur)}" data-ease="{esc(spec)}">Play</button>'
            f'</div></div>')
    for t in easings:
        spec = resolved[t["id"]]["resolved"]
        rows.append(
            f'<div class="motion"><div class="plot">{vb.bezier_svg(spec, 168, 88)}</div>'
            f'<div class="mid"><div class="mono" data-copy="var(--{esc(t["css"].lstrip("-"))})" role="button" '
            f'tabindex="0">{esc(t["id"])}</div><div class="spec-val">{esc(spec)}</div></div>'
            f'<div class="act">{obs("motion", t["status"])}</div></div>')

    taste_blocks, gate_blocks = "", ""
    for t in dna["taste"]:
        taste_blocks += (
            f'<article class="tcard"><div class="head"><span>{esc(t["kind"])}</span>'
            f'<span>{esc(" · ".join(t["evidence"]))}</span><span>{esc(t["status"])}</span></div>'
            f'<h4>{esc(t["name"])}</h4>'
            f'<div class="ab"><div class="v">{esc(t["chose"])}</div><div class="vs">over</div>'
            f'<div class="v over">{esc(t["over"])}</div></div>'
            f'<p class="why">{esc(t["reason"])}</p>'
            + (sr.guardrail_caps(t["guardrail"], expandable=True) if t.get("guardrail") else "")
            + '</article>')
        if t.get("guardrail"):
            gate_blocks += (f'<div class="gate-item"><div class="gate-head"><span>{esc(t["name"])}</span>'
                            f'<span class="mono">{esc(t["id"])}</span></div>'
                            f'{sr.guardrail_caps(t["guardrail"], expandable=True)}</div>')
    live_motion = f"""
<div class="lp-sheet"><span class="lp-num">04</span><h2 class="lp-title">Motion &amp; Guardrails</h2>
<span class="rule"></span><span class="count">{len(durations)} durations · {len(easings)} curves</span></div>
<p class="lp-lede">Each curve is the token's own cubic-bezier with its handles drawn. Play runs the real
duration, the slider scrubs it, and Reduced motion in the top bar replaces every travel with its end state.</p>
<div class="lp-motion">{''.join(rows)}</div>
<p class="lp-motion-legend">dot · direction of travel · curve · measured easing · status · evidence class</p>
<div class="sec-col">
  <div><div class="cap">MUST NOT · mechanical gates</div>
    <p class="lp-figcaption">Every capsule is a machine-readable rule. Expand one to read the regex a build is
    checked against; a generated page that matches it fails <code>lint_output.py</code>.</p>
    <div class="gate-list">{gate_blocks or '<p class="lp-figcaption">No restraint carries a machine gate in this run.</p>'}</div></div>
  <div><div class="cap">Taste · decision, and the rejected alternative</div>{taste_blocks}</div>
</div>"""

    # ---------------------------------------------------------------- 05 bricks
    if bricks:
        cards_html = "".join(_brick_card(b, read, esc, obs) for b in bricks)
        bricks_html = (f'<div class="lp-bricks">{cards_html}</div>'
                       f'<p class="provenance">Each brick was recorded twice in the same browser: once normally, '
                       f'once with CDP <code>prefers-reduced-motion: reduce</code>. The screenshots are the real '
                       f'frames from <code>clips/{esc(bricks[0]["slug"])}/shots/</code>.</p>')
        count = f"{len(bricks)} brick{'' if len(bricks) == 1 else 's'}"
    else:
        bricks_html = ('<p class="provenance">No <code>clips/</code> in this run. A single module can be lifted '
                       'with <code>lewitt clip --find "…"</code>; its brick, keyframes and reduced-motion '
                       'measurement would land here.</p>')
        count = "no clips yet"
    live_bricks = f"""
<div class="lp-sheet"><span class="lp-num">05</span><h2 class="lp-title">Clipped Bricks</h2>
<span class="rule"></span><span class="count">{esc(count)}</span></div>
<p class="lp-lede">One module with its interaction, skin stripped and mapped onto this run's slots. The live
module on the left is rebuilt from the slot mapping; on the right is what the browser recorded on the source.</p>
{bricks_html}"""

    live = {"hero": _hero_html(dna, resolved, read, text, esc, obs),
            "colour": live_colour, "type": live_type, "components": live_components,
            "motion": live_motion, "bricks": live_bricks}
    # each long-scroll step is painted by specimens.backdrop in site_render._live_section
    specs = _specs_panels(dna, dest, resolved, pages, bricks, esc)

    html = sr.app_shell(dna, resolved, live, specs, pages=len(pages))
    html = html.replace('<link rel="stylesheet" href="site.css">',
                        '<link rel="stylesheet" href="site.css">\n<style>:root { --doc-bg: '
                        + vb.TONES[tone]["bg"] + '; }\n'
                        + vb.fingerprint_css(vb.fingerprint_stops(resolved, dna), selector="#fp")
                        + '</style>')
    evidence = json.dumps({"source": meta["source"], "capturedAt": meta.get("capturedAt"),
                           "evidence": dna["evidence"], "measurements": dna["measurements"],
                           "specimens": dna.get("specimens")},
                          ensure_ascii=False, indent=2) + "\n"
    return {
        "system/index.html": html,
        "system/doc.css": vb.base_css(tone, scope=":root") + "\n" + sr.CSS,
        "system/site.css": SITE_CSS,
        "system/system.js": sr.JS,
        "system/evidence.json": evidence,
    }


def _brick_card(b: dict, read: dict, esc, obs) -> str:
    skin = b["skin"]
    fill = (skin.get("trigger_fill") or {}).get("css") or "var(--lw-action-bg)"
    label_css = (skin.get("trigger_label") or {}).get("css") or "var(--lw-action-fg)"
    radius = (skin.get("radius") or {}).get("css")
    timing = b["timing"] or "transform .3s ease"
    rm = b["reducedMotion"]
    verdict = {
        "degraded-to-none": ("ok", "transition removed under reduce; end state applied instantly"),
        "degraded": ("ok", f"shortened to {rm.get('reduced', {}).get('durationMs', 0):g}ms; end state kept"),
        "not-degraded": ("bad", "the source keeps moving under reduce — implement the branch yourself"),
        "unrecorded": ("manual", "the reduced pass produced no snapshot"),
    }.get(rm.get("status"), ("manual", "not recorded"))
    # every shot is a 1440x900 viewport frame; crop the window around the trigger (where it sat), as a %
    # of the image height so the thumbnail scales with the column
    shot_h = 900
    crop = max(0.0, b["crop"])
    band = 620
    top = min(max(crop - 40, 0), shot_h - band)
    shots = "".join(
        f'<figure class="trim" style="--crop-y:{(top / shot_h) * 100:.2f}%">'
        f'<img src="../clips/{esc(b["slug"])}/shots/{esc(name)}" alt="{esc(b["label"])} · {esc(name[:-4])}" loading="lazy">'
        f'<figcaption>{esc(name[:-4].replace("-", " "))}</figcaption></figure>'
        for name in b["shots"][:3])
    changes = ""
    for part, props in (b["deltas"].get("module.hover") or {}).items():
        for k, pair in list(props.items())[:2]:
            changes += f'<div class="row"><span>{esc(part)} · {esc(k)}</span><b>{esc(str(pair[1])[:26])}</b></div>'
    skin_notes = " · ".join(f"{esc(k)} → {esc(v['css'])}" for k, v in list(skin.items())[:3] if v.get("css"))
    radius_rule = (f"--brick-radius:{radius};" if radius else "")
    return f"""
<div class="brick-card">
  <div class="bh"><span class="name">brick · {esc(b["slug"])}</span>
    <span>action {esc(b["action"])}</span><span>slots {esc(b["system"])}</span>
    <span>{esc(b["source"].get("how", ""))} · <q>{esc(b["label"])}</q></span>
    <span class="tag-obs" aria-disabled="true">{esc(b["conclusion"])} · {esc(b["signalCount"])} changes</span></div>
  <div class="brick-live">
    <div class="brick-stage" style="--brick-bg:{esc(fill)};--brick-fg:{esc(label_css)};{radius_rule}--brick-transition:{esc(timing)}">
      <div class="cap"><span>live brick · rebuilt from the slot mapping</span></div>
      <div class="brick-cta-row"><button class="brick-cta" type="button">{esc(b["label"])}</button></div>
      <div class="brick-shots">{shots}</div>
    </div>
    <aside class="brick-meta">
      <div class="cap"><span>measured on the source</span>{obs("material")}</div>
      <div class="rows">
        <div class="row"><span>trigger</span><b>&lt;{esc(b["source"].get("triggerTag", "a"))}&gt; {esc(b["source"].get("triggerBox") or "")}</b></div>
        {f'<div class="row"><span>module</span><b>{esc(_short(b["source"].get("module", ""), 40))}</b></div>' if b["source"].get("moduleIsTrigger") is False else ""}
        <div class="row"><span>changes</span><b>{esc(b["signalCount"])}</b></div>
        {changes}
      </div>
      <div class="verdict {verdict[0]}">reduced motion · {esc(rm.get("status", "n/a"))}<br>{esc(verdict[1])}</div>
      <div class="mono-line">{skin_notes}</div>
    </aside>
  </div>
</div>"""


def _short(text: str, n: int) -> str:
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "…"


def _hero_html(dna: dict, resolved: dict, read: dict, text: dict, esc, obs) -> str:
    """First screen = the brand: the run's own headline at its own display size, its stats strip, the
    eyebrow pill and the single primary action; the source's media becomes the band below the copy."""
    hero = text["hero"]
    lines = text["headline_lines"] or ["Specimen copy is set at this step"]
    ctas = ""
    if hero.get("secondaryCta"):
        ctas += f'<button class="ds-btn ds-btn--secondary" type="button">{esc(hero["secondaryCta"])}</button>'
    if hero.get("primaryCta"):
        ctas += f'<button class="ds-btn ds-btn--primary" type="button">{esc(hero["primaryCta"])}</button>'
    strip = ('<div class="stat-strip">' + "".join(
        f'<div class="stat"><span class="v">{esc(s["value"])}</span><span class="k">{esc(s["label"])}</span></div>'
        for s in text["stats"]) + '</div>') if text["stats"] else ""
    canvas_v = resolved.get("color/canvas", {}).get("resolved", "")
    specs = dna.get("specimens") or {}
    accent = (specs.get("backdrop") or {}).get("nav")
    media = hero.get("media") or ""
    src = os.path.relpath(Path(os.path.dirname(os.path.abspath(__file__)))) and ""
    media_html = (f'<figure class="hero-band"><img src="../{esc(media)}" alt="captured hero frame of '
                  f'{esc(dna["meta"].get("name") or "")}" loading="eager">'
                  f'<figcaption>hero frame · the captured source, not a rebuilt mock</figcaption></figure>'
                  if media else "")
    kind = "a twin answering at midnight, in your voice" if "twin" in json.dumps(specs).lower() else "the brand, in one line"
    eyebrow = (f'<p class="eyebrow{" is-tip" if accent == "action" else ""}">{esc(hero["eyebrow"])}</p>'
               if hero.get("eyebrow") else "")
    return f"""
<div class="hero-before">{esc(kind)}</div>
<div class="hero-copy">
  {eyebrow}
  <h1>{"".join(f"<span>{esc(ln)}</span>" for ln in lines)}</h1>
  {f'<p class="sub">{esc(hero["subhead"])}</p>' if hero.get("subhead") else ""}
  <div class="ctas">{ctas}</div>
</div>
{media_html}
{strip}
<p class="hero-note">canvas <code>{esc(canvas_v)}</code> · {"hero frame · the captured still, not a rebuilt mock; " if media else ""}every specimen on this page reads the run's own <code>--lw-*</code> tokens {obs("palette")}</p>
"""


def _section_roles(dna: dict, live: dict[str, str], esc) -> dict[str, str]:
    """specimens.backdrop picks the source's own rhythm: a section is painted canvas, surface or action."""
    backdrop = (dna.get("specimens") or {}).get("backdrop") or {}
    out = {}
    for key, html in live.items():
        role = backdrop.get(key)
        if role and role != "canvas":
            out[key] = f'<div data-backdrop="{esc(role)}">{html}</div>'
        else:
            out[key] = f'<div data-backdrop="canvas">{html}</div>'
    return out


def _brick_card(b: dict, read: dict, esc, obs) -> str:
    skin = b["skin"]
    fill = (skin.get("trigger_fill") or {}).get("css") or "var(--lw-action-bg)"
    label_css = (skin.get("trigger_label") or {}).get("css") or "var(--lw-action-fg)"
    radius = (skin.get("radius") or {}).get("css")
    timing = b["timing"] or "transform .3s ease"
    rm = b["reducedMotion"]
    verdict = {
        "degraded-to-none": ("ok", "transition removed under reduce; end state applied instantly"),
        "degraded": ("ok", f"shortened to {rm.get('reduced', {}).get('durationMs', 0):g}ms; end state kept"),
        "not-degraded": ("bad", "the source keeps moving under reduce — implement the branch yourself"),
        "unrecorded": ("manual", "the reduced pass produced no snapshot"),
    }.get(rm.get("status"), ("manual", "not recorded"))
    # every shot is a 1440x900 viewport frame; crop the window around the trigger (where it sat), as a %
    # of the image height so the thumbnail scales with the column
    shot_h = 900
    crop = max(0.0, b["crop"])
    band = 620
    top = min(max(crop - 40, 0), shot_h - band)
    shots = "".join(
        f'<figure class="trim" style="--crop-y:{(top / shot_h) * 100:.2f}%">'
        f'<img src="../clips/{esc(b["slug"])}/shots/{esc(name)}" alt="{esc(b["label"])} · {esc(name[:-4])}" loading="lazy">'
        f'<figcaption>{esc(name[:-4].replace("-", " "))}</figcaption></figure>'
        for name in b["shots"][:3])
    changes = ""
    for part, props in (b["deltas"].get("module.hover") or {}).items():
        for k, pair in list(props.items())[:2]:
            changes += f'<div class="row"><span>{esc(part)} · {esc(k)}</span><b>{esc(str(pair[1])[:26])}</b></div>'
    skin_notes = " · ".join(f"{esc(k)} → {esc(v['css'])}" for k, v in list(skin.items())[:3] if v.get("css"))
    radius_rule = (f"--brick-radius:{radius};" if radius else "")
    return f"""
<div class="brick-card">
  <div class="bh"><span class="name">brick · {esc(b["slug"])}</span>
    <span>action {esc(b["action"])}</span><span>slots {esc(b["system"])}</span>
    <span>{esc(b["source"].get("how", ""))} · <q>{esc(b["label"])}</q></span>
    <span class="tag-obs" aria-disabled="true">{esc(b["conclusion"])} · {esc(b["signalCount"])} changes</span></div>
  <div class="brick-live">
    <div class="brick-stage" style="--brick-bg:{esc(fill)};--brick-fg:{esc(label_css)};{radius_rule}--brick-transition:{esc(timing)}">
      <div class="cap"><span>live brick · rebuilt from the slot mapping</span></div>
      <div class="brick-cta-row"><button class="brick-cta" type="button">{esc(b["label"])}</button></div>
      <div class="brick-shots">{shots}</div>
    </div>
    <aside class="brick-meta">
      <div class="cap"><span>measured on the source</span>{obs("material")}</div>
      <div class="rows">
        <div class="row"><span>trigger</span><b>&lt;{esc(b["source"].get("triggerTag", "a"))}&gt; {esc(b["source"].get("triggerBox") or "")}</b></div>
        {f'<div class="row"><span>module</span><b>{esc(_short(b["source"].get("module", ""), 40))}</b></div>' if b["source"].get("moduleIsTrigger") is False else ""}
        <div class="row"><span>changes</span><b>{esc(b["signalCount"])}</b></div>
        {changes}
      </div>
      <div class="verdict {verdict[0]}">reduced motion · {esc(rm.get("status", "n/a"))}<br>{esc(verdict[1])}</div>
      <div class="mono-line">{skin_notes}</div>
    </aside>
  </div>
</div>"""


def _short(text: str, n: int) -> str:
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "…"


def _hero_html(dna: dict, resolved: dict, read: dict, text: dict, esc, obs) -> str:
    """First screen = the brand: the run's own headline, its stats strip, and its source's hero media
    when one was captured (the captured frame itself, never a fake mock)."""
    hero = text["hero"]
    lines = text["headline_lines"] or ["Specimen copy is set at this step"]
    ctas = ""
    if hero.get("primaryCta"):
        ctas += f'<button class="ds-btn ds-btn--primary" type="button">{esc(hero["primaryCta"])}</button>'
    if hero.get("secondaryCta"):
        ctas += f'<button class="ds-btn ds-btn--secondary" type="button">{esc(hero["secondaryCta"])}</button>'
    strip = ('<div class="stat-strip">' + "".join(
        f'<div class="stat"><span class="v">{esc(s["value"])}</span><span class="k">{esc(s["label"])}</span></div>'
        for s in text["stats"]) + '</div>') if text["stats"] else ""
    canvas_v = resolved.get("color/canvas", {}).get("resolved", "")
    specs = dna.get("specimens") or {}
    accent = (specs.get("backdrop") or {}).get("nav")
    chip = " is-tip" if accent == "action" else ""
    kind = "a twin answering at midnight, in your voice" if "twin" in json.dumps(specs).lower() else "the run's signature module"
    eyebrow = f'<p class="eyebrow{chip}" title="{esc(kind)}">{esc(hero["eyebrow"])}</p>' if hero.get("eyebrow") else ""
    media = bool(hero.get("media"))
    cls = "lp-hero lp-hero--solo" if (hero.get("composition") == "solo" or not media) else "lp-hero"
    note = ("every specimen below reads the run's own <code>--lw-*</code> tokens, not a screenshot"
            if not media else
            "hero photograph · the captured frame, not a rebuilt mock; every specimen below reads the run's own "
            "<code>--lw-*</code> tokens")
    return f"""
<div class="hero-copy">
  <div class="hero-before">{esc(hero["eyebrow"])}</div>
  <h1>{"".join(f"<span>{esc(ln)}</span>" for ln in lines)}</h1>
  {f'<p class="sub">{esc(hero["subhead"])}</p>' if hero.get("subhead") else ""}
  <div class="ctas">{ctas}</div>
  <p class="hero-note">canvas <code>{esc(canvas_v)}</code> · {note} {obs("palette")}</p>
</div>
{strip}"""
def _specs_panels(dna: dict, dest: Path, resolved: dict, pages: list, bricks: list, esc) -> dict[str, str]:
    meta = dna["meta"]
    taste0 = dna["taste"][0]

    def badge(status: str) -> str:
        return f'<span class="badge {esc(status)}">{esc(status)}</span>'

    hero = (dna.get("specimens") or {}).get("hero") or {}
    claims = [("specimens.hero.headline", hero.get("headline")), ("specimens.hero.subhead", hero.get("subhead")),
              ("specimens.hero.primaryCta", hero.get("primaryCta")),
              ("specimens.stats", "; ".join(f'{s["value"]} {s["label"]}' for s in (dna.get("specimens") or {}).get("stats") or [])),
              ("specimens.cards", "; ".join(c["title"] for c in (dna.get("specimens") or {}).get("cards") or [])),
              ("clips/", ", ".join(b["slug"] for b in bricks))]
    claim_rows = "".join(f'<tr><td class="mono">{esc(k)}</td><td>{esc(v)}</td></tr>' for k, v in claims if v)

    overview = f"""
<h1>Overview</h1>
<p class="lede">{esc(meta['source'])} · captured {esc(str(meta.get('capturedAt', ''))[:19])} · {esc(meta.get('mode'))} mode · every figure is rendered from <code>dna.json</code> and reads <code>../tokens.css</code>.</p>
<p class="sp-ledger"><span class="tb-meta">{len(dna['tokens'])} tokens</span><span class="tb-meta">{len(dna['evidence'])} evidence</span><span class="tb-meta">{len(pages)} pages inspected</span></p>
<div class="note"><strong>{esc(taste0['name'])}</strong> — {esc(taste0['reason'])}</div>
<div class="sp-stat-grid">
  <div class="sp-stat"><span class="v">{len(pages)}</span><span class="k">pages inspected</span><span class="d">entry + representative subpages</span></div>
  <div class="sp-stat"><span class="v">{len(dna['tokens'])}</span><span class="k">tokens</span><span class="d">primitive → semantic → component</span></div>
  <div class="sp-stat"><span class="v">{len(dna['evidence'])}</span><span class="k">evidence entries</span><span class="d">each observed value cites one</span></div>
  <div class="sp-stat"><span class="v">{len(dna['measurements'])}</span><span class="k">measurements</span><span class="d">werted with units and a status</span></div>
  <div class="sp-stat"><span class="v">{len(dna['patterns'])}</span><span class="k">patterns</span><span class="d">rules between values and taste</span></div>
  <div class="sp-stat"><span class="v">{len(dna['taste'])}</span><span class="k">taste principles</span><span class="d">{sum(1 for t in dna['taste'] if t['kind'] == 'restraint')} restraint(s) with machine gate</span></div>
  <div class="sp-stat"><span class="v">{len(dna.get('interactions') or [])}</span><span class="k">interaction deltas</span><span class="d">forced with a real pointer</span></div>
  <div class="sp-stat"><span class="v">{len(bricks)}</span><span class="k">clipped bricks</span><span class="d">single modules, reduce measured</span></div>
</div>
<h2>Pages</h2>
<ul>{"".join(f'<li><a href="{esc(p)}" rel="noreferrer">{esc(p)}</a></li>' for p in pages)}</ul>
<h2>Claim register</h2>
<p class="lede">Specimen copy is <em>inferred</em> from the source's voice: it is written for this run, never quoted
from the site, and the page never presents it as the site's own copy. Tokens and measurements are observed.</p>
<div class="tbl"><table><thead><tr><th>Claim</th><th>Basis</th></tr></thead><tbody>{claim_rows}</tbody></table></div>"""
    overview = overview.replace("werted with units", "measured with units")

    token_rows = "".join(
        f'<tr><td><span class="mono" data-copy="var(--{esc(t["css"].lstrip("-"))})">{esc(t["css"])}</span></td>'
        f'<td class="mono">{esc(t["id"])}</td><td>{esc(t["layer"])}</td><td>{esc(t["type"])}</td>'
        f'<td><span class="mono" data-copy="{esc(resolved[t["id"]]["resolved"])}">{esc(resolved[t["id"]]["resolved"])}</span></td>'
        f'<td>{badge(t["status"])}</td></tr>' for t in dna["tokens"])
    tokens = f"""
<h1>Tokens</h1>
<p class="lede">The full registry with aliases resolved for mode <code>{esc((meta.get('modes') or ['default'])[0])}</code>.
Click a name or a value to copy it.</p>
<div class="tbl"><table><thead><tr><th>CSS var</th><th>Token</th><th>Layer</th><th>Type</th><th>Value</th><th>Status</th></tr></thead>
<tbody>{token_rows}</tbody></table></div>"""

    measure_rows = "".join(
        f'<tr><td>{esc(m["category"])}</td><td>{esc(m["value"])}</td><td>{badge(m["status"])}</td>'
        f'<td class="mono">{esc(", ".join(m["evidence"]))}</td></tr>' for m in dna["measurements"])
    measurements = f"""
<h1>Measurements</h1>
<p class="lede">Values with units and the evidence that produced them. A row whose status is not observed says so.</p>
<div class="tbl"><table><thead><tr><th>Category</th><th>Value</th><th>Status</th><th>Evidence</th></tr></thead><tbody>{measure_rows}</tbody></table></div>"""

    evidence_rows = "".join(
        f'<tr><td class="mono">{esc(e["id"])}</td><td class="mono">{esc(e["url"].replace("https://", ""))}</td>'
        f'<td>{esc(e["locator"])}</td><td class="mono">{esc(e["method"])}</td><td>{badge(e["status"])}</td>'
        f'<td class="mono">{esc(json.dumps(e["values"], ensure_ascii=False)[:220])}</td></tr>' for e in dna["evidence"])
    ledger = f"""
<h1>Evidence Ledger</h1>
<p class="lede">Every observed or inferred claim cites one of these recordings; none was estimated from a screenshot.</p>
<div class="tbl"><table><thead><tr><th>ID</th><th>URL</th><th>Locator</th><th>Method</th><th>Status</th><th>Values</th></tr></thead>
<tbody>{evidence_rows}</tbody></table></div>"""

    limitations = f"""
<h1>Limitations</h1>
<p class="lede">What this run can and cannot claim. Rows that are not tested say so in <code>VERIFY.md</code>.</p>
<ul>{"".join(f"<li>{esc(x)}</li>" for x in meta.get("limitations", []))}</ul>
<h2>Fidelity</h2>
<p class="lede">The rebuild is the Live Preview of this page. Type parity is out of scope: the source face is not
shipped. Fidelity stays <strong>PARTIAL</strong> until every deviation in <code>fidelity.json</code> is closed.</p>"""

    def code_block(filename: str) -> str:
        path = dest / filename
        if not path.exists():
            return ""
        body = path.read_text(encoding="utf-8")
        return (f'<div class="code"><div class="code-head"><span>{esc(filename)}</span>'
                f'<button class="mini-btn" data-copy="{esc(body)}">Copy</button></div>'
                f'<pre>{esc(body)}</pre></div>')

    downloads = f"""
<h1>Code &amp; Downloads</h1>
<p class="lede">All three files are renders of the same <code>dna.json</code>; a hand edit to any of them fails
<code>lint_output.py</code>'s single-source drift check.</p>
<div class="dl">{"".join(f'<a class="mini-btn" href="../{f}" download>{f}</a>' for f in ("tokens.css", "shadcn-theme.css", "agent-rules.md", "taste.md", "VERIFY.md", "tokens.resolved.json"))}</div>
{code_block("tokens.css")}{code_block("shadcn-theme.css")}{code_block("agent-rules.md")}"""

    shots = sorted(p.name for p in (dest / "capture").glob("viewport*.png")) if (dest / "capture").exists() else []
    source_shot = shots[0] if shots else None
    rebuild_shot = next((n for n in ("rebuild.png", "rebuild-1.png") if (dest / "capture" / n).exists()), None)
    fid: dict = {}
    if (dest / "fidelity.json").exists():
        try:
            fid = json.loads((dest / "fidelity.json").read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            fid = {}
    deviations = "".join(
        f'<div class="deviation"><strong>{esc(d.split(" — ")[0][:72])}</strong>'
        f'{esc(d.split(" — ", 1)[1]) if " — " in d else ""}</div>' for d in fid.get("deviations") or [])
    agrees = "".join(f"<li>{esc(a)}</li>" for a in fid.get("agrees") or [])
    if source_shot and rebuild_shot:
        compare = f"""
<div class="compare" id="compare">
  <img src="../capture/{esc(source_shot)}" alt="captured source page">
  <div class="layer b"><img src="../capture/{esc(rebuild_shot)}" alt="rebuilt page"></div>
  <div class="handle"></div>
  <span class="lab l">source · capture/{esc(source_shot)}</span><span class="lab r">rebuild · capture/{esc(rebuild_shot)}</span>
  <input id="split" type="range" min="0" max="100" value="50" aria-label="compare source and rebuild">
</div>"""
    elif source_shot:
        compare = (f'<div class="fid"><div class="src-shot"><img src="../capture/{esc(source_shot)}" '
                   f'alt="captured source page"></div><div class="fid-note"><h3>Rebuild</h3>'
                   f'<p class="lede">The rebuild is the Live Preview itself. No rebuild screenshot was recorded, '
                   f'so there is no split to drag. Record <code>capture/rebuild.png</code> at '
                   f'{esc(str(meta.get("viewport") or "the same viewport"))} to enable pixel comparison.</p></div></div>')
    else:
        compare = '<p class="lede">No capture was recorded for this run.</p>'
    fidelity = f"""
<h1>Fidelity vs Source</h1>
<p class="lede">{esc(fid.get("method") or "No fidelity record in this run.")}</p>
{compare}
{('<h2>Agrees</h2><ul>' + agrees + '</ul>') if agrees else ''}
{('<h2>Recorded deviations</h2><div class="deviations">' + deviations + '</div>') if deviations else ''}
<p class="note">Status: <strong>{esc(str(fid.get("status") or "unverified").upper())}</strong>. Deviations stay visible rather than claimed away.</p>"""

    return {"overview": overview, "tokens": tokens, "measurements": measurements,
            "evidence": ledger, "limitations": limitations, "downloads": downloads,
            "fidelity": fidelity}


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
                         "Any of: evidence,measurements,patterns,taste,tokens,interactions,specimens")
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
    # system/ is the reference site; any run can carry it, whatever meta.mode says (drift_check is
    # the authority for whether it is current)
    full = True
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


