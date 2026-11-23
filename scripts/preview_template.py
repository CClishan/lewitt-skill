import json

# resolve_tokens is injected by build_artifacts (single implementation of alias resolution).
resolve_tokens = None

# Neutral specimen text: the preview must not borrow copy from any earlier run.
SPECIMEN = "Aa 0123456789 The quick brown fox"

PREVIEW_CSS = """
:root{--p-bg:#0d0f13;--p-panel:#15181e;--p-line:#262b34;--p-ink:#e8eaee;--p-mute:#8b93a1;--p-accent:#e2b53f;
--p-mono:ui-monospace,SFMono-Regular,Menlo,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--p-bg);color:var(--p-ink);font:15px/1.6 -apple-system,"Helvetica Neue",Arial,sans-serif}
header{padding:32px 40px 16px;border-bottom:1px solid var(--p-line)}
h1{font-size:26px;margin:0 0 6px}
h2{font-size:19px;margin:0 0 14px;padding-bottom:10px;border-bottom:1px solid var(--p-line)}
h3{font-size:14px;margin:18px 0 8px;color:var(--p-ink)}
p,li{color:#c3c9d3}
.lede{color:var(--p-mute);max-width:78ch;margin:6px 0}
main{padding:24px 40px 96px;max-width:1240px}
section{margin-bottom:48px}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.tag{font:11px/1 var(--p-mono);padding:4px 7px;border-radius:4px;border:1px solid var(--p-line);color:var(--p-mute);text-transform:uppercase;letter-spacing:.04em}
.tag.observed{border-color:#2f9e75;color:#7fd7b4}
.tag.inferred{border-color:#b8912f;color:#e2c06a}
.tag.proposed{border-color:#6b7484;color:#aab3c2}
code,.mono{font-family:var(--p-mono);font-size:12px;color:#d7dce4}
.row{display:flex;flex-wrap:wrap;gap:16px}
.card{background:var(--p-panel);border:1px solid var(--p-line);border-radius:10px;padding:16px}
.sw{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px}
.chip{height:44px;border-radius:8px;border:1px solid rgba(255,255,255,.06);cursor:pointer;position:relative}
.chip:focus-visible{outline:2px solid var(--p-accent);outline-offset:2px}
.copy-all{display:block;padding:8px}
.copy-all:hover{background:#1b1f27}
table{width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed}
td,th{overflow-wrap:anywhere}
.mono{overflow-wrap:anywhere}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--p-line);vertical-align:top}
th{color:var(--p-mute);font-weight:500;font-size:12px}
button{font:inherit}
.btn{background:var(--p-panel);color:var(--p-ink);border:1px solid var(--p-line);border-radius:8px;padding:7px 12px;cursor:pointer}
.btn:hover{border-color:#4a5263}
.btn:focus-visible{outline:2px solid var(--p-accent);outline-offset:2px}
.status{min-height:18px;font-size:12px;color:var(--p-mute);font-family:var(--p-mono)}
.bar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;position:sticky;top:0;background:rgba(13,15,19,.94);padding:10px 0;z-index:5;border-bottom:1px solid var(--p-line)}
.shot{width:100%;border-radius:8px;border:1px solid var(--p-line);display:block}
.taste{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}
.ab{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
.ab div{border-radius:8px;padding:10px;font-size:13px}
.chose{background:#12261f;border:1px solid #2f9e75}
.over{background:#261618;border:1px solid #a3475a;text-decoration:line-through;text-decoration-color:#a3475a}
.guard{font-family:var(--p-mono);font-size:11px;color:#e2b53f;word-break:break-all;margin-top:8px}
footer{padding:24px 40px;border-top:1px solid var(--p-line);color:var(--p-mute);font-size:12px}
@media(max-width:760px){header,main,footer{padding-left:16px;padding-right:16px}main{overflow-x:clip}}
body{overflow-x:hidden}
@media(prefers-reduced-motion:reduce){*{animation-duration:.001ms!important;transition-duration:.001ms!important}}
"""

