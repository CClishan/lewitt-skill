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
CSS_VARS_JS = r"""
() => {
  const out = {};
  for (const sheet of document.styleSheets) {
    let rules;
    try { rules = sheet.cssRules; } catch (e) { continue; }
    if (!rules) continue;
    for (const rule of rules) {
      if (!rule.style) continue;
      for (const name of rule.style) {
        if (!name.startsWith('--lw-')) continue;
        const v = rule.style.getPropertyValue(name).trim();
        if (!v) continue;
        const probe = document.createElement('span');
        probe.style.color = v;
        document.body.appendChild(probe);
        out[name] = getComputedStyle(probe).color;
        probe.remove();
      }
    }
  }
  return out;
}
"""


def target_css_colours(url: str) -> dict:
    """--lw-* custom properties the local page itself declares, resolved to rgb."""
    script = f"""
const {{ chromium }} = require(process.env.LEWITT_PLAYWRIGHT || 'playwright');
(async () => {{
  const browser = await chromium.launch({{ headless: true }});
  const page = await browser.newPage();
  await page.goto({json.dumps(url)}, {{ waitUntil: 'domcontentloaded', timeout: 45000 }});
  await page.waitForTimeout(1500);
  const out = await page.evaluate({CSS_VARS_JS});
  await browser.close();
  process.stdout.write(JSON.stringify(out));
}})().catch((e) => {{ console.error(String(e)); process.exit(1); }});
"""
    with __import__("tempfile").TemporaryDirectory() as tmp:
        f = Path(tmp) / "vars.js"
        f.write_text(script)
        env = dict(__import__("os").environ)
        mod = __import__("capture").resolve_playwright()
        if mod:
            env["LEWITT_PLAYWRIGHT"] = str(mod)
        proc = subprocess.run(["node", str(f)], capture_output=True, text=True, env=env, timeout=180)
    if proc.returncode != 0:
        return {}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {}


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
                checks.append({**spec, "actual": actual, "measured": True, "ok": abs(e - a) <= tol})
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
def verdict(checks: list[dict], guard_hits: list[dict]) -> str:
    measured = [c for c in checks if c.get("measured")]
    failed = [c for c in measured if c.get("ok") is False]
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
    out.append("| Token | Value in tokens.css | Rendered value | Result |")
    out.append("| --- | --- | --- | --- |")
    for c in cert["checks"]:
        res = "not measured" if not c.get("measured") else ("match" if c.get("ok") else "deviation")
        out.append(f"| `{c['token']}` | `{c['expected']}` | `{c.get('actual', '—')}` | {res} |")
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


def render_html(cert: dict) -> str:
    rows = "".join(
        f'<tr><td><code>{c["token"]}</code></td><td><code>{c["expected"]}</code></td>'
        f'<td><code>{c.get("actual", "—")}</code></td>'
        f'<td>{"not measured" if not c.get("measured") else ("match" if c.get("ok") else "deviation")}</td></tr>'
        for c in cert["checks"])
    devs = "".join(f'<li><code>{d["token"]}</code>: expected <code>{d["expected"]}</code>, got <code>{d["actual"]}</code></li>' for d in cert["deviations"])
    gh = "".join(f'<li><code>{h["principle"]}</code> — {h["rule"]} on &lt;{h["tag"]}&gt;</li>' for h in cert["guardrailHits"])
    colour = {"certified": "#2f9e75", "warned": "#b8912f", "rejected": "#c0392b", "inconclusive": "#6b7484"}[cert["status"]]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>lewitt certificate — {cert['target']}</title>
<style>body{{font:15px/1.6 -apple-system,Helvetica,Arial,sans-serif;max-width:920px;margin:40px auto;padding:0 20px;color:#1d2430}}
h1{{font-size:24px}}code{{font-family:ui-monospace,Menlo,monospace;font-size:12px}}
.banner{{background:{colour};color:#fff;padding:14px 18px;border-radius:10px;font-weight:600}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin:12px 0}}th,td{{text-align:left;padding:7px 9px;border-bottom:1px solid #e5edf5}}
.meta{{color:#64748d;font-size:13px}}</style></head><body>
<h1>lewitt certificate</h1>
<div class="banner">Verdict: {cert['status'].upper()} — {cert['measured']}/{cert['total']} probes measured, {len(cert['deviations'])} deviation(s)</div>
<p class="meta">target <code>{cert['target']}</code> · instructions <code>{cert['sourceRun']}</code> · issued {cert['issuedAt']}</p>
<h2>Deviations</h2><ul>{devs or '<li>none on the measured tokens</li>'}</ul>
<h2>Guardrail hits</h2><ul>{gh or '<li>none</li>'}</ul>
<h2>What was measured</h2>
<table><thead><tr><th>Token</th><th>tokens.css</th><th>Rendered</th><th>Result</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Not certified</h2><ul>{''.join(f'<li>{u}</li>' for u in cert['unchecked'])}</ul>
</body></html>
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
    page_vars = target_css_colours(args.url)
    for spec in specs:
        if spec["kind"] == "color" and spec["css"] in page_vars:
            probed.setdefault(spec["token"], {})
            probed[spec["token"]] = {"actual": page_vars[spec["css"]], "missing": False, "via": "page css custom property"}
    result = evaluate(dna, dom, resolved, probed)
    checks = result["checks"]

    guardrails = check_guardrails(dna)
    hits = live_guardrails(guardrails, args.url).get("hits", []) if guardrails else []
    guard_scope = f"the audited page ({args.url})" if guardrails else "no restraint guardrails in this run"
    if guardrails and not hits:
        guard_scope += "; scanned each element's class list, inline style and box-shadow"
    measured = [c for c in checks if c.get("measured")]
    deviations = [c for c in measured if c.get("ok") is False]
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
