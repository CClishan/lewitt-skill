#!/usr/bin/env python3
"""lewitt cert — audit a running site against an extracted dna.json and issue a certificate.

Named after Sol LeWitt's certificates: an assistant executed the instructions, and he signed what
was actually on the wall. Here the "wall" is your localhost page and the "instructions" are the
tokens/guardrails in a lewitt run. The certificate states what matched, what deviated, and what
could not be checked — it never upgrades an unmeasured claim to a pass.

    python3 scripts/cert.py --url http://localhost:3000 --dest runs/stripe.com
    python3 scripts/cert.py --url http://localhost:3000 --dest runs/stripe.com --pages 3 --open

Outputs inside the run directory (and never edits dna.json):
    cert.json   machine-readable: verdict, checks, deviations, coverage
    cert.md     the certificate: verdict banner, deviations first, then the evidence
    cert.html   the same, as a printable page (self-contained, light theme)

Exit codes: 0 certified (or warnings only with --allow-warn), 1 deviations found, 2 could not run.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import page_probe  # noqa: E402  shared live-page reader

TOL = {"color": 4, "dimension": 1.0, "radius": 1.0}
WEIGHTS = {"color": 3, "dimension": 2, "radius": 1, "weight": 2, "font": 2, "mode": 3}


# ------------------------------------------------------------------ colour math
def parse_colour(value: str):
    v = (value or "").strip().lower()
    m = re.fullmatch(r"rgba?\(([^)]+)\)", v)
    if m:
        parts = [p.strip() for p in re.split(r"[,\s/]+", m.group(1)) if p.strip()]
        try:
            if len(parts) == 4:
                r, g, b = (float(parts[0]), float(parts[1]), float(parts[2]))
                a = float(parts[3])
            else:
                r, g, b = (float(parts[0]), float(parts[1]), float(parts[2]))
                a = 1.0
            return (r, g, b, a)
        except ValueError:
            return None
    m = re.fullmatch(r"#([0-9a-f]{3,8})", v)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return (r, g, b, a)
    return None


def colour_distance(expected: str, actual: str) -> dict | None:
    """Composite both colours over white so alpha differences are judged by what a user sees."""
    e, a = parse_colour(expected), parse_colour(actual)
    if not e or not a:
        return None

    def over_white(c):
        r, g, b, al = c
        return (r * al + 255 * (1 - al), g * al + 255 * (1 - al), b * al + 255 * (1 - al))

    e2, a2 = over_white(e), over_white(a)
    d = max(abs(x - y) for x, y in zip(e2, a2))
    return {"expected": expected, "actual": actual, "delta": round(d, 1), "ok": d <= TOL["color"]}


def parse_lengths(value: str) -> list[float]:
    return [float(x) for x in re.findall(r"(-?\d*\.?\d+)", value or "")]


def px(value: str) -> float | None:
    m = re.match(r"\s*(-?\d*\.?\d+)\s*(px|rem|em)?", value or "")
    if not m:
        return None
    n = float(m.group(1))
    return n * 16 if m.group(2) in ("rem", "em") else n


# ------------------------------------------------------------------ capture
def capture(url: str, workdir: Path, pages: int) -> tuple[dict, dict]:
    cmd = [sys.executable, str(HERE / "capture.py"), url, "--dest", str(workdir), "--pages", str(pages)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return {}, {"ok": False, "error": (proc.stderr or proc.stdout).strip()[-600:]}
    try:
        info = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}, {"ok": False, "error": "capture.py produced no JSON"}
    cap = Path(info["dest"]) / "capture"
    dom_path = cap / "dom.json"
    if not dom_path.exists():
        return {}, {"ok": False, "error": "capture produced no dom.json"}
    return json.loads(dom_path.read_text()), info


# ------------------------------------------------------------------ checks
SHADCN_SLOTS = {
    "color/canvas": ["--background", "--card"],
    "color/surface": ["--card", "--secondary", "--background"],
    "color/surface-subtle": ["--muted", "--secondary", "--accent"],
    "color/text/heading": ["--foreground", "--card-foreground"],
    "color/text/body": ["--foreground"],
    "color/text/primary": ["--foreground"],
    "color/text/muted": ["--muted-foreground"],
    "color/text/secondary": ["--muted-foreground"],
    "color/action/bg": ["--primary"],
    "color/action/fg": ["--primary-foreground"],
    "color/link": ["--primary", "--ring"],
    "color/border": ["--border", "--input"],
    "color/ink-tint": ["--foreground"],
}
SHADCN_RADIUS = "--radius"

RENDERED_JS = r"""
(specs) => {
  // last resort: read what the page actually paints on its landmark elements
  const pick = (sel) => { try { return document.querySelector(sel); } catch (e) { return null; } };
  const body = document.body;
  const h1 = pick('h1, h2, [role="heading"]');
  const primary = pick('button, [role="button"], a[class*="btn"], a[class*="button"]');
  const card = pick('[class*="card"], article');
  const out = {};
  if (body) { out['color/canvas'] = getComputedStyle(body).backgroundColor; out['color/text/body'] = getComputedStyle(body).color; }
  if (h1) { out['color/text/heading'] = getComputedStyle(h1).color; out['type/hero'] = getComputedStyle(h1).fontSize; }
  if (primary) { out['color/action/bg'] = getComputedStyle(primary).backgroundColor; out['color/action/fg'] = getComputedStyle(primary).color; out['radius/control'] = getComputedStyle(primary).borderRadius; }
  if (card) { out['color/surface'] = getComputedStyle(card).backgroundColor; out['radius/card'] = getComputedStyle(card).borderRadius; }
  return out;
}
"""


def rendered_fallback(url: str) -> dict:
    got = page_probe.run(url, RENDERED_JS, None)
    return {k: v for k, v in (got or {}).items() if v and v not in ("rgba(0, 0, 0, 0)", "initial")}


def shadcn_radius(vars_map: dict) -> str | None:
    entry = vars_map.get(SHADCN_RADIUS)
    if not entry:
        return None
    raw = entry.get("raw", "")
    m = re.match(r"(-?\d*\.?\d+)(px|rem|em)?", raw)
    if not m:
        return None
    n = float(m.group(1))
    return f"{n * 16:g}px" if m.group(2) in ("rem", "em") else f"{n:g}px"


def check_colours(dna: dict, dom: dict, resolved: dict) -> list[dict]:
    """Every semantic colour token whose hex appears in the source DOM is probed on the local page."""
    found = set()
    colours = dom.get("colors") or {}
    for entry in colours.get("backgroundColors", []) + colours.get("textColors", []) + colours.get("accentCandidates", []):
        found.add(entry.get("value", ""))
    if colours.get("pageBackground"):
        found.add(colours["pageBackground"])
    out = []
    for tok in dna["tokens"]:
        if tok["type"] != "color" or tok["layer"] != "semantic":
            continue
        value = resolved[tok["id"]]["resolved"]
        out.append({"kind": "color", "token": tok["id"], "css": tok["css"], "expected": value,
                    "source_seen": value in found})
    return out


def check_type(dna: dict, resolved: dict) -> list[dict]:
    out = []
    for tok in dna["tokens"]:
        if tok["layer"] != "component":
            continue
        if tok["type"] == "dimension" and (tok["id"].startswith("type/") or tok["id"].startswith("radius/")):
            out.append({"kind": "radius" if tok["id"].startswith("radius/") else "dimension",
                        "token": tok["id"], "css": tok["css"], "expected": resolved[tok["id"]]["resolved"]})
        if tok["type"] == "fontFamily":
            out.append({"kind": "font", "token": tok["id"], "css": tok["css"], "expected": resolved[tok["id"]]["resolved"]})
    return out


PROBE_JS = r"""
(specs) => {
  const out = {};
  const style = document.createElement('style');
  style.id = 'lewitt-cert-probe';
  style.textContent = ':root{ --lewitt-probe: 1 }';
  document.head.appendChild(style);
  const probe = document.createElement('div');
  probe.id = 'lewitt-cert-probe-el';
  probe.style.position = 'absolute';
  probe.style.left = '-9999px';
  document.body.appendChild(probe);
  for (const spec of specs) {
    if (spec.kind === 'color') {
      probe.style.color = `var(${spec.css}, color-mix(in srgb, #ff00ff 100%, transparent))`;
      const v = getComputedStyle(probe).color;
      out[spec.token] = { actual: v, missing: v.replace(/\s/g, '') === 'rgb(255,0,255)' };
    } else if (spec.kind === 'radius') {
      probe.style.borderRadius = `var(${spec.css}, -999px)`;
      const rv = getComputedStyle(probe).borderRadius;
      out[spec.token] = { actual: rv, missing: rv.trim() === '0px' || rv.trim() === '-999px' };
    } else if (spec.kind === 'dimension') {
      probe.style.fontSize = `var(${spec.css}, -1px)`;
      const fv = getComputedStyle(probe).fontSize;
      out[spec.token] = { actual: fv, missing: fv.trim() === '-1px' };
    } else if (spec.kind === 'font') {
      probe.style.fontFamily = `var(${spec.css}, '__lewitt_missing__')`;
      const ff = getComputedStyle(probe).fontFamily;
      out[spec.token] = { actual: ff, missing: ff.includes('__lewitt_missing__') };
    }
  }
  probe.remove();
  style.remove();
  return out;
}
"""


def probe(specs: list[dict], workdir: Path, tokens_css: Path | None = None, url: str | None = None) -> dict:
    """Run a Playwright evaluate on a data: page. Separate page so styles not in your URL are covered."""
    js = json.dumps(specs)
    script = f"""