PREVIEW_JS = """
(function(){
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var status = document.getElementById('p-status');
  function say(t){ if(status) status.textContent = t; }
  // "240ms" -> 240, "0.4s" -> 400; never assume a unit
  function msFrom(d){
    var m = /^ *([0-9.]+) *(ms|s)? *$/i.exec(String(d));
    if(!m) return 300;
    return m[2] && m[2].toLowerCase() === 's' ? parseFloat(m[1]) * 1000 : parseFloat(m[1]);
  }
  function copyAll(btn, text){
    var done = function(){ say('copied ' + (text.indexOf('\\n') > -1 ? 'token set' : text)); };
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(done, function(){ say('clipboard blocked — select the text instead'); });
    } else { say('clipboard unavailable — select the text instead'); }
  }
  Array.prototype.forEach.call(document.querySelectorAll('[data-copy]'), function(el){
    el.addEventListener('click', function(){ copyAll(el, el.getAttribute('data-copy')); });
    el.addEventListener('keydown', function(e){ if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); copyAll(el, el.getAttribute('data-copy')); } });
  });
  var all = document.getElementById('copy-all');
  if(all) all.addEventListener('click', function(){
    var lines = Array.prototype.map.call(document.querySelectorAll('[data-copy]'), function(el){ return el.getAttribute('data-copy'); });
    copyAll(all, lines.join('\\n'));
  });
  // motion replay: read duration/easing from the stylesheet's custom properties
  Array.prototype.forEach.call(document.querySelectorAll('[data-replay]'), function(btn){
    var box = document.getElementById(btn.getAttribute('data-replay'));
    if(!box) return;
    var dur = btn.getAttribute('data-dur'), ease = btn.getAttribute('data-ease');
    btn.addEventListener('click', function(){
      box.style.transition = 'none';
      box.style.transform = 'none';
      box.style.opacity = '1';
      void box.offsetWidth;
      if(reduce){ say('reduced motion: replay skipped'); return; }
      box.style.transition = 'transform ' + dur + ' ' + ease + ', opacity ' + dur + ' ' + ease;
      box.style.transform = 'translateX(56px) scale(.96)';
      box.style.opacity = '0.55';
      say('replaying ' + dur + ' ' + ease);
      window.setTimeout(function(){ box.style.transform = 'none'; box.style.opacity = '1'; }, msFrom(dur) + 60);
    });
  });
})();
"""


