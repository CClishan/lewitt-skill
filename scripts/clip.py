#!/usr/bin/env python3
"""lewitt clip — lift one interaction-ready block out of a live site, stripped of its skin.

Phase 1 of `lewitt clip`: a single module, one interaction, a round-trip state machine.
The block is found by selector or by visible text, the interaction is triggered with real CDP
input, and every state is recorded as geometry + motion deltas. Source colours and faces are
mapped to the run's semantic slots so the brick drops into a project that never saw the source.

    python3 scripts/clip.py --url https://example.com --find "See how it works" \
        --dest runs/example.com [--action hover|click|toggle]

Outputs in `{dest}/clips/{slug}/`:
    brick.json   locator, states, deltas, slot mapping, cleanup
    brick.md     the brick: states, deltas, skin mapping, implementation notes
    shots/        before / during / after screenshots
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import page_probe  # noqa: E402
import build_artifacts as ba  # noqa: E402

FIND_JS = r"""
(arg) => {
  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
  const box = (node) => { const r = node.getBoundingClientRect();
    return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; };
  const locator = (node) => {
    if (node.id) return '#' + CSS.escape(node.id);
    const cls = String(node.className || '').trim().split(/\s+/).filter((c) => c && !/^is-|^has-/.test(c)).slice(0, 2);
    let sel = node.tagName.toLowerCase() + cls.map((c) => '.' + CSS.escape(c)).join('');
    if (document.querySelectorAll(sel).length !== 1) {
      const parent = node.parentElement;
      const idx = parent ? Array.from(parent.children).indexOf(node) : 0;
      sel = (parent && parent.id ? '#' + CSS.escape(parent.id) + ' > ' : '') + sel + ':nth-child(' + (idx + 1) + ')';
    }
    return sel;
  };

  // pick the trigger: selector first, then exact text, then a substring match
  let el = null, how = null;
  if (arg.selector) {
    el = document.querySelector(arg.selector);
    how = 'selector';
    if (!el) return { error: 'selector not found: ' + arg.selector };
  } else {
    const all = Array.from(document.querySelectorAll('a, button, [role="button"]'));
    el = all.find((n) => norm(n.innerText) === norm(arg.text));
    how = 'text-exact';
    if (!el) { el = all.find((n) => norm(n.innerText).includes(norm(arg.text))); how = 'text-partial'; }
    if (!el) return { error: 'no clickable element contains "' + arg.text + '"' };
  }

  el.scrollIntoView({ block: 'center', inline: 'center' });

  // with a selector the caller already named the module's trigger: walk up twice at most.
  // otherwise climb to the nearest block-looking ancestor (card / tile / panel / section).
  const looksLikeBlock = (node) => node && node.matches('article, li, section, [class*="card"], [class*="tile"], [class*="panel"], [class*="item"], [class*="box"]');
  let module = el;
  // a text match lands on the trigger itself, so climb until the box is block-sized and tag-shaped;
  // a selector names the trigger too, so the same rule applies to both paths.
  for (let i = 0; i < 6; i++) {
    const parent = module.parentElement;
    if (!parent || parent.tagName.toLowerCase() === 'body') break;
    module = parent;
    const mr = module.getBoundingClientRect();
    const blocky = looksLikeBlock(module);
    if (blocky && mr.width >= 280 && mr.height >= 100) break;
    if (!blocky && mr.width >= 280 && mr.height >= 100 && mr.height <= 600 && /^(article|li|section|div)$/.test(module.tagName.toLowerCase()) && /card|tile|panel|item|box|hero|banner/i.test(String(module.className))) break;
  }

  // drop media beyond the first two: a brick is instructions, not an asset dump
  const imgs = document.querySelectorAll('img, video');
  for (let i = 0; i < imgs.length; i++) if (i > 2) imgs[i].removeAttribute('src');

  // the stateful descendant (drawer / panel / menu) is what actually moves on activation
  const inner = el.closest('[class]') && (el.parentElement || el);
  const candidates = inner ? Array.from(inner.querySelectorAll('[class]')).filter((n) => n !== el) : [];
  const stateful = candidates.find((n) => /panel|drawer|menu|content|body|collapse|dropdown|sheet/i.test(String(n.className))) || candidates[0] || null;

  return {
    how,
    stateful: stateful ? locator(stateful) : null,
    trigger: locator(el),
    triggerText: (el.innerText || '').trim().slice(0, 80),
    triggerTag: el.tagName.toLowerCase(),
    triggerBox: box(el),
    module: locator(module),
    moduleBox: box(module),
  };
}
"""

STATE_JS = r"""
(sel) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  const anims = (el.getAnimations ? el.getAnimations({ subtree: true }) : []).map((a) => {
    let effect = null;
    try { effect = a.effect.getKeyframes().map((k) => ({ offset: k.offset, props: Object.keys(k).filter((x) => x !== 'offset' && x !== 'easing' && x !== 'composite') })).slice(0, 2); } catch (e) {}
    return { name: a.animationName || a.id || '(transition)', playState: a.playState,
             currentTime: Math.round(a.currentTime || 0), effect };
  });
  return {
    rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
    opacity: cs.opacity, transform: cs.transform,
    display: cs.display, visibility: cs.visibility,
    background: cs.backgroundColor, color: cs.color,
    'border-radius': cs.borderRadius, 'box-shadow': cs.boxShadow,
    transition: cs.transition, animation: cs.animation,
    anims,
    timing: (() => {
      const ms = (v) => (String(v || '').match(/([\d.]+)\s*(m?s)/g) || []).map((x) => {
        const n = parseFloat(x); return /ms$/.test(x) ? n : n * 1000; });
      const tr = ms(cs.transitionDuration).filter((n) => n > 0);
      const an = ms(cs.animationDuration).filter((n) => n > 0);
      const transformPx = (() => {
        const m = /matrix\(([^)]+)\)/.exec(cs.transform || '');
        if (!m) return [0, 0];
        const p = m[1].split(',').map((x) => parseFloat(x.trim()));
        return [Math.round(p[4] || 0), Math.round(p[5] || 0)];
      })();
      return { transitionMaxMs: tr.length ? Math.max(...tr) : 0, animationMaxMs: an.length ? Math.max(...an) : 0, transformPx };
    })(),
  };
}
"""


def run(page_url: str, script_body: str, steps_in: list[dict], reduced: bool = False) -> list[dict]:
    """One page load, a scripted timeline. reduced=True emulates prefers-reduced-motion: reduce."""
    plan = json.dumps(steps_in)
    media_arg = '"reduce"' if reduced else '"no-preference"' 
    js = f"""