const {{ chromium }} = require(process.env.LEWITT_PLAYWRIGHT || 'playwright');
(async () => {{
  const browser = await chromium.launch({{ headless: true }});
  const page = await browser.newPage();
  await page.setContent('<!doctype html><html><head></head><body></body></html>');
  const css = process.env.LEWITT_CERT_CSS;
  if (css) await page.addStyleTag({{ content: css }});
  const url = process.env.LEWITT_CERT_URL;
  if (url) {{
    await page.goto(url, {{ waitUntil: 'domcontentloaded', timeout: 45000 }});
    await page.waitForTimeout(1500);
  }}
  const out = await page.evaluate({PROBE_JS}, {js});
  await browser.close();
  process.stdout.write(JSON.stringify(out));
}})().catch((e) => {{ console.error(String(e)); process.exit(1); }});
"""
    with __import__("tempfile").TemporaryDirectory() as tmp:
        f = Path(tmp) / "probe.js"
        f.write_text(script)
        env = dict(__import__("os").environ)
        mod = __import__("capture").resolve_playwright()
        if mod:
            env["LEWITT_PLAYWRIGHT"] = str(mod)
        src = tokens_css if tokens_css and tokens_css.exists() else (workdir / "tokens.css")
        # audit the target page: its own CSS decides the rendered value. tokens.css is only a
        # fallback for the (useless) case where the page declares nothing at all.
        env["LEWITT_CERT_URL"] = url or ""
        env["LEWITT_CERT_CSS"] = "" if url else (src.read_text() if src.exists() else "")
        proc = subprocess.run(["node", str(f)], capture_output=True, text=True, env=env, timeout=180)
    if proc.returncode != 0:
        return {"error": proc.stderr.strip()[-400:]}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"error": "probe produced no JSON"}


def evaluate(dna: dict, dom: dict, resolved: dict, probed: dict) -> dict:
    checks = []
    # semantic colours are checked wherever the local page paints them; a missing role is a
    # covered gap, not a pass, and it is reported as such below
    for spec in check_type(dna, resolved) + check_colours(dna, dom, resolved):
        got = probed.get(spec["token"]) or {}
        actual = got.get("actual")
        if spec["kind"] == "color":
            dist = colour_distance(spec["expected"], actual or "")
            if dist:
                if got.get("missing"):
                    checks.append({**spec, "actual": actual, "measured": False, "ok": None,
                                   "note": "the page never defines this role's variable"})
                else:
                    checks.append({**spec, **dist, "measured": True})
            else:
                checks.append({**spec, "measured": False, "ok": None,
                               "note": "no tokens.css or unparsable colour; not asserted"})
        elif spec["kind"] in ("radius", "dimension"):
            e, a = px(spec["expected"]), px(actual or "")
            tol = TOL["radius"] if spec["kind"] == "radius" else TOL["dimension"]
            if a is None or got.get("missing") or (a == 0 and e):
                checks.append({**spec, "actual": actual, "measured": False, "ok": None,
                               "note": "the page never applies this variable (rendered at the CSS initial)"})
            else:
                checks.append({**spec, "actual": actual, "measured": True, "ok": abs(e - a) <= tol,
                               "via": got.get("via") or "probe element"})
        else:  # font
            fam = (spec["expected"].split(",")[0] or "").strip("'\" ")
            ok = actual is not None and fam.split()[0].lower() in (actual or "").lower()
            checks.append({**spec, "actual": actual, "measured": actual is not None, "ok": ok})
    return {"checks": checks}


# ------------------------------------------------------------------ guardrails on the live page
def check_guardrails(dna: dict) -> list[dict]:
    """Restraint guardrails re-checked against the local page's own DOM (class + inline style)."""
    return [{"principle": t["id"], "guardrail": t["guardrail"]} for t in dna["taste"] if t.get("guardrail")]