def _esc(value) -> str:
    return (
        str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _js(value) -> str:
    return json.dumps(str(value), ensure_ascii=False).replace("</", "<\\/")


def render_preview_html(dna: dict, resolver=None, exists=None) -> str:
    """Single-file live preview. Zero external deps: styles from ./tokens.css, everything else inline."""
    meta = dna["meta"]
    modes = meta.get("modes") or ["default"]
    mode = modes[0]
    global resolve_tokens
    if resolver is not None:
        resolve_tokens = resolver
    resolved = resolve_tokens(dna["tokens"], mode)
    ev = {e["id"]: e for e in dna["evidence"]}

    def tag(status: str) -> str:
        return f'<span class="tag {status}">{status}</span>'

    # ---- swatches: semantic + component first, primitives after
    def swatch_group(layer: str, heading: str) -> str:
        toks = [t for t in dna["tokens"] if t["type"] == "color" and t["layer"] == layer]
        if not toks:
            return ""
        cells = []
        for t in toks:
            value = resolved[t["id"]]["resolved"]
            alias = next(iter(t["values"].values()))
            alias_note = f"→ {alias['alias']}" if isinstance(alias, dict) else value
            evid = ", ".join(t.get("evidence", [])) or "—"
            cells.append(
                f'<div class="card" style="padding:10px">'
                f'<div class="chip" style="background:{_esc(value)}" tabindex="0" role="button" '
                f'title="{_esc(t["id"])}" data-copy="{_esc(value)}" aria-label="copy {_esc(t["id"])} value {_esc(value)}"></div>'
                f'<div class="mono" style="margin-top:8px">{_esc(t["id"])}</div>'
                f'<div class="mono" style="color:var(--p-mute)">{_esc(alias_note)} · {_esc(evid)}</div>'
                f'<div style="margin-top:6px">{tag(t["status"])}</div></div>'
            )
        return f"<h3>{heading}</h3><div class=\"sw\">{''.join(cells)}</div>"

    colour_html = swatch_group("semantic", "Semantic roles") + swatch_group("component", "Component colours") + \
        swatch_group("primitive", "Primitives")

    # ---- type specimens
    type_cells = []
    for t in dna["tokens"]:
        if t["type"] != "dimension" or not t["id"].startswith("type/"):
            continue
        size = resolved[t["id"]]["resolved"]
        type_cells.append(
            f'<tr><td class="mono"><span data-copy="var({_esc(t["css"])})">{_esc(t["id"])}</span></td>'
            f'<td class="mono">{_esc(size)}</td>'
            f'<td><span style="font-size:{_esc(size)};line-height:1.1;display:inline-block">{_esc(SPECIMEN)}</span></td>'
            f'<td>{tag(t["status"])}</td></tr>'
        )
    weight_cells = []
    for t in dna["tokens"]:
        if t["type"] != "fontWeight":
            continue
        w = resolved[t["id"]]["resolved"]
        weight_cells.append(
            f'<tr><td class="mono"><span data-copy="var({_esc(t["css"])})">{_esc(t["id"])}</span></td>'
            f'<td class="mono">{_esc(w)}</td><td><span style="font-weight:{_esc(w)};font-size:20px">Hierarchy weight</span></td></tr>'
        )

    # ---- radius + depth
    radius_cells = []
    for t in dna["tokens"]:
        if t["type"] != "dimension" or not t["id"].startswith("radius/"):
            continue
        r = resolved[t["id"]]["resolved"]
        radius_cells.append(
            f'<div class="card" style="padding:12px"><div style="height:56px;border:1px solid #3a4150;'
            f'background:#1d222b;border-radius:{_esc(r)}"></div>'
            f'<div class="mono" style="margin-top:8px"><span data-copy="var({_esc(t["css"])})">{_esc(t["id"])}</span></div>'
            f'<div class="mono" style="color:var(--p-mute)">{_esc(r)}</div></div>'
        )
    shadow_cells = []
    for t in dna["tokens"]:
        if t["type"] != "shadow":
            continue
        sh = resolved[t["id"]]["resolved"]
        shadow_cells.append(
            f'<div class="card" style="padding:16px;background:#10131a"><div style="height:52px;background:#1b2029;'
            f'border-radius:8px;box-shadow:{_esc(sh)}"></div>'
            f'<div class="mono" style="margin-top:10px"><span data-copy="var({_esc(t["css"])})">{_esc(t["id"])}</span></div>'
            f'<div class="mono" style="color:var(--p-mute);word-break:break-all">{_esc(sh)}</div></div>'
        )

    # ---- motion replay
    durations = [t for t in dna["tokens"] if t["type"] == "duration"]
    easings = [t for t in dna["tokens"] if t["type"] == "easing"]
    denom = (durations[0]["values"].get(mode) if durations else "300ms")
    ease_default = resolved[easings[0]["id"]]["resolved"] if easings else "ease"
    slider = f'<input id="p-slow" type="range" min="1" max="4" step="0.25" value="1" aria-label="slow motion factor">'
    if isinstance(denom, dict):
        denom = "300ms"
    motion_rows = []
    for t in durations:
        dur = resolved[t["id"]]["resolved"]
        box_id = "m-" + t["id"].split("/")[-1]
        motion_rows.append(
            f'<tr><td class="mono"><span data-copy="var({_esc(t["css"])})">{_esc(t["id"])}</span></td>'
            f'<td class="mono">{_esc(dur)}</td>'
            f'<td><div id="{box_id}" style="width:120px;height:28px;border-radius:6px;background:linear-gradient(90deg,#e2b53f,#8a6d24)"></div></td>'
            f'<td><button class="btn" data-replay="{box_id}" data-dur="{_esc(dur)}" data-ease="{_esc(ease_default)}">Replay</button></td></tr>'
        )
    ease_rows = "".join(f'<li class="mono">{_esc(t["id"])} · {_esc(resolved[t["id"]]["resolved"])}</li>' for t in easings)

    # ---- taste cards
    taste_cards = []
    for t in dna["taste"]:
        guard = ""
        if t.get("guardrail"):
            guard = f'<div class="guard">{_esc(json.dumps(t["guardrail"], ensure_ascii=False))}</div>'
        taste_cards.append(
            f'<div class="card"><div class="mono" style="color:var(--p-mute)">{_esc(t["kind"])} · {_esc(", ".join(t["evidence"]))} {tag(t["status"])}</div>'
            f'<h3 style="font-size:16px">{_esc(t["name"])}</h3>'
            f'<div class="ab" aria-label="chosen versus rejected">'
            f'<div class="chose"><strong>Chose</strong><br>{_esc(t["chose"])}</div>'
            f'<div class="over"><strong>Over</strong><br>{_esc(t["over"])}</div></div>'
            f'<p style="margin:10px 0 0"><span class="mono">Why</span> {_esc(t["reason"])}</p>{guard}</div>'
        )

    # ---- source thumbnails (relative to this file)
    def has_file(name: str) -> bool:
        return True if exists is None else bool(exists(name))

    shots = []
    for name in ("viewport.png", "viewport-2.png", "viewport-3.png", "viewport-4.png"):
        if not has_file(name):
            continue
        shots.append(
            f'<figure style="margin:0"><img class="shot" src="capture/{name}" alt="source page screenshot {name}" '
            f'onerror="this.closest(\'figure\').style.display=\'none\'">'
            f'<figcaption class="mono" style="color:var(--p-mute);margin-top:6px">{name} — captured, not rebuilt</figcaption></figure>'
        )
    pages = meta.get("crawl", {}).get("pages") or [meta["source"]]
    shots_html = "".join(shots)

    token_rows = "".join(
        f'<tr><td class="mono"><span data-copy="var({_esc(t["css"])})">{_esc(t["css"])}</span></td>'
        f'<td class="mono">{_esc(t["id"])}</td><td>{_esc(t["layer"])}</td><td>{_esc(t["type"])}</td>'
        f'<td class="mono"><span data-copy="{_esc(resolved[t["id"]]["resolved"])}">{_esc(resolved[t["id"]]["resolved"])}</span></td></tr>'
        for t in dna["tokens"]
    )

    limits = "".join(f"<li>{_esc(x)}</li>" for x in meta.get("limitations", []))
    page_list = "".join(f'<li class="mono"><a href="{_esc(p)}" rel="noreferrer">{_esc(p)}</a></li>' for p in pages)
    principle = max(dna["taste"], key=lambda t: (t["kind"] == "restraint", len(t.get("evidence", []))))
    iso = "isolated" if meta.get("captureIsolated") else f"NOT isolated — {meta.get('isolationNote', 'no note')}"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>lewitt preview — {_esc(meta['name'])}</title>
<link rel="stylesheet" href="tokens.css">
<style>{PREVIEW_CSS}</style>
</head>
<body>
<header>
  <h1>{_esc(meta['name'])} — live design preview</h1>
  <p class="lede">Rendered from <code>dna.json</code> by lewitt. Colour, type and motion read the same
  <code>tokens.css</code> the rest of the system uses; every value carries its evidence id and status.</p>
  <p class="lede">Sharpest principle — <strong>{_esc(principle['name'])}</strong>: {_esc(principle['chose'])} over {_esc(principle['over'])}.</p>
  <div class="meta">
    <span class="tag">{_esc(meta['mode'])} mode</span>
    <span class="tag">{_esc(len(pages))} pages</span>
    <span class="tag">captured {_esc(str(meta.get('capturedAt', 'unknown'))[:19])}</span>
    <span class="tag">{_esc(iso)}</span>
    <span class="tag">{_esc(len(dna['tokens']))} tokens</span>
  </div>
</header>
<main>
  <div class="bar" role="toolbar" aria-label="Handoff">
    <button class="btn" id="copy-all">Copy all token values</button>
    <a class="btn" href="tokens.css" download>tokens.css</a>
    <a class="btn" href="tokens.resolved.json" download>tokens.resolved.json</a>
    <a class="btn" href="agent-rules.md" download>agent-rules.md</a>
    <a class="btn" href="taste.md" download>taste.md</a>
    <span class="status" id="p-status" aria-live="polite"></span>
  </div>

  <section aria-labelledby="s-color">
    <h2 id="s-color">Colour — live swatches</h2>
    <p>Click any swatch to copy its value; roles are listed before raw primitives.</p>
    {colour_html}
  </section>

  <section aria-labelledby="s-type">
    <h2 id="s-type">Typography — real sizes and weights</h2>
    <table><thead><tr><th>Token</th><th>Value</th><th>Specimen</th><th>Status</th></tr></thead><tbody>{''.join(type_cells)}</tbody></table>
    <h3>Weights</h3>
    <table><thead><tr><th>Token</th><th>Value</th><th>Specimen</th></tr></thead><tbody>{''.join(weight_cells)}</tbody></table>
  </section>

  <section aria-labelledby="s-shape">
    <h2 id="s-shape">Radius &amp; depth</h2>
    <div class="sw">{''.join(radius_cells)}</div>
    <h3>Shadows</h3>
    <div class="sw">{''.join(shadow_cells) or '<p class="lede">No shadow tokens: this system separates layers with borders.</p>'}</div>
  </section>

  <section aria-labelledby="s-motion">
    <h2 id="s-motion">Motion replay</h2>
    <p>Each row replays the actual duration token with the system's easing. Reduced motion is respected.</p>
    <table><thead><tr><th>Duration</th><th>Value</th><th>Specimen</th><th></th></tr></thead><tbody>{''.join(motion_rows)}</tbody></table>
    <h3>Easings observed</h3><ul>{ease_rows}</ul>
  </section>

  <section aria-labelledby="s-taste">
    <h2 id="s-taste">Taste DNA</h2>
    <div class="taste">{''.join(taste_cards)}</div>
  </section>

  <section aria-labelledby="s-source">
    <h2 id="s-source">Source record</h2>
    <p class="lede">Screenshots below are the captured source pages, shown for comparison — they are not rebuilt by lewitt.</p>
    <div class="sw" style="grid-template-columns:repeat(auto-fill,minmax(320px,1fr))">{shots_html}</div>
    <h3>Pages inspected</h3><ul>{page_list}</ul>
    <h3>Limitations</h3><ul>{limits}</ul>
  </section>

  <section aria-labelledby="s-tokens">
    <h2 id="s-tokens">Every token</h2>
    <table><thead><tr><th>CSS var</th><th>Token</th><th>Layer</th><th>Type</th><th>Value</th></tr></thead><tbody>{token_rows}</tbody></table>
  </section>
</main>
<footer>Generated by lewitt from dna.json — do not edit by hand. Re-render with <code>build_artifacts.py</code>.</footer>
<script>{PREVIEW_JS}</script>
</body>
</html>
"""

