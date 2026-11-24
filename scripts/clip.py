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
  };
}
"""


def run(page_url: str, script_body: str, wait: list[dict]) -> list[dict]:
    """One page load, a scripted timeline: [{'action':'snapshot'|'hover'|'click'|'wait', ...}]."""
    plan = json.dumps(wait)
    js = f"""
const {{ chromium }} = require(process.env.LEWITT_PLAYWRIGHT || 'playwright');
(async () => {{
  const browser = await chromium.launch({{ headless: true }});
  const ctx = await browser.newContext({{ viewport: {{ width: 1440, height: 900 }} }});
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await page.goto({json.dumps(page_url)}, {{ waitUntil: 'domcontentloaded', timeout: 45000 }});
  await page.waitForTimeout(2500);
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
    if (step.snapshot) out.push({{ name: step.name, sel: step.snapshot, state: await page.evaluate({STATE_JS}, step.snapshot) }});
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


def slot_for(dna: dict, resolved: dict, colour: str, purpose: str) -> dict:
    """Map a source colour to the run's semantic slot with the closest value."""
    best, best_d = None, None
    kind = "fg" if purpose == "fg" else "bg"
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


def write_md(brick: dict, path: Path) -> None:
    s = brick["source"]
    lines = [
        f"# brick — {s['module']}", "",
        f"- url: {s['url']}", f"- found by: {s['how']} · trigger `<{s['triggerTag']}>` “{s['triggerText']}”",
        f"- action: **{brick['action']}** · camera: {brick['camera']['width']}×{brick['camera']['height']}",
        f"- instructions: `{brick['sourceRun']}` (dna.json {brick['schemaVersion']})",
        f"- captured: {brick['capturedAt']}", "",
        "## States", "",
        "| State | geometry | opacity | transform | transitions running |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, st in brick["states"].items():
        if name.startswith("_"):
            continue
        if not st:
            lines.append(f"| {name} | missing | — | — | — |")
            continue
        lines.append(f"| {name} | {st['rect']} | {st['opacity']} | {st['transform'][:32]} | {len(st['anims'])} |")
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
        slot = v.get("slot")
        lines.append(f"- `{k}`: source `{v['value']}` → slot `{slot}`"
                     + (f" (`var({v['css']})` = `{v['resolved']}`, Δ{v['delta']})" if slot else " — **no slot matched, pick one**"))
    lines += ["", "## State machine", ""]
    for transition in brick["states"].get("_machine", []):
        lines.append(f"- **{transition['from']} → {transition['to']}**: {transition['how']}"
                     + (f" (observed: {transition['observed']})" if transition.get("observed") is not None else " (not observed)"))
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Clip one interaction-ready block out of a live site")
    ap.add_argument("--url", required=True)
    ap.add_argument("--dest", required=True, help="a lewitt run directory (provides dna.json for skin slots)")
    ap.add_argument("--find", help="visible text of the trigger")
    ap.add_argument("--selector", help="CSS selector of the trigger")
    ap.add_argument("--action", default="hover", choices=["hover", "click", "toggle"])
    ap.add_argument("--slug", default=None)
    args = ap.parse_args()

    run_dir = Path(args.dest).expanduser().resolve()
    dna_path = run_dir / "dna.json"
    if not dna_path.exists():
        print("FAIL: --dest must be a lewitt run (dna.json missing)", file=sys.stderr)
        return 2
    dna = json.loads(dna_path.read_text())
    resolved = ba.resolve_tokens(dna["tokens"], (dna.get("meta", {}).get("modes") or ["default"])[0])

    found = page_probe.run(args.url, FIND_JS, {"text": args.find or "", "selector": args.selector or ""})
    if not found or found.get("error"):
        print("FAIL: " + ((found or {}).get("error") or "could not locate the trigger"), file=sys.stderr)
        return 2

    slug = args.slug or re.sub(r"[^a-z0-9]+", "-", (args.find or args.selector or "block").lower()).strip("-")[:40]
    out_dir = run_dir / "clips" / slug
    (out_dir / "shots").mkdir(parents=True, exist_ok=True)
    tx, ty = found["moduleBox"][0] + found["moduleBox"][2] // 2, found["moduleBox"][1] + found["moduleBox"][3] // 2
    trig = found.get("triggerBox") or [tx, ty, 1, 1]
    click_x, click_y = None, None
    click_point = page_probe.run(args.url, r"""
      (arg) => { const el = document.querySelector(arg.sel); if (!el) return null;
        el.scrollIntoView({ block: 'center' });
        const r = el.getBoundingClientRect(); return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) }; }
    """, {"sel": found["trigger"]}) or {}
    click_x = click_point.get("x", tx)
    click_y = click_point.get("y", ty)

    name = out_dir.name
    shot = lambda s: str(out_dir / "shots" / f"{s}.png")
    target = found.get("stateful") or found["module"]     # what actually moves on activation
    snap = lambda name, sel, with_shot=False: {
        "action": "snapshot", "name": name, "sel": sel, "snapshot": sel,
        **({"shot": shot(name)} if with_shot else {}),
    }
    timeline = [snap("before", found["module"], True)]
    if args.action == "hover":
        timeline += [
            {"action": "hover", "x": click_x, "y": click_y, "wait": 60},
            snap("during", found["module"], True),
            {"action": "shake", "x": click_x, "y": click_y, "wait": 120},
            snap("settled", found["module"]),
            {"action": "move", "wait": 400},
            snap("after", found["module"], True),
        ]
    else:
        timeline += [
            snap("before_target", target),
            {"action": "click", "x": click_x, "y": click_y, "wait": 80},
            snap("during", target, True),
            {"action": "move", "wait": 600},
            snap("after", target, True),
        ]
        if args.action == "toggle":
            timeline += [
                {"action": "click", "x": click_x, "y": click_y, "wait": 700},
                snap("restored", target),
            ]

    states = {s["name"]: s["state"] for s in run(args.url, "", timeline)}
    layout = page_probe.run(args.url, LAYOUT_JS, found["module"])

    before = states.get("before")
    skin = {}
    for key, purpose in (("background", "bg"), ("color", "fg")):
        if before:
            skin[key] = slot_for(dna, resolved, before[key], "action" if args.action != "hover" else "bg")
    if states.get("during") and states["during"].get("background") != (before or {}).get("background"):
        skin["background_during"] = slot_for(dna, resolved, states["during"]["background"], "bg")
    skin["__layout"] = layout

    observed_hover = "during" in states and bool(diff(before, states.get("during")))
    observed_settled = states.get("settled") is not None
    if args.action == "hover":
        machine = [
            {"from": "idle", "to": "hover", "how": "pointer enters the module (CSS :hover or pointer handlers)", "observed": observed_hover},
            {"from": "hover", "to": "settled", "how": "transition finishes; nothing else moves", "observed": bool(diff(before, states.get("settled")))},
            {"from": "settled", "to": "idle", "how": "pointer leaves the module; every computed value returns to baseline", "observed": diff(before, states.get("after")) == {}},
        ]
    else:
        opens = bool(diff(states.get("before_target"), states.get("after")))
        closes = args.action == "toggle" and diff(states.get("before_target"), states.get("restored")) == {} and opens
        machine = [
            {"from": "idle", "to": "open", "how": "click (or keyboard equivalent) on the trigger", "observed": opens},
            {"from": "open", "to": "idle", "how": "second click, Escape, or click outside", "observed": closes},
        ]

    notes = [
        "Drive the state with a class the project owns (e.g. `is-open`), never with source-site classes.",
        f"Animate only the properties that changed: {', '.join(sorted({k for d in [diff(before, states.get('during'))] for k in d})) or 'none'}.",
        "Use the source's transition string for timing; replace colours and faces with the mapped slots above.",
        "Keep the geometry contract: the module's box is " + str((before or {}).get("rect")) + ". Layout inside it may change, the box may not.",
        "If a property did not change in the recording, do not invent a transition for it.",
    ]
    cleanup = [
        "Remove any injected helper styles before leaving the page.",
        "Close any window an activation opened; the recording never submits forms or logs in.",
        "Keep shots/ next to brick.md so the geometry can be re-checked after implementation.",
    ]
    brick = {
        "version": "0.1.0",
        "capturedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sourceRun": run_dir.name,
        "schemaVersion": dna.get("schemaVersion"),
        "action": args.action,
        "camera": {"width": 1440, "height": 900},
        "source": {"url": args.url, **{k: found[k] for k in ("how", "trigger", "triggerText", "triggerTag", "module", "moduleBox")}},
        "states": {k: v for k, v in states.items() if not k.startswith("_")},
        "deltas": {
            "module.hover": diff(before, states.get("during")) if args.action == "hover" else {},
            "module.settled": diff(before, states.get("settled")),
            "stateful.open": diff(states.get("before_target"), states.get("after")) if args.action != "hover" else {},
            "stateful.closed": diff(states.get("before_target"), states.get("restored")) if args.action == "toggle" else {},
        },
        "skin": skin,
        "notes": notes,
        "cleanup": cleanup,
    }
    brick["states"]["_machine"] = machine
    (out_dir / "brick.json").write_text(json.dumps(brick, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_md(brick, out_dir / "brick.md")
    print(f"[CLIPPED] {found['module']}  ({found['how']})")
    for target, d in brick["deltas"].items():
        print(f"  {target}: {', '.join(d) if d else 'no computed change'}")
    print(f"wrote {out_dir}/brick.md and brick.json and shots/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