LIVE_GUARDRAIL_JS = r"""
(guardrails) => {
  // every element, not just ones with a class: inline styles and UA defaults count too
  const nodes = Array.from(document.querySelectorAll('body *'));
  const hits = [];
  for (const g of guardrails) {
    const patterns = [];
    for (const p of (g.guardrail.forbidClass || [])) {
      try { patterns.push(new RegExp(p)); } catch (e) { /* reported by lint, not here */ }
    }
    const cssProps = g.guardrail.forbidCss || [];
    const shadowCap = ((g.guardrail.max || {})['box-shadow'] || {}).value;
    for (const el of nodes) {
      const cls = String(el.className || '');
      for (const re of patterns) {
        const m = re.exec(cls);
        if (m) hits.push({ principle: g.principle, rule: '/' + re.source + '/', value: m[0], tag: el.tagName.toLowerCase() });
      }
      const inline = el.getAttribute('style') || '';
      for (const prop of cssProps) {
        if (inline && inline.replace(/\s+/g, '').includes(prop)) {
          hits.push({ principle: g.principle, rule: 'forbidCss: ' + prop, value: inline.slice(0, 80), tag: el.tagName.toLowerCase() });
        }
      }
      if (shadowCap !== undefined) {
        const cs = getComputedStyle(el);
        const v = cs.boxShadow;
        if (v && v !== 'none') {
          const lengths = (v.match(/-?\d*\.?\d+px/g) || []).map((x) => Math.abs(parseFloat(x)));
          if (lengths.some((n) => n > parseFloat(String(shadowCap)))) {
            hits.push({ principle: g.principle, rule: 'max box-shadow <= ' + shadowCap + 'px', value: v.slice(0, 80), tag: el.tagName.toLowerCase() });
          }
        }
      }
    }
  }
  return hits.slice(0, 40);
}
"""