const {{ chromium }} = require(process.env.LEWITT_PLAYWRIGHT || 'playwright');
(async () => {{
  const browser = await chromium.launch({{ headless: true }});
  const ctx = await browser.newContext({{ viewport: {{ width: 1440, height: 900 }} }});
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await page.goto({json.dumps(page_url)}, {{ waitUntil: 'domcontentloaded', timeout: 45000 }});
  await cdp.send('Emulation.setEmulatedMedia', {{ features: [{{ name: 'prefers-reduced-motion', value: {media_arg} }}] }});
  await page.waitForTimeout(2500);
  const reduceActive = await page.evaluate(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const steps = {plan};
  const out = [];
  for (const step of steps) {{
    if (step.action === 'hover') {{
      await cdp.send('Input.dispatchMouseEvent', {{ type: 'mouseMoved', x: step.x, y: step.y, button: 'none' }});
    }} else if (step.action === 'click') {{
      await cdp.send('Input.dispatchMouseEvent', {{ type: 'mouseMoved', x: step.x, y: step.y, button: 'none' }});
      await cdp.send('Input.dispatchMouseEvent', {{ type: 'mousePressed', x: step.x, y: step.y, button: 'left', clickCount: 1 }});
      await cdp.send('Input.dispatchMouseEvent', {{ type: 'mouseReleased', x: step.x, y: step.y, button: 'left', clickCount: 1 }});
    }} else if (step.action === 'move') {{
      await cdp.send('Input.dispatchMouseEvent', {{ type: 'mouseMoved', x: 2, y: 2, button: 'none' }});
    }} else if (step.action === 'shake') {{
      await cdp.send('Input.dispatchMouseEvent', {{ type: 'mouseMoved', x: step.x + 18, y: step.y + 6, button: 'none' }});
    }}
    if (step.wait) await page.waitForTimeout(step.wait);
    if (step.shot) await page.screenshot({{ path: step.shot }});
    if (step.snapshot) out.push({{ name: step.name, sel: step.snapshot, reduceActive, state: await page.evaluate({STATE_JS}, step.snapshot) }});
  }}
  await browser.close();
  process.stdout.write(JSON.stringify(out));
}})().catch((e) => {{ console.error(String(e)); process.exit(1); }});
"""
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "clip.js"
        f.write_text(js)
        import os, subprocess
        env = dict(os.environ)
        mod = __import__("capture").resolve_playwright()
        if mod:
            env["LEWITT_PLAYWRIGHT"] = str(mod)
        proc = subprocess.run(["node", str(f)], capture_output=True, text=True, env=env, timeout=300)
    if proc.returncode != 0:
        raise SystemExit("clip capture failed: " + proc.stderr.strip()[-500:])
    return json.loads(proc.stdout.strip().splitlines()[-1])


SCRIPT_SHOTS = []


def shadcn_map(before: dict, during: dict | None, action: str) -> dict:
    """Map an element to shadcn/Tailwind v4 slots by role, not by nearest hex."""
    out = {}
    bg = (before or {}).get("background")
    fg = (before or {}).get("color")
    radius = (before or {}).get("border-radius")
    if action == "hover":
        out["surface"] = {"value": bg, "slot": "--card", "css": "var(--card)",
                          "why": "the module is a passive block: card surface"}
        if during and during.get("background") != bg:
            out["surface_hover"] = {"value": during["background"], "slot": "--muted", "css": "var(--muted)",
                                    "why": "hover darkens/lightens the block: muted is the neutral hover surface"}
        out["text"] = {"value": fg, "slot": "--card-foreground", "css": "var(--card-foreground)",
                       "why": "body text inside a card"}
    else:
        out["trigger_fill"] = {"value": bg, "slot": "--primary", "css": "var(--primary)",
                               "why": "the control that changes state is the primary action"}
        out["trigger_label"] = {"value": fg, "slot": "--primary-foreground", "css": "var(--primary-foreground)",
                                "why": "label on the primary action"}
        out["surface"] = {"value": None, "slot": "--card", "css": "var(--card)",
                          "why": "the revealed panel is a card"}
    if radius:
        out["radius"] = {"value": radius, "slot": "--radius", "css": "var(--radius)",
                         "why": "shadcn derives every control radius from --radius"}
    return out


def lewitt_map(dna: dict, resolved: dict, before: dict, during: dict | None, action: str) -> dict:
    """The v1.1 behaviour: nearest semantic token of this run."""
    out = {}
    for key, purpose in (("background", "bg"), ("color", "fg")):
        if before:
            out[key] = slot_for(dna, resolved, before[key], "action" if action != "hover" else "bg")
    if during and during.get("background") != (before or {}).get("background"):
        out["background_during"] = slot_for(dna, resolved, during["background"], "bg")
    return out


def slot_for(dna: dict, resolved: dict, colour: str, purpose: str) -> dict:
    """Map a source colour to the run's semantic slot with the closest value."""
    best, best_d = None, None
    for tok in dna["tokens"]:
        if tok["type"] != "color" or tok["layer"] != "semantic":
            continue
        want_action = tok["id"].startswith("color/action") or tok["id"].startswith("color/link")
        if purpose == "action" and not want_action:
            continue
        dist = __import__("cert").colour_distance(resolved[tok["id"]]["resolved"], colour) if colour else None
        if not dist:
            continue
        d = dist["delta"]
        if best_d is None or d < best_d:
            best, best_d = tok, d
    if not best:
        return {"value": colour, "slot": None, "match": "none"}
    return {"value": colour, "slot": best["id"], "css": best["css"],
            "resolved": resolved[best["id"]]["resolved"], "delta": best_d}


def diff(a: dict | None, b: dict | None) -> dict:
    if not a or not b:
        return {}
    out = {}
    for k in ("rect", "opacity", "transform", "background", "color", "border-radius", "box-shadow"):
        if a.get(k) != b.get(k):
            out[k] = [a.get(k), b.get(k)]
    return out


def reduced_report(std: dict, red: dict, action: str) -> dict:
    """Compare the normal and reduced-motion recordings of the element that actually moves."""
    s_during, r_during = std.get("during_target"), red.get("during_target")
    s_t = (s_during or {}).get("timing") or {}
    r_t = (r_during or {}).get("timing") or {}
    s_px = abs((s_t.get("transformPx") or [0, 0])[1])
    r_px = abs((r_t.get("transformPx") or [0, 0])[1])
    s_ms = max(s_t.get("transitionMaxMs", 0), s_t.get("animationMaxMs", 0))
    r_ms = max(r_t.get("transitionMaxMs", 0), r_t.get("animationMaxMs", 0))
    same_end = ((s_during or {}).get("rect") == (r_during or {}).get("rect")
                and (s_during or {}).get("transform") == (r_during or {}).get("transform"))
    if r_during is None:
        status, reason = "unrecorded", "the reduced-motion pass produced no snapshot for this state"
    elif s_during is None:
        status, reason = "unrecorded", "the normal pass produced no snapshot for this state"
    elif r_ms == 0 and s_ms > 0:
        status, reason = "degraded-to-none", f"transition removed entirely (normal {s_ms:g}ms)"
    elif r_ms < s_ms * 0.8 and (same_end or action != "hover") and r_px <= s_px:
        status, reason = "degraded", (f"{s_ms:g}ms → {r_ms:g}ms, travel {s_px:g}px → {r_px:g}px"
                                      + ("" if same_end else ", end state differs"))
    elif r_px == 0 and s_px > 0:
        status, reason = "degraded", f"motion removed: travel {s_px:g}px → 0px, end state kept"
    else:
        status, reason = "not-degraded", (
            f"same motion under reduce: {s_ms:g}ms → {r_ms:g}ms, travel {s_px:g}px → {r_px:g}px")
    return {
        "emulated": bool(red.get("_reduceActive", True)),
        "status": status,
        "reason": reason,
        "normal": {"durationMs": s_ms, "travelPx": round(s_px, 1), "transform": (s_during or {}).get("transform")},
        "reduced": {"durationMs": r_ms, "travelPx": round(r_px, 1), "transform": (r_during or {}).get("transform")},
        "endStateKept": same_end,
    }


def write_md(brick: dict, path: Path) -> None:
    src = brick["source"]
    system = brick["slots"]["system"]
    lines = [
        f"# brick — {src['module']}", "",
        f"> **Slot system: `{system}`** — every colour and radius below is written as a "
        + ("shadcn / Tailwind v4 variable (`var(--card)`, `var(--muted)`…). "
           if system == "shadcn" else
           "lewitt variable (`var(--lw-…)`) from this run. ")
        + "Copying the source's hardcoded hex or rgb values into your project is a **hard violation**: "
        "re-run `lewitt cert` and it will reject the build.", "",
        f"- url: {src['url']}", f"- found by: {src['how']} · trigger `<{src['triggerTag']}>` “{src['triggerText']}”",
        f"- action: **{brick['action']}** · camera: {brick['camera']['width']}×{brick['camera']['height']}",
        f"- instructions: " + (f"`{brick['sourceRun']}` (dna.json {brick['schemaVersion']})" if brick.get("schemaVersion")
                                else "none — standalone clip, skin mapping by role"),
        f"- slot source: " + (brick["slots"].get("from") or "—"),
        f"- captured: {brick['capturedAt']}", "",
        "## States", "",
        "| State | geometry | opacity | transform | transitions running | duration |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, st in brick["states"].items():
        if name.startswith("_"):
            continue
        if not st:
            lines.append(f"| {name} | missing | — | — | — | — |")
            continue
        tm = st.get("timing") or {}
        dur = max(tm.get("transitionMaxMs", 0), tm.get("animationMaxMs", 0))
        lines.append(f"| {name} | {st['rect']} | {st['opacity']} | {st['transform'][:32]} | "
                     f"{len(st['anims'])} | {dur:g}ms |")
    lines += ["", "## Deltas", ""]
    for target, d in brick["deltas"].items():
        if not d:
            lines.append(f"- **{target}**: no computed change")
            continue
        for k, v in d.items():
            lines.append(f"- **{target}** · `{k}`: `{v[0]}` → `{v[1]}`")
    lines += ["", "## Skin mapping (stripped)", ""]
    for k, v in brick["skin"].items():
        if k.startswith("__"):
            continue
        target = v.get("slot")
        if system == "shadcn":
            lines.append(f"- `{k}`: source `{v['value']}` → `{v['css']}`" + (f" — {v['why']}" if v.get("why") else "")
                         + ("  · **no slot — pick one**" if not target else ""))
        else:
            lines.append(f"- `{k}`: source `{v['value']}` → slot `{target}`"
                         + (f" (`var({v['css']})` = `{v['resolved']}`, Δ{v['delta']})" if target else " — **no slot matched, pick one**"))
    lines += ["", "## State machine", ""]
    for transition in brick["states"].get("_machine", []):
        lines.append(f"- **{transition['from']} → {transition['to']}**: {transition['how']}"
                     + (f" (observed: {transition['observed']})" if transition.get("observed") is not None else " (not observed)"))
    rm = brick.get("reducedMotion") or {}
    lines += ["", "## Reduced motion", ""]
    if not rm:
        lines.append("_Not recorded._")
    else:
        flag = {"degraded": "✅ observed", "degraded-to-none": "✅ observed",
                "not-degraded": "⚠️ **not degraded — the source keeps moving**",
                "unrecorded": "⚠️ not recorded"}.get(rm["status"], rm["status"])
        lines += [
            f"- emulated with CDP `Emulation.setEmulatedMedia` `prefers-reduced-motion: reduce` "
            f"(matchMedia in page: {rm.get('emulated')})",
            f"- status: **{rm['status']}** — {flag}",
            f"- detail: {rm['reason']}",
            "",
            "| Recording | duration | travel (translateY) | transform |",
            "| --- | --- | --- | --- |",
            f"| normal | {rm['normal']['durationMs']:g}ms | {rm['normal']['travelPx']:g}px | `{str(rm['normal']['transform'])[:40]}` |",
            f"| reduced | {rm['reduced']['durationMs']:g}ms | {rm['reduced']['travelPx']:g}px | `{str(rm['reduced']['transform'])[:40]}` |",
            "",
        ]
        if rm["status"] == "not-degraded":
            lines.append("> The source does not honour `prefers-reduced-motion` here. Your implementation must — "
                         "either drop the transition or keep the end state and remove the travel. "
                         "This is a place to improve on the source, not to copy it.")
        elif rm["status"] == "degraded-to-none":
            lines.append("> Under reduce the source removes the transition entirely. Mirror that: "
                         "apply the end state instantly, no cross-fade.")
        elif rm["status"] == "degraded":
            lines.append("> Under reduce the source keeps the end state and shortens/removes the travel. "
                         "Mirror that ratio rather than inventing one.")
    lines += ["", "## Implementation notes", ""]
    for note in brick["notes"]:
        lines.append(f"- {note}")
    layout = brick["skin"].get("__layout")
    if layout:
        lines += ["", "## Content skeleton (no skin)", "", "| tag | role | text |", "| --- | --- | --- |"]
        for row in layout["rows"]:
            lines.append(f"| `{row['tag']}` | {row['role']} | {row['text'][:60]} |")
    lines += ["", "## Cleanup", ""]
    for step in brick["cleanup"]:
        lines.append(f"- {step}")
    lines += ["", "_A brick is instructions, not a clone: the geometry, timing and state machine come from "
              "the source; colour and type come from your project's slots._", ""]
    path.write_text("\n".join(lines))


LAYOUT_JS = r"""
(sel) => {
  const root = document.querySelector(sel);
  if (!root) return null;
  const rows = [];
  for (const el of root.querySelectorAll('h1,h2,h3,h4,p,button,a,li,span,div')) {
    const text = (el.innerText || '').trim();
    if (!text) continue;
    const direct = Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!direct) continue;
    rows.push({ tag: el.tagName.toLowerCase(), role: el.getAttribute('role') || el.tagName.toLowerCase(), text });
    if (rows.length >= 24) break;
  }
  return { rows };
}
"""


def build_timeline(action: str, module: str, target: str, click: tuple[int, int], shot) -> list[dict]:
    """States per action. `target` is the stateful element that moves on activation."""
    x, y = click

    def snap(name, sel, with_shot=False):
        return {"action": "snapshot", "name": name, "sel": sel, "snapshot": sel,
                **({"shot": shot(name)} if with_shot else {})}

    steps = [snap("before", module, True)]
    if action == "hover":
        steps += [
            {"action": "hover", "x": x, "y": y, "wait": 60},
            snap("during", module, True),
            {"action": "shake", "x": x, "y": y, "wait": 120},
            snap("settled", module),
            snap("during_target", target),
            {"action": "move", "wait": 400},
            snap("after", module, True),
        ]
    else:
        steps += [
            snap("before_target", target),
            {"action": "click", "x": x, "y": y, "wait": 80},
            snap("during_target", target, True),
            {"action": "move", "wait": 600},
            snap("after", target, True),
        ]
        if action == "toggle":
            steps += [
                {"action": "click", "x": x, "y": y, "wait": 700},
                snap("restored", target),
            ]
    return steps


def collect(url: str, steps: list[dict], reduced: bool) -> tuple[dict, dict]:
    rows = run(url, "", steps, reduced=reduced)
    return {r["name"]: r["state"] for r in rows}, {"_reduceActive": rows[0]["reduceActive"] if rows else False}


def main() -> int:
    ap = argparse.ArgumentParser(description="Clip one interaction-ready block out of a live site")
    ap.add_argument("--url", required=True)
    ap.add_argument("--dest", help="output root (a lewitt run directory, or any folder in standalone mode)")
    ap.add_argument("--out", help="explicit output directory; wins over --dest")
    ap.add_argument("--find", help="visible text of the trigger")
    ap.add_argument("--selector", help="CSS selector of the trigger")
    ap.add_argument("--action", default="hover", choices=["hover", "click", "toggle"])
    ap.add_argument("--slots", default="shadcn", choices=["shadcn", "lw"],
                    help="target slot system (default: shadcn / Tailwind v4; lw needs dna.json)")
    ap.add_argument("--slug", default=None)
    ap.add_argument("--no-reduced", action="store_true", help="skip the reduced-motion pass")
    args = ap.parse_args()
    if not args.out and not args.dest:
        ap.error("give --dest (or --out)")

    dest = Path((args.out or args.dest)).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    dna_path = Path(args.dest).expanduser().resolve() / "dna.json" if args.dest else None
    dna = json.loads(dna_path.read_text()) if dna_path and dna_path.exists() else None
    if args.slots == "lw" and not dna:
        print("FAIL: --slots=lw needs a run with dna.json in --dest", file=sys.stderr)
        return 2
    resolved = ba.resolve_tokens(dna["tokens"], (dna.get("meta", {}).get("modes") or ["default"])[0]) if dna else {}

    found = page_probe.run(args.url, FIND_JS, {"text": args.find or "", "selector": args.selector or ""})
    if not found or found.get("error"):
        print("FAIL: " + ((found or {}).get("error") or "could not locate the trigger"), file=sys.stderr)
        return 2

    slug = args.slug or re.sub(r"[^a-z0-9]+", "-", (args.find or args.selector or "block").lower()).strip("-")[:40]
    domain = re.sub(r"^www\.", "", re.sub(r"^https?://", "", args.url).split("/")[0])
    domain = re.sub(r"[^a-z0-9.-]+", "-", domain.lower()).strip(".-") or "local"
    if args.out:                      # explicit directory: use it verbatim
        out_dir = dest
    elif args.slots == "shadcn" and not dna:
        out_dir = dest / "clips" / f"{domain}-{slug}"
    else:
        out_dir = dest / "clips" / slug
    (out_dir / "shots").mkdir(parents=True, exist_ok=True)

    point = page_probe.run(args.url, r"""
      (arg) => { const el = document.querySelector(arg.sel); if (!el) return null;
        el.scrollIntoView({ block: 'center' });
        const r = el.getBoundingClientRect(); return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) }; }
    """, {"sel": found["trigger"]}) or {}
    box = found["moduleBox"]
    click = (point.get("x", box[0] + box[2] // 2), point.get("y", box[1] + box[3] // 2))
    target = found.get("stateful") or found["module"]

    shot = lambda s: str(out_dir / "shots" / f"{s}.png")
    steps = build_timeline(args.action, found["module"], target, click, shot)
    states, std_meta = collect(args.url, steps, reduced=False)

    red = {}
    rm = {}
    if not args.no_reduced:
        red_steps = []
        for st in steps:
            st = dict(st)
            if st.get("shot"):
                st["shot"] = shot(st["name"] + "-reduced")
            red_steps.append(st)
        red, red_meta = collect(args.url, red_steps, reduced=True)
        rm = reduced_report(states, red, args.action)
        rm["emulated"] = bool(red_meta.get("_reduceActive"))

    before = states.get("before")
    during = states.get("during")
    if args.slots == "lw":
        skin = lewitt_map(dna, resolved, before or {}, during, args.action)
        slot_from = f"lewitt run `{dna_path.parent.name}` (dna.json {dna.get('schemaVersion')})"
    else:
        skin = shadcn_map(before or {}, during, args.action)
        slot_from = "shadcn / Tailwind v4 slots, mapped by role"
    skin["__layout"] = page_probe.run(args.url, LAYOUT_JS, found["module"])

    if args.action == "hover":
        machine = [
            {"from": "idle", "to": "hover", "how": "pointer enters the module (CSS :hover or pointer handlers)",
             "observed": bool(diff(before, during))},
            {"from": "hover", "to": "settled", "how": "transition finishes; nothing else moves",
             "observed": bool(diff(before, states.get("settled")))},
            {"from": "settled", "to": "idle", "how": "pointer leaves the module; every computed value returns to baseline",
             "observed": diff(before, states.get("after")) == {}},
        ]
    else:
        opens = bool(diff(states.get("before_target"), states.get("after")))
        closes = args.action == "toggle" and opens and diff(states.get("before_target"), states.get("restored")) == {}
        machine = [
            {"from": "idle", "to": "open", "how": "click (or keyboard equivalent) on the trigger", "observed": opens},
            {"from": "open", "to": "idle", "how": "second click, Escape, or click outside", "observed": closes},
        ]

    changed = sorted({k for d in [diff(before, during), diff(states.get("before_target"), states.get("after"))] for k in d})
    if args.slots == "shadcn" and args.action != "hover" and states.get("before_target"):
        tgt = states["before_target"]
        skin["surface"] = {"value": tgt.get("background"), "slot": "--card", "css": "var(--card)",
                           "why": "the revealed panel is a card"}
        if tgt.get("color"):
            skin["surface_text"] = {"value": tgt.get("color"), "slot": "--card-foreground",
                                    "css": "var(--card-foreground)", "why": "text inside the revealed panel"}
        if (during or {}).get("background") not in (None, tgt.get("background")):
            skin["surface_open"] = {"value": during["background"], "slot": "--muted", "css": "var(--muted)",
                                    "why": "open state tint"}
    notes = [
        "Drive the state with a class the project owns (e.g. `is-open`), never with source-site classes.",
        f"Animate only the properties that changed: {', '.join(changed) or 'none'}.",
        "Use the source's transition string for timing; take colours from the mapped slots, never from the source.",
        "Keep the geometry contract: the module's box is " + str((before or {}).get("rect")) + ". Layout inside it may change, the box may not.",
        "If a property did not change in the recording, do not invent a transition for it.",
    ]
    if rm.get("status") == "not-degraded":
        notes.append("The source ignores prefers-reduced-motion: implement the reduce branch yourself.")
    elif rm.get("status") in ("degraded", "degraded-to-none"):
        notes.append(f"Mirror the measured reduce branch: {rm['reason']}.")

    cleanup = [
        "Remove any injected helper styles before leaving the page.",
        "Close any window an activation opened; the recording never submits forms or logs in.",
        "Keep shots/ next to brick.md so the geometry can be re-checked after implementation.",
    ]
    brick = {
        "version": "0.2.0",
        "capturedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "run" if dna else "standalone",
        "sourceRun": dna_path.parent.name if dna_path and dna_path.exists() else None,
        "schemaVersion": dna.get("schemaVersion") if dna else None,
        "slots": {"system": args.slots, "from": slot_from},
        "action": args.action,
        "camera": {"width": 1440, "height": 900},
        "source": {"url": args.url, **{k: found[k] for k in ("how", "trigger", "triggerText", "triggerTag", "module", "moduleBox")}},
        "states": states,
        "deltas": {
            "module.hover": diff(before, during) if args.action == "hover" else {},
            "module.settled": diff(before, states.get("settled")),
            "stateful.open": diff(states.get("before_target"), states.get("after")) if args.action != "hover" else {},
            "stateful.closed": diff(states.get("before_target"), states.get("restored")) if args.action == "toggle" else {},
        },
        "skin": skin,
        "reducedMotion": rm,
        "notes": notes,
        "cleanup": cleanup,
    }
    brick["states"]["_machine"] = machine
    (out_dir / "brick.json").write_text(json.dumps(brick, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_md(brick, out_dir / "brick.md")
    print(f"[CLIPPED] {found['module']}  ({found['how']}) · slots={args.slots} · mode={brick['mode']}")
    for key, d in brick["deltas"].items():
        print(f"  {key}: {', '.join(d) if d else 'no computed change'}")
    if rm:
        print(f"  reduced-motion: {rm['status']} — {rm['reason']}")
    print(f"wrote {out_dir}/brick.md and brick.json and shots/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
