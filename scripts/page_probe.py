#!/usr/bin/env python3
"""Shared page probe: read what a live page actually renders.

Used by `cert.py` (audit a build) and `clip.py` (extract one module). Two ways to ask:

  vars   — every custom property the page declares, grouped by naming family
           (lewitt's --lw-*, shadcn/Tailwind v4's --background/--primary/…, plus anything else)
  set    — for a list of selectors, the computed values the caller asked about
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PROPS = ["background-color", "color", "border-color", "box-shadow", "outline", "transform",
         "font-size", "font-weight", "font-family", "line-height", "letter-spacing",
         "border-radius", "border-width", "border-style", "opacity", "width", "height",
         "padding", "margin", "gap", "display", "position", "transition", "text-transform"]

VAR_JS = r"""
() => {
  const out = { lewitt: {}, shadcn: {}, other: {} };
  const seen = new Set();
  const push = (name, raw) => {
    if (seen.has(name) || !raw) return;
    seen.add(name);
    const p = document.createElement('span');
    p.style.color = raw.trim();
    document.body.appendChild(p);
    const resolved = getComputedStyle(p).color;
    p.remove();
    const entry = { raw: raw.trim(), rgb: resolved };
    if (name.startsWith('--lw-')) out.lewitt[name] = entry;
    else if (/^--(background|foreground|card|popover|primary|secondary|muted|accent|destructive|border|input|ring|radius)(-|$)/.test(name)) out.shadcn[name] = entry;
    else out.other[name] = entry;
  };
  const walk = (rules) => {
    for (const rule of rules) {
      if (rule.cssRules && !rule.style) { walk(rule.cssRules); continue; }
      if (rule.cssRules) walk(rule.cssRules);
      if (!rule.style) continue;
      for (const name of rule.style) {
        if (!name.startsWith('--')) continue;
        push(name, rule.style.getPropertyValue(name));
      }
    }
  };
  for (const sheet of document.styleSheets) {
    let rules;
    try { rules = sheet.cssRules; } catch (e) { continue; }
    if (rules) walk(rules);
  }
  const cs = getComputedStyle(document.documentElement);
  for (const name of Array.from(cs)) if (name.startsWith('--') && !seen.has(name)) push(name, cs.getPropertyValue(name));
  return out;
}
"""

SET_JS = r"""
(spec) => {
  const el = (() => { try { return document.querySelector(spec.selector); } catch (e) { return null; } })();
  if (!el) return null;
  el.scrollIntoView({ block: 'center', inline: 'center' });
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  const out = { rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
                tag: el.tagName.toLowerCase(), text: (el.innerText || '').trim().slice(0, 120) };
  for (const p of spec.props) out[p] = cs.getPropertyValue(p);
  out.transition = cs.transition;
  return out;
}
"""


def _playwright_module() -> str | None:
    import capture
    mod = capture.resolve_playwright()
    return str(mod) if mod else None


def run(page_url: str, evaluate: str, arg, viewport=(1440, 900), wait: int = 1500) -> dict | list | None:
    """Load page_url and evaluate the arrow function IN THE PAGE with one JSON argument."""
    script = (
        "const { chromium } = require(process.env.LEWITT_PLAYWRIGHT || 'playwright');\n"
        "(async () => {\n"
        f"  const browser = await chromium.launch({{ headless: true }});\n"
        f"  const page = await browser.newPage({{ viewport: {{ width: {viewport[0]}, height: {viewport[1]} }} }});\n"
        f"  await page.goto({json.dumps(page_url)}, {{ waitUntil: 'domcontentloaded', timeout: 45000 }});\n"
        f"  await page.waitForTimeout({wait});\n"
        f"  const fn = ({evaluate});\n"
        f"  const out = await page.evaluate(fn, {json.dumps(arg)});\n"
        "  await browser.close();\n"
        "  process.stdout.write(JSON.stringify(out === undefined ? null : out));\n"
        "})().catch((e) => { console.error(String(e)); process.exit(1); });\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "probe.js"
        f.write_text(script)
        env = dict(os.environ)
        mod = _playwright_module()
        if mod:
            env["LEWITT_PLAYWRIGHT"] = mod
        proc = subprocess.run(["node", str(f)], capture_output=True, text=True, env=env, timeout=180)
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return None


def read_vars(page_url: str) -> dict:
    got = run(page_url, VAR_JS, None)
    return got if isinstance(got, dict) else {"lewitt": {}, "shadcn": {}, "other": {}}


def read_styles(page_url: str, selectors: list[str], props: list[str] | None = None, one_load: bool = False) -> dict:
    """Computed styles per selector. one_load=True probes all selectors in a single page load."""
    props = props or PROPS
    if one_load:
        batch = r"""
(specs) => {
  const out = {};
  for (const spec of specs) {
    const el = (() => { try { return document.querySelector(spec.selector); } catch (e) { return null; } })();
    if (!el) continue;
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const rec = { selector: spec.selector, tag: el.tagName.toLowerCase(),
                  text: (el.innerText || '').trim().slice(0, 120),
                  rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)] };
    for (const p of spec.props) rec[p] = cs.getPropertyValue(p);
    rec.transition = cs.transition;
    out[spec.selector] = rec;
  }
  return out;
}
"""
        got = run(page_url, batch, [{"selector": s, "props": props} for s in selectors])
        return got if isinstance(got, dict) else {}
    out = {}
    for sel in selectors:
        res = run(page_url, SET_JS, {"selector": sel, "props": props}, wait=800)
        if res:
            res["selector"] = sel
            out[sel] = res
    return out