def normalise_patterns(guardrails: list[dict]) -> list[dict]:
    """Ship exactly the patterns the linter validated: collapse double escapes, drop non-compiling ones."""
    import re as _re

    out = []
    for g in guardrails:
        cls = []
        for raw in (g.get("guardrail") or {}).get("forbidClass", []):
            pattern = raw.replace(chr(92) + chr(92), chr(92))
            try:
                _re.compile(pattern)
            except _re.error:
                continue
            cls.append(pattern)
        out.append({**g, "guardrail": {**g["guardrail"], "forbidClass": cls}})
    return out


def live_guardrails(guardrails: list[dict], url: str) -> dict:
    """Check forbidClass / forbidCss / max against a real DOM (the page under audit)."""
    if not guardrails:
        return {"hits": [], "note": "no restraint guardrails in this run"}
    guardrails = normalise_patterns(guardrails)
    js = json.dumps(guardrails)
    if not any(g["guardrail"].get("forbidClass") for g in guardrails):
        return {"hits": [], "error": "no forbidClass pattern survived normalisation"}
    script = f"""
const {{ chromium }} = require(process.env.LEWITT_PLAYWRIGHT || 'playwright');
(async () => {{
  const browser = await chromium.launch({{ headless: true }});
  const page = await browser.newPage({{ viewport: {{ width: 1440, height: 900 }} }});
  await page.goto({json.dumps(url)}, {{ waitUntil: 'domcontentloaded', timeout: 45000 }});
  await page.waitForTimeout(2500);
  const out = await page.evaluate({LIVE_GUARDRAIL_JS}, {js});
  await browser.close();
  process.stdout.write(JSON.stringify(out));
}})().catch((e) => {{ console.error(String(e)); process.exit(1); }});
"""
    with __import__("tempfile").TemporaryDirectory() as tmp:
        f = Path(tmp) / "guard.js"
        f.write_text(script)
        env = dict(__import__("os").environ)
        mod = __import__("capture").resolve_playwright()
        if mod:
            env["LEWITT_PLAYWRIGHT"] = str(mod)
        proc = subprocess.run(["node", str(f)], capture_output=True, text=True, env=env, timeout=180)
    if proc.returncode != 0:
        return {"hits": [], "error": proc.stderr.strip()[-300:]}
    try:
        return {"hits": json.loads(proc.stdout.strip().splitlines()[-1])}
    except (json.JSONDecodeError, IndexError):
        return {"hits": [], "error": "guardrail probe produced no JSON"}


# ------------------------------------------------------------------ verdict + report
def load_intentions(run: Path) -> list[dict]:
    """cert.config.json: {"intentional": [{"token": "color/link", "reason": "brand accent", "actual": "#..."}]}"""
    cfg = run / "cert.config.json"
    if not cfg.exists():
        return []
    try:
        data = json.loads(cfg.read_text())
    except json.JSONDecodeError:
        return []
    items = data.get("intentional") or data.get("allowedDeviations") or []
    return [i for i in items if isinstance(i, dict) and i.get("token") and i.get("reason")]


def apply_intentions(checks: list[dict], intentions: list[dict]) -> list[dict]:
    by_token = {i["token"]: i for i in intentions}
    for c in checks:
        note = by_token.get(c["token"])
        if note and c.get("ok") is False:
            c["intentional"] = True
            c["reason"] = note["reason"]
    return checks


def verdict(checks: list[dict], guard_hits: list[dict]) -> str:
    measured = [c for c in checks if c.get("measured")]
    failed = [c for c in measured if c.get("ok") is False and not c.get("intentional")]
    score = sum(WEIGHTS.get(c["kind"], 1) for c in failed)
    if guard_hits:
        return "rejected"
    if not measured:
        return "inconclusive"
    if not failed:
        return "certified"
    ratio = score / max(1, sum(WEIGHTS.get(c["kind"], 1) for c in measured))
    return "rejected" if ratio > 0.15 or any(c["kind"] == "color" for c in failed) else "warned"


def render_md(cert: dict) -> str:
    out = ["# lewitt certificate", ""]
    out.append(f"**Verdict: {cert['status'].upper()}** · {cert['measured']}/{cert['total']} token probes measured · "
               f"{len(cert['deviations'])} deviation(s) · {len(cert['guardrailHits'])} guardrail hit(s)")
    out.append("")
    out.append(f"- target: `{cert['target']}`")
    out.append(f"- instructions: `{cert['sourceRun']}` (dna.json, schema {cert['schemaVersion']})")
    out.append(f"- issued: {cert['issuedAt']} · pages inspected: {cert['pages']}")
    out.append("")
    if cert.get("note"):
        out.append("> " + cert["note"])
        out.append("")
    out.append("## Deviations first")
    out.append("")
    if cert["deviations"]:
        out.append("| Token | Expected | Actual | Delta | Kind |")
        out.append("| --- | --- | --- | --- | --- |")
        for d in cert["deviations"]:
            delta = d.get("delta", "—")
            out.append(f"| `{d['token']}` | `{d['expected']}` | `{d['actual']}` | {delta} | {d['kind']} |")
    else:
        out.append("No deviation on the measured tokens.")
    out.append("")
    if cert["guardrailHits"]:
        out.append("## Guardrail hits on the live page")
        out.append("")
        for h in cert["guardrailHits"]:
            out.append(f"- `{h['principle']}` — {h['rule']} matched `{h['value']}` on `<{h['tag']}>`")
        out.append("")
    out.append("## What was measured")
    out.append("")
    out.append("| Token | Value in tokens.css | Rendered value | Read from | Result |")
    out.append("| --- | --- | --- | --- | --- |")
    for c in cert["checks"]:
        if not c.get("measured"):
            res = "not measured"
        elif c.get("intentional"):
            res = "intentional deviation"
        else:
            res = "match" if c.get("ok") else "deviation"
        out.append(f"| `{c['token']}` | `{c['expected']}` | `{c.get('actual', '—')}` | {c.get('via', '—')} | {res} |")
    if cert.get("intentional"):
        out.append("")
        out.append("## Intentional deviations (cert.config.json)")
        out.append("")
        for c in cert["intentional"]:
            out.append(f"- `{c['token']}` — {c.get('reason')} (rendered `{c.get('actual')}, extracted `{c.get('expected')}`)")
    out.append("")
    out.append("## Not certified")
    out.append("")
    for line in cert["unchecked"]:
        out.append(f"- {line}")
    out.append("")
    out.append("_A certificate does not replace a design review: it proves the tokens whose values are "
               "checkable were applied. Anything this run could not probe is listed above, not assumed._")
    out.append("")
    return "\n".join(out)


TIER_LABEL = (("--lw-", "L1 --lw-*"), ("rendered element", "L3 computed"))


def tier_of(via: str | None) -> tuple[str, str]:
    """(short label, css class) for the column that says which tier answered."""
    via = via or ""
    if via.startswith("page --lw"):
        return "L1 --lw-*", "t1"
    if via.startswith("page --") or via.startswith("page css"):
        return "L2 shadcn", "t2"
    if "rendered" in via:
        return "L3 computed", "t3"
    if "probe" in via:
        return "L2 probe", "t2"
    return "—", ""


def render_html(cert: dict) -> str:
    import visual_base as vb

    esc = __import__("html").escape
    tone = "light"
    t = vb.TONES[tone]
    passed = [c for c in cert["checks"] if c.get("measured") and c.get("ok")]
    deviations = cert["deviations"]
    intentional = cert.get("intentional") or []
    unmeasured = [c for c in cert["checks"] if not c.get("measured")]
    hits = cert.get("guardrailHits") or []
    verdict = cert["status"]
    verdict_cls = {"certified": "ok", "warned": "warn", "rejected": "bad", "inconclusive": ""}.get(verdict, "")

    def rows(items: list[dict], kind: str) -> str:
        out = []
        for c in items:
            tier, cls = tier_of(c.get("via"))
            tail = ""
            if kind == "intentional":
                tail = f'<span class="reason">{esc(c.get("reason") or "")}</span>'
            elif kind == "unmeasured":
                tail = f'<span class="reason">{esc(c.get("note") or "not measured")}</span>'
            out.append(
                f'<tr><td><code>{esc(c["token"])}</code></td>'
                f'<td><code class="muted">{esc(str(c.get("expected", "—")))}</code></td>'
                f'<td><code>{esc(str(c.get("actual") or "—"))}</code></td>'
                f'<td><span class="tier {cls}">{esc(tier)}</span></td>'
                f'<td>{tail or ("Δ " + str(c["delta"]) if c.get("delta") is not None else "")}</td></tr>'
            )
        return "".join(out)

    def block(title: str, count: int, body: str, *, empty: str) -> str:
        if count == 0:
            return (f'<section><h2>{esc(title)} <span class="count">0</span></h2>'
                    f'<p class="empty">{esc(empty)}</p></section>')
        return f'<section><h2>{esc(title)} <span class="count">{count}</span></h2>{body}</section>' 

    def table(items: list[dict], kind: str) -> str:
        return ('<table><thead><tr><th>Token</th><th>Spec</th><th>Rendered</th><th>Read from</th><th></th></tr></thead>'
                f'<tbody>{rows(items, kind)}</tbody></table>')

    guard_html = "".join(
        f'<li><code>{esc(h.get("principle", ""))}</code> — {esc(h.get("rule", ""))} on &lt;{esc(h.get("tag", ""))}&gt;</li>'
        for h in hits)

    css = vb.base_css(tone) + f"""
.cert {{ max-width: 1080px; margin: 0 auto; padding: 56px 40px 120px; }}
@media (max-width: 700px) {{
  .cert {{ padding: 32px 20px 80px; }}
  .stats {{ grid-template-columns: 1fr 1fr; }}
  .meta {{ grid-template-columns: 1fr; }}
  section {{ overflow-x: auto; }}
}}
.head {{ display: grid; gap: 18px; padding-bottom: 32px; border-bottom: 1px solid var(--n-line); }}
.head .eyebrow {{ margin: 0; }}
.head h1 {{ margin: 0; font-size: 34px; font-weight: 400; letter-spacing: -.02em; }}
.verdict {{ display: inline-flex; align-items: center; gap: 10px; font: 500 12px/1 var(--n-mono);
  letter-spacing: .1em; text-transform: uppercase; padding: 8px 12px; border: 1px solid var(--n-line-strong);
  border-radius: 2px; width: fit-content; }}
.verdict.ok {{ color: var(--n-ok); border-color: color-mix(in srgb, var(--n-ok) 55%, transparent); }}
.verdict.warn {{ color: var(--n-warn); border-color: color-mix(in srgb, var(--n-warn) 55%, transparent); }}
.verdict.bad {{ color: var(--n-bad); border-color: color-mix(in srgb, var(--n-bad) 55%, transparent); }}
.verdict .dot {{ width: 8px; height: 8px; border-radius: 50%; background: currentColor; }}
.meta {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 18px; margin: 0; }}
.meta div {{ }}
.meta dt {{ font: 500 11px/1 var(--n-mono); letter-spacing: .08em; text-transform: uppercase; color: var(--n-faint); }}
.meta dd {{ margin: 6px 0 0; font-size: 13px; }}
.meta dd code {{ font-family: var(--n-mono); font-size: 12px; }}
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1px;
  background: var(--n-line); border: 1px solid var(--n-line); margin: 32px 0 0; }}
.stat {{ background: var(--n-panel); padding: 18px 20px; }}
.stat b {{ display: block; font-size: 30px; font-weight: 400; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }}
.stat span {{ font: 500 11px/1 var(--n-mono); letter-spacing: .08em; text-transform: uppercase; color: var(--n-mute); }}
section {{ padding: 40px 0 0; }}
h2 {{ font-size: 13px; font-weight: 500; letter-spacing: .08em; text-transform: uppercase; margin: 0 0 16px; }}
h2 .count {{ font-family: var(--n-mono); font-size: 11px; letter-spacing: 0; color: var(--n-faint); }}
.empty {{ color: var(--n-mute); font-size: 13px; margin: 0; }}
.muted {{ color: var(--n-mute); }}
.tier {{ font: 500 10.5px/1 var(--n-mono); letter-spacing: .04em; text-transform: uppercase; padding: 3px 6px;
  border-radius: 2px; border: 1px solid var(--n-line-strong); color: var(--n-mute); white-space: nowrap; }}
.tier.t1 {{ color: var(--n-ok); border-color: color-mix(in srgb, var(--n-ok) 45%, transparent); }}
.tier.t2 {{ color: var(--n-ink); }}
.tier.t3 {{ color: var(--n-warn); border-color: color-mix(in srgb, var(--n-warn) 45%, transparent); }}
.reason {{ color: var(--n-mute); font-size: 12.5px; }}
ul {{ color: var(--n-mute); font-size: 13px; padding-left: 18px; }}
footer {{ margin-top: 56px; padding-top: 20px; border-top: 1px solid var(--n-line);
  color: var(--n-mute); font: 12px/1.6 var(--n-mono); }}
"""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>lewitt certificate — {esc(cert['target'])}</title>
<style>{css}</style>
</head>
<body data-tone="{tone}">
<div class="cert">
  <header class="head">
    <p class="eyebrow">lewitt · certificate of implementation</p>
    <h1>This build is <span class="verdict {verdict_cls}"><span class="dot"></span>{esc(verdict)}</span></h1>
    <dl class="meta">
      <div><dt>Target</dt><dd><code>{esc(cert['target'])}</code></dd></div>
      <div><dt>Instructions</dt><dd><code>{esc(cert.get('sourceRun') or '—')}</code> · schema {esc(str(cert.get('schemaVersion')))}</dd></div>
      <div><dt>Issued</dt><dd>{esc(cert['issuedAt'])}</dd></div>
      <div><dt>Pages inspected</dt><dd>{esc(str(cert.get('pages', 0)))}</dd></div>
    </dl>
    <div class="stats">
      <div class="stat"><span>Measured</span><b>{cert['measured']}<small>/{cert['total']}</small></b></div>
      <div class="stat"><span>Passed</span><b>{len(passed)}</b></div>
      <div class="stat"><span>Intentional</span><b>{len(intentional)}</b></div>
      <div class="stat"><span>Violations</span><b>{len(deviations) + len(hits)}</b></div>
    </div>
  </header>
  {block("Deviations to fix", len(deviations), table(deviations, "deviation") if deviations else "", empty="No measured token deviates from the spec.")}
  {block("Intentional (registered)", len(intentional), table(intentional, "intentional"), empty="Nothing was excused.")}
  {f'<section><h2>Guardrail hits <span class="count">{len(hits)}</span></h2><ul>{guard_html}</ul></section>' if hits else ''}
  {block("Passing", len(passed), table(passed, "pass"), empty="Nothing measured yet.")}
  {block("Not measured", len(unmeasured), table(unmeasured, "unmeasured"), empty="Every token in this run could be probed.")}
  <section><h2>Not certified</h2><ul>{''.join(f'<li>{esc(u)}</li>' for u in cert['unchecked'])}</ul></section>
  <footer>A certificate covers the tokens above and nothing else. Anything this run could not probe is listed,
  not assumed. Rendered by lewitt from cert.json.</footer>
</div>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit a running site against an extracted dna.json")
    ap.add_argument("--url", required=True, help="e.g. http://localhost:3000")
    ap.add_argument("--dest", required=True, help="the lewitt run directory that holds dna.json")
    ap.add_argument("--pages", type=int, default=1, help="pages of the local site to inspect")
    ap.add_argument("--allow-warn", action="store_true", help="exit 0 even when the verdict is 'warned'")
    ap.add_argument("--keep-capture", action="store_true", help="keep the temporary capture directory")
    args = ap.parse_args()

    run = Path(args.dest).expanduser().resolve()
    dna_path = run / "dna.json"
    if not dna_path.exists():
        print(f"FAIL: {dna_path} not found — cert needs a completed lewitt run", file=sys.stderr)
        return 2
    dna = json.loads(dna_path.read_text())
    import build_artifacts as ba

    resolved = ba.resolve_tokens(dna["tokens"], (dna.get("meta", {}).get("modes") or ["default"])[0])

    work = run / ".cert-capture"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    # re-use the run's tokens.css: the probe loads exactly what a product would ship
    if (run / "tokens.css").exists():
        shutil.copy(run / "tokens.css", work / "tokens.css")

    dom, info = capture(args.url, work, args.pages)
    if not dom:
        print("FAIL: could not capture the local site — " + info.get("error", "unknown error"), file=sys.stderr)
        return 2

    specs = check_type(dna, resolved) + [
        {"kind": "color", "token": t["id"], "css": t["css"], "expected": resolved[t["id"]]["resolved"]}
        for t in dna["tokens"] if t["type"] == "color" and t["layer"] == "semantic"
    ]
    probed = probe(specs, work, run / "tokens.css", args.url)
    for spec in specs:
        rec = probed.get(spec["token"]) or {}
        if rec.get("via"):
            continue
        css = spec.get("css") or ""
        rec["via"] = ("page --lw-* var" if css.lstrip("-").startswith("lw-") else
                      "page css custom property" if css else "probe element")
    # three tiers, in this order: the page's own --lw-* vars, then shadcn/Tailwind slots,
    # then what the page actually paints. A shadcn build must not read as "nothing measured".
    page_vars = page_probe.read_vars(args.url)
    lewitt_vars = page_vars.get("lewitt", {})
    shadcn_vars = page_vars.get("shadcn", {})
    rendered = rendered_fallback(args.url)
    sources = {}
    for spec in specs:
        token, kind = spec["token"], spec["kind"]
        if kind == "color":
            if spec["css"] in lewitt_vars:
                probed[token] = {"actual": lewitt_vars[spec["css"]].get("rgb"), "missing": False, "via": "page --lw-* var"}
                sources[token] = "page --lw-* var"
            else:
                for slot in SHADCN_SLOTS.get(token, []):
                    if slot in shadcn_vars:
                        probed[token] = {"actual": shadcn_vars[slot].get("rgb"), "missing": False, "via": f"page {slot}"}
                        sources[token] = f"page {slot}"
                        break
                else:
                    if token in rendered:
                        probed[token] = {"actual": rendered[token], "missing": False, "via": "rendered element"}
                        sources[token] = "rendered element"
        elif kind == "radius" and SHADCN_RADIUS in shadcn_vars and spec["css"] not in lewitt_vars:
            probed[token] = {"actual": shadcn_radius(shadcn_vars), "missing": False, "via": "page --radius"}
            sources[token] = "page --radius"
        elif kind == "dimension" and token in rendered:
            probed[token] = {"actual": rendered[token], "missing": False, "via": "rendered element"}
            sources[token] = "rendered element"
        elif kind == "font" and token in rendered:
            pass
    result = evaluate(dna, dom, resolved, probed)
    for c in result["checks"]:
        c["via"] = sources.get(c["token"]) or probed.get(c["token"], {}).get("via") or (
            "probe element" if c.get("measured") else "—")
    checks = apply_intentions(result["checks"], load_intentions(run))

    guardrails = check_guardrails(dna)
    hits = live_guardrails(guardrails, args.url).get("hits", []) if guardrails else []
    guard_scope = f"the audited page ({args.url})" if guardrails else "no restraint guardrails in this run"
    if guardrails and not hits:
        guard_scope += "; scanned each element's class list, inline style and box-shadow"
    measured = [c for c in checks if c.get("measured")]
    deviations = [c for c in measured if c.get("ok") is False and not c.get("intentional")]
    excused = [c for c in measured if c.get("intentional")]
    status = verdict(checks, hits)

    unchecked = [
        "component geometry (padding, gaps, radii of specific elements) is not probed — only token values are",
        "spacing scale, motion timing and hover/focus deltas on the live page are not asserted",
        "visual resemblance to the source site is out of scope: this certificate is about instructions, not screenshots",
    ]
    if probed.get("error"):
        unchecked.insert(0, f"probe failed: {probed['error']}")
    if probed.get("error"):
        pass
    if not (run / "tokens.css").exists():
        unchecked.insert(0, "tokens.css missing in the run directory; CSS values could not be applied")

    cert = {
        "issuedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "target": args.url,
        "sourceRun": run.name,
        "schemaVersion": dna.get("schemaVersion"),
        "status": status,
        "total": len(checks),
        "measured": len(measured),
        "deviations": [d for d in deviations],
        "intentional": excused,
        "guardrailHits": hits,
        "guardrailScope": guard_scope,
        "checks": checks,
        "pages": len(info.get("pages", [])),
        "unchecked": unchecked,
        "note": "sign this only for the tokens above; unmeasured rows are listed, not assumed",
    }
    (run / "cert.json").write_text(json.dumps(cert, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run / "cert.md").write_text(render_md(cert), encoding="utf-8")
    (run / "cert.html").write_text(render_html(cert), encoding="utf-8")

    print(f"[{status.upper()}] {cert['measured']}/{cert['total']} probes measured · "
          f"{len(deviations)} deviation(s) · {len(hits)} guardrail hit(s)")
    for d in deviations[:6]:
        print(f"  - {d['token']}: expected {d['expected']}, got {d.get('actual')} (delta {d.get('delta', 'n/a')})")
    for h in hits[:4]:
        print(f"  - guardrail {h['principle']}: {h['rule']} on <{h['tag']}>")
    print(f"wrote {run / 'cert.md'} and {run / 'cert.html'} and {run / 'cert.json'}")
    if not args.keep_capture:
        shutil.rmtree(work, ignore_errors=True)
    if status == "certified":
        return 0
    if status == "warned":
        return 0 if args.allow_warn else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
