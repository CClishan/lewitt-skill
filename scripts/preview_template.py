import json

# resolve_tokens is injected by build_artifacts (single implementation of alias resolution).
resolve_tokens = None

# Neutral specimen text: the preview must not borrow copy from any earlier run.
SPECIMEN = "Aa 0123456789 The quick brown fox"

PREVIEW_CSS = """
/* preview.html — Architectural Specimen Book. Neutrals come from visual_base; the system's own
   colour only appears inside a Stage. */
header.top{padding:56px 56px 28px;border-bottom:1px solid var(--n-line)}
.top .eyebrow{margin-bottom:14px}
.top h1{font-size:34px;line-height:1.1;letter-spacing:-.02em;margin:0 0 12px;font-weight:400;max-width:24ch}
.top .lede{color:var(--n-mute);max-width:70ch;margin:0 0 6px;font-size:14px}
.top .meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:18px}
main{padding:0 56px 120px;max-width:1180px}
.bar{position:sticky;top:0;z-index:20;display:flex;flex-wrap:wrap;gap:8px;align-items:center;
  padding:12px 0;margin:0 0 8px;background:var(--n-bg);border-bottom:1px solid var(--n-line)}
.bar .grow{flex:1}
section{padding:56px 0;border-bottom:1px solid var(--n-line)}
section:last-of-type{border-bottom:0}
h2{font-size:13px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:var(--n-ink);
  margin:0 0 6px;display:flex;align-items:baseline;gap:12px}
h2 .count{color:var(--n-faint);font-family:var(--n-mono);letter-spacing:0;font-size:11px}
.sect-note{color:var(--n-mute);font-size:13px;margin:0 0 28px;max-width:72ch}
h3{font-size:12px;font-weight:500;margin:32px 0 12px;color:var(--n-mute);letter-spacing:.05em;text-transform:uppercase}

/* ---- colour: 96px chips, two lines underneath, WCAG badges on real pairs */
.sw{display:grid;grid-template-columns:repeat(auto-fill,minmax(196px,1fr));gap:1px;background:var(--n-line);
  border:1px solid var(--n-line);border-right:0;border-bottom:0}
.sw .swatch{border-right:1px solid var(--n-line);border-bottom:1px solid var(--n-line)}
.swatch{background:var(--n-panel);padding:0 0 12px;cursor:copy}
.swatch .fill{height:96px;border-bottom:1px solid var(--n-line)}
.swatch .fill.checker{background-image:linear-gradient(45deg,var(--n-hover) 25%,transparent 25%,transparent 75%,var(--n-hover) 75%),linear-gradient(45deg,var(--n-hover) 25%,transparent 25%,transparent 75%,var(--n-hover) 75%);background-size:10px 10px;background-position:0 0,5px 5px}
.swatch .line{padding:10px 12px 0;display:flex;align-items:baseline;justify-content:space-between;gap:8px}
.swatch .tok{font:12px/1.3 var(--n-mono);color:var(--n-ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.swatch .hex{font:11px/1.3 var(--n-mono);color:var(--n-mute);font-variant-numeric:tabular-nums}
.swatch .sub{padding:2px 12px 0;display:flex;align-items:center;justify-content:space-between;gap:8px}
.pairs{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1px;background:var(--n-line);border:1px solid var(--n-line)}
.pair{background:var(--n-panel);padding:18px 20px}
.pair .sample{padding:14px 16px;border-radius:2px;font-size:14px}
.pair .pmeta{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:12px}
.pair .pmeta .mono{color:var(--n-mute);font-size:11px}

/* ---- typography: parameters left, specimen right */
.type-row{display:grid;grid-template-columns:220px minmax(0,1fr);gap:0;border-top:1px solid var(--n-line)}
.type-row:last-child{border-bottom:1px solid var(--n-line)}
.type-params{padding:20px 24px 20px 0;border-right:1px solid var(--n-line)}
.type-params dl{margin:0;display:grid;grid-template-columns:auto 1fr;gap:3px 14px;font:11.5px/1.5 var(--n-mono)}
.type-params dt{color:var(--n-faint)}
.type-params dd{margin:0;color:var(--n-ink);text-align:right}
.type-params .tok{font:12px/1.4 var(--n-mono);color:var(--n-ink);display:block;margin-bottom:8px}
.type-specimen{padding:20px 0 20px 32px;overflow:hidden;color:var(--n-ink)}
.type-specimen .spec{white-space:nowrap;text-overflow:ellipsis;overflow:hidden;display:block}
.type-specimen .wide{white-space:normal}
.wspec{display:flex;align-items:baseline;gap:18px;padding:14px 0 14px 32px}
.wspec b{font-size:28px;font-weight:inherit}

/* ---- shape */
.grid-2{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:1px;background:var(--n-line);border:1px solid var(--n-line)}
.shape{background:var(--n-panel);padding:20px}
.shape .obj{height:72px;background:var(--n-hover);border:1px solid var(--n-line-strong)}
.shape .cap{display:flex;justify-content:space-between;align-items:baseline;margin-top:12px;gap:8px}

/* ---- motion: easing plot + duration + replay */
.motion{display:grid;grid-template-columns:196px minmax(0,1fr) 120px;gap:0;border-top:1px solid var(--n-line);align-items:center}
.motion:last-child{border-bottom:1px solid var(--n-line)}
.motion .plot{padding:16px 24px 16px 0;border-right:1px solid var(--n-line);display:flex;align-items:center}
.motion .mid{padding:16px 24px}
.motion .mid .tok{font:12px/1.4 var(--n-mono)}
.motion .mid .ease{color:var(--n-mute);font:11px/1.5 var(--n-mono);margin-top:4px;word-break:break-all}
.motion .act{padding:16px 0;text-align:right}
.track{height:2px;background:var(--n-line-strong);margin-top:14px;position:relative}
.track .dot{position:absolute;top:-5px;left:0;width:12px;height:12px;border-radius:50%;background:var(--n-ink)}

/* ---- taste: structured cards, machine rule folded away */
.taste{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:1px;background:var(--n-line);border:1px solid var(--n-line)}
.tcard{background:var(--n-panel);padding:24px 24px 20px;display:flex;flex-direction:column;gap:12px}
.tcard .head{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.tcard h4{margin:0;font-size:15px;font-weight:500;letter-spacing:-.005em}
.tcard .ab{display:grid;grid-template-columns:1fr 22px 1fr;gap:10px;align-items:center;font-size:13px}
.tcard .ab .v{padding:10px 12px;border:1px solid var(--n-line-strong);border-radius:2px;background:var(--n-bg)}
.tcard .ab .over{color:var(--n-mute);text-decoration:line-through;text-decoration-color:var(--n-line-strong)}
.tcard .ab .vs{text-align:center;color:var(--n-faint);font:11px/1 var(--n-mono)}
.tcard .why{margin:0;font-size:13px;color:var(--n-mute)}
.rules{display:flex;flex-wrap:wrap;gap:6px;margin:0;padding:0;list-style:none}
.rule{font:500 10.5px/1 var(--n-mono);letter-spacing:.06em;text-transform:uppercase;padding:4px 7px;
  border-radius:2px;border:1px solid var(--n-line-strong);color:var(--n-mute)}
.rule.forbid{color:var(--n-bad);border-color:color-mix(in srgb,var(--n-bad) 45%,transparent)}
.rule.max{color:var(--n-warn);border-color:color-mix(in srgb,var(--n-warn) 45%,transparent)}
.rule.require{color:var(--n-ok);border-color:color-mix(in srgb,var(--n-ok) 45%,transparent)}

/* ---- source record: split compare */
.compare{position:relative;border:1px solid var(--n-line);overflow:hidden;background:var(--n-panel);touch-action:none}
.compare .layer{display:block;width:100%}
.compare .layer.b{position:absolute;inset:0;clip-path:inset(0 50% 0 0)}
.compare .layer.b img{width:100%;display:block}
.compare img{display:block;width:100%}
.compare .handle{position:absolute;top:0;bottom:0;left:50%;width:1px;background:var(--n-ink);pointer-events:none}
.compare .handle::after{content:'';position:absolute;top:50%;left:50%;width:28px;height:28px;margin:-14px 0 0 -14px;
  border-radius:50%;border:1px solid var(--n-ink);background:var(--n-bg)}
.compare input[type=range]{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:ew-resize;margin:0}
.compare .lab{position:absolute;bottom:10px;font:10.5px/1 var(--n-mono);letter-spacing:.06em;text-transform:uppercase;
  background:var(--n-bg);color:var(--n-mute);padding:5px 7px;border:1px solid var(--n-line-strong)}
.compare .lab.l{left:10px} .compare .lab.r{right:10px}
.sbs{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--n-line);border:1px solid var(--n-line)}
.sbs figure{margin:0;background:var(--n-panel);padding:12px}
.sbs img{width:100%;display:block;border:1px solid var(--n-line)}
.sbs figcaption{font:11px/1.4 var(--n-mono);color:var(--n-mute);margin-top:8px}
.shots{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:20px;margin-top:20px}
.shots figure{margin:0}
.shots img{width:100%;border:1px solid var(--n-line);display:block}
.shots figcaption{font:11px/1.4 var(--n-mono);color:var(--n-mute);margin-top:6px}
ul.plain{margin:0;padding-left:18px;color:var(--n-mute);font-size:13px}
ul.plain li{margin:4px 0}
footer{padding:32px 56px 64px;color:var(--n-mute);font-size:12px;font-family:var(--n-mono)}
@media(max-width:900px){
  header.top,main,footer{padding-left:20px;padding-right:20px}
  main{padding-bottom:80px}
  .type-row{grid-template-columns:1fr}
  .type-params{border-right:0;padding-right:0;border-bottom:1px solid var(--n-line)}
  .type-specimen{padding-left:0}
  .motion{grid-template-columns:1fr}
  .motion .plot{border-right:0}
  .sbs{grid-template-columns:1fr}
}
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
  // slow-motion factor shared by every replay control (0.25x .. 4x)
  var slow = 1;
  var slowEl = document.getElementById('p-slow');
  if(slowEl) slowEl.addEventListener('input', function(){ slow = parseFloat(slowEl.value) || 1; say('replay speed ' + slow + 'x'); });

  Array.prototype.forEach.call(document.querySelectorAll('[data-replay]'), function(btn){
    var dot = document.getElementById(btn.getAttribute('data-replay'));
    if(!dot) return;
    var dur = btn.getAttribute('data-dur'), ease = btn.getAttribute('data-ease');
    btn.addEventListener('click', function(){
      dot.style.transition = 'none'; dot.style.transform = 'translateX(0)'; void dot.offsetWidth;
      if(reduce){ say('reduced motion: replay skipped'); return; }
      var ms = msFrom(dur) * slow;
      dot.style.transition = 'transform ' + ms + 'ms ' + ease;
      dot.style.transform = 'translateX(calc(100% - 12px))';
      say('replaying ' + dur + ' at ' + slow + 'x');
      window.setTimeout(function(){ dot.style.transition = 'transform ' + ms + 'ms ' + ease; dot.style.transform = 'translateX(0)'; }, ms + 120);
    });
    btn.addEventListener('mouseenter', function(){ if(!reduce) dot.style.transition = 'transform ' + (msFrom(dur) * slow) + 'ms ' + ease; });
  });

  // fidelity: split compare by default, side-by-side on request
  var cmp = document.getElementById('p-compare');
  var sbs = document.getElementById('p-sbs');
  var toggle = document.getElementById('p-view-toggle');
  if(toggle && cmp && sbs){
    toggle.addEventListener('click', function(){
      var split = toggle.getAttribute('aria-pressed') === 'true';
      toggle.setAttribute('aria-pressed', split ? 'false' : 'true');
      toggle.textContent = split ? 'Side by side' : 'Split compare';
      cmp.hidden = split ? true : false;
      sbs.hidden = split ? false : true;
    });
  }
  var range = document.getElementById('p-split');
  if(range && cmp){
    var apply = function(){ cmp.style.setProperty('--split', range.value + '%');
      var b = cmp.querySelector('.layer.b'); if(b) b.style.clipPath = 'inset(0 ' + (100 - range.value) + '% 0 0)';
      var h = cmp.querySelector('.handle'); if(h) h.style.left = range.value + '%'; };
    range.addEventListener('input', apply); apply();
  }
  document.addEventListener('keydown', function(e){
    if(!range || (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight')) return;
    var step = e.shiftKey ? 10 : 2;
    range.value = Math.max(0, Math.min(100, parseFloat(range.value) + (e.key === 'ArrowRight' ? step : -step)));
    range.dispatchEvent(new Event('input'));
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
    """Single-file specimen book. Zero external deps: styles from ./tokens.css, everything else inline."""
    meta = dna["meta"]
    modes = meta.get("modes") or ["default"]
    mode = modes[0]
    global resolve_tokens
    if resolver is not None:
        resolve_tokens = resolver
    import visual_base as vb

    resolved = resolve_tokens(dna["tokens"], mode)
    ev = {e["id"]: e for e in dna["evidence"]}
    canvas = next((resolved[t["id"]]["resolved"] for t in dna["tokens"] if t["id"] == "color/canvas"), None)
    tone = vb.tone_of(canvas)

    def chip(status: str) -> str:
        cls = {"observed": "ok", "inferred": "warn", "proposed": "", "unknown": "bad"}.get(status, "")
        return f'<span class="chip {cls}">{_esc(status)}</span>'

    # ---- colour: 96px fill, token + hex, then a quieter sub-line
    def swatch_group(layer: str, heading: str) -> str:
        toks = [t for t in dna["tokens"] if t["type"] == "color" and t["layer"] == layer]
        if not toks:
            return ""
        cells = []
        for t in toks:
            value = resolved[t["id"]]["resolved"]
            alias = next(iter(t["values"].values()))
            alias_note = alias["alias"] if isinstance(alias, dict) else ""
            transparent = str(value).replace(" ", "") in ("rgba(0,0,0,0)", "transparent")
            cells.append(
                '<div class="swatch" data-copy="' + _esc(value) + '" tabindex="0" role="button" '
                'aria-label="copy ' + _esc(t["id"]) + ' value ' + _esc(value) + '">'
                f'<div class="fill{" checker" if transparent else ""}" style="background:{_esc(value)}"></div>'
                f'<div class="line"><span class="tok">{_esc(t["id"])}</span>'
                f'<span class="hex">{_esc(value)}</span></div>'
                f'<div class="sub"><span class="mono" style="color:var(--n-faint)">{_esc(alias_note or " ")}</span>'
                f'{chip(t["status"])}</div></div>'
            )
        return (f'<h3>{heading} <span class="count" style="font-family:var(--n-mono);font-size:11px;'
                f'color:var(--n-faint);text-transform:none;letter-spacing:0">· {len(toks)}</span></h3>'
                f'<div class="sw">{"" .join(cells)}</div>')

    colour_html = (swatch_group("semantic", "Semantic roles")
                   + swatch_group("component", "Component colours")
                   + swatch_group("primitive", "Primitives"))

    # real pairs used on the source page, with the contrast ratio measured from the token values
    pairs = [
        ("heading / canvas", "color/text/heading", "color/canvas", "display copy"),
        ("body / canvas", "color/text/body", "color/canvas", "paragraphs"),
        ("body / subtle", "color/text/body", "color/surface-subtle", "cards, raised rows"),
        ("action-fg / action-bg", "color/action/fg", "color/action/bg", "primary button"),
        ("link / canvas", "color/link", "color/canvas", "inline links"),
    ]
    pair_cells = []
    for label, fg_id, bg_id, where in pairs:
        fg = resolved.get(fg_id, {}).get("resolved")
        bg = resolved.get(bg_id, {}).get("resolved")
        if not fg or not bg:
            continue
        badge, grade = vb.wcag_badge(fg, bg)
        pair_cells.append(
            f'<div class="pair"><div class="sample" style="background:{_esc(bg)};color:{_esc(fg)}">{_esc(label)}</div>'
            f'<div class="pmeta"><span class="mono">{_esc(where)}</span>'
            f'<span class="chip {grade}">{_esc(badge)}</span></div></div>'
        )
    pairs_html = "".join(pair_cells)

    # ---- typography: parameters on the left, specimen on the right, one row per token
    def type_row(t: dict) -> str:
        size = resolved[t["id"]]["resolved"]
        tracking = next((resolved[x["id"]]["resolved"] for x in dna["tokens"]
                         if x["id"].startswith("tracking/")), None)
        params = [("size", size), ("colour", "var(--n-ink)")]
        if tracking:
            params.append(("tracking", tracking))
        dl = "".join(f"<dt>{_esc(k)}</dt><dd>{_esc(v)}</dd>" for k, v in params)
        long_text = float(str(size).replace("px", "") or 16) <= 20
        spec_cls = "spec wide" if long_text else "spec"
        return (
            f'<div class="type-row"><div class="type-params">'
            f'<span class="tok" data-copy="var({_esc(t["css"])})">{_esc(t["id"])}</span>'
            f'<dl>{dl}</dl></div>'
            f'<div class="type-specimen"><span class="{spec_cls}" style="font-size:{_esc(size)};'
            f'line-height:1.12">{_esc(SPECIMEN)}</span></div></div>'
        )

    type_rows = "".join(type_row(t) for t in dna["tokens"]
                        if t["type"] == "dimension" and t["id"].startswith("type/"))
    weight_rows = ""
    for t in dna["tokens"]:
        if t["type"] != "fontWeight":
            continue
        w = resolved[t["id"]]["resolved"]
        weight_rows += (
            f'<div class="type-row"><div class="type-params">'
            f'<span class="tok" data-copy="var({_esc(t["css"])})">{_esc(t["id"])}</span>'
            f'<dl><dt>weight</dt><dd>{_esc(w)}</dd></dl></div>'
            f'<div class="wspec" style="font-weight:{_esc(w)}"><b>{_esc(SPECIMEN)}</b></div></div>'
        )

    # ---- radius + depth
    radius_cells = []
    for t in dna["tokens"]:
        if t["type"] != "dimension" or not t["id"].startswith("radius/"):
            continue
        r = resolved[t["id"]]["resolved"]
        radius_cells.append(
            f'<div class="shape"><div class="obj" style="border-radius:{_esc(r)}"></div>'
            f'<div class="cap"><span class="mono" data-copy="var({_esc(t["css"])})">{_esc(t["id"])}</span>'
            f'<span class="mono" style="color:var(--n-mute)">{_esc(r)}</span></div></div>'
        )
    shadow_cells = []
    for t in dna["tokens"]:
        if t["type"] != "shadow":
            continue
        sh = resolved[t["id"]]["resolved"]
        shadow_cells.append(
            f'<div class="shape"><div class="obj" style="box-shadow:{_esc(sh)};border-color:transparent"></div>'
            f'<div class="cap"><span class="mono" data-copy="var({_esc(t["css"])})">{_esc(t["id"])}</span>'
            f'<span class="mono" style="color:var(--n-mute);text-align:right;word-break:break-all">{_esc(sh)}</span></div></div>'
        )

    # ---- motion: a deterministic easing plot per duration, plus a real replay dot
    durations = [t for t in dna["tokens"] if t["type"] == "duration"]
    easings = [t for t in dna["tokens"] if t["type"] == "easing"]
    ease_default = resolved[easings[0]["id"]]["resolved"] if easings else "ease"
    motion_rows = []
    ease_list = []
    easing_specs = [resolved[e["id"]]["resolved"] for e in easings] or [ease_default]

    def easing_for(token_id: str) -> str:
        # pick by name so a "reveal" tier plots a different curve from a "fast" one
        key = token_id.lower()
        for e in easings:
            tail = e["id"].split("/")[-1].lower()
            if tail and tail in key:
                return resolved[e["id"]]["resolved"]
        if "reveal" in key or "enter" in key:
            return max(easing_specs, key=lambda spec: abs((vb.cubic_points(spec) or (0, 0, 0.5, 1))[2] - 0.5))
        return easing_specs[0]

    for t in durations:
        dur = resolved[t["id"]]["resolved"]
        ease_here = easing_for(t["id"])
        dot_id = "dot-" + t["id"].split("/")[-1]
        plot = vb.bezier_svg(ease_here)
        motion_rows.append(
            f'<div class="motion"><div class="plot">{plot}</div>'
            f'<div class="mid"><div class="tok" data-copy="var({_esc(t["css"])})">{_esc(t["id"])} · {_esc(dur)}</div>'
            f'<div class="ease">{_esc(ease_here)}</div>'
            f'<div class="track"><span class="dot" id="{dot_id}"></span></div></div>'
            f'<div class="act"><button class="mini-btn" data-replay="{dot_id}" data-dur="{_esc(dur)}" '
            f'data-ease="{_esc(ease_here)}">Replay</button></div></div>'
        )
    for t in easings:
        bottom = t["values"].get(mode) if isinstance(t["values"].get(mode), dict) else None
        spec = resolved[t["id"]]["resolved"]
        ease_list.append(
            f'<div class="motion"><div class="plot">{vb.bezier_svg(spec)}</div>'
            f'<div class="mid"><div class="tok" data-copy="var({_esc(t["css"])})">{_esc(t["id"])}</div>'
            f'<div class="ease">{_esc(spec)}</div></div>'
            f'<div class="act"><span class="chip">{_esc(t["status"])}</span></div></div>'
        )

    # ---- taste: rule capsules derived from the guardrail, machine rule folded into <details>
    def rule_capsules(guard: dict) -> str:
        caps = []
        for prop in guard.get("forbidCss") or []:
            caps.append(f'<li class="rule forbid">forbid · {_esc(prop)}</li>')
        if guard.get("forbidClass"):
            caps.append(f'<li class="rule forbid">forbid · {len(guard["forbidClass"])} class pattern(s)</li>')
        for prop, bound in (guard.get("max") or {}).items():
            caps.append(f'<li class="rule max">max · {_esc(prop)} ≤ {_esc(bound.get("value"))}{_esc(bound.get("unit", ""))}</li>')
        for prop in guard.get("require") or []:
            caps.append(f'<li class="rule require">require · {_esc(prop)}</li>')
        return f'<ul class="rules">{"".join(caps)}</ul>' if caps else ""

    taste_cards = []
    for t in dna["taste"]:
        guard = t.get("guardrail") or {}
        machine = ""
        if guard:
            machine = (f'<details><summary>Machine rule</summary>'
                       f'<pre>{_esc(json.dumps(guard, indent=1, ensure_ascii=False))}</pre></details>')
        taste_cards.append(
            f'<article class="tcard"><div class="head">{chip(t["status"])}'
            f'<span class="mono" style="color:var(--n-faint)">{_esc(t["kind"])} · {_esc(", ".join(t["evidence"]))}</span></div>'
            f'<h4>{_esc(t["name"])}</h4>'
            f'<div class="ab"><div class="v">{_esc(t["chose"])}</div><div class="vs">over</div>'
            f'<div class="v over">{_esc(t["over"])}</div></div>'
            f'<p class="why">{_esc(t["reason"])}</p>{rule_capsules(guard)}{machine}</article>'
        )

    # ---- source record
    def has_file(name: str) -> bool:
        return True if exists is None else bool(exists(name))

    shots = [n for n in ("viewport.png", "viewport-2.png", "viewport-3.png", "viewport-4.png") if has_file(n)]
    hero = shots[0] if shots else None
    compare_html = ""
    if hero:
        compare_html = (
            '<div class="compare" id="p-compare"><img class="layer a" src="capture/' + _esc(hero) + '" alt="captured source page">'
            '<div class="layer b"><img src="capture/' + _esc(hero) + '" alt=""></div>'
            '<div class="handle"></div>'
            '<span class="lab l">source · capture/' + _esc(hero) + '</span>'
            '<span class="lab r">split compare</span>'
            '<input id="p-split" type="range" min="0" max="100" value="50" '
            'aria-label="compare source and rebuild, drag or use arrow keys"></div>'
        )
    sbs_html = ""
    if hero:
        sbs_html = (
            '<div class="sbs" id="p-sbs" hidden>'
            f'<figure><img src="capture/{_esc(hero)}" alt="captured source page"><figcaption>source · capture/{_esc(hero)}</figcaption></figure>'
            '<figure><div class="stage" style="border:0"><div class="stage-body tight" style="min-height:180px">'
            '<p class="sect-note" style="margin:0">Rebuilt surfaces read <code>tokens.css</code>; open '
            '<code>system/index.html</code> (full mode) for the live rebuild.</p></div></div>'
            '<figcaption>rebuild · this file</figcaption></figure></div>'
        )
    other_shots = "".join(
        f'<figure><img src="capture/{_esc(n)}" alt="source page screenshot {_esc(n)}" loading="lazy">'
        f'<figcaption>{_esc(n)}</figcaption></figure>' for n in shots[1:]
    )
    pages = meta.get("crawl", {}).get("pages") or [meta["source"]]
    token_rows = "".join(
        f'<tr><td><code data-copy="var({_esc(t["css"])})">{_esc(t["css"])}</code></td>'
        f'<td><code>{_esc(t["id"])}</code></td><td>{_esc(t["layer"])}</td><td>{_esc(t["type"])}</td>'
        f'<td><code data-copy="{_esc(resolved[t["id"]]["resolved"])}">{_esc(resolved[t["id"]]["resolved"])}</code></td>'
        f'<td>{chip(t["status"])}</td></tr>'
        for t in dna["tokens"]
    )
    limits = "".join(f"<li>{_esc(x)}</li>" for x in meta.get("limitations", []))
    page_list = "".join(f'<li><a href="{_esc(p)}" rel="noreferrer">{_esc(p)}</a></li>' for p in pages)
    principle = max(dna["taste"], key=lambda t: (t["kind"] == "restraint", len(t.get("evidence", []))))
    iso = "isolated browser" if meta.get("captureIsolated") else "not isolated"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>lewitt specimen — {_esc(meta['name'])}</title>
<link rel="stylesheet" href="tokens.css">
<style>{vb.base_css(tone)}{PREVIEW_CSS}</style>
</head>
<body data-tone="{tone}">
<header class="top">
  <p class="eyebrow">lewitt · design specimen · {_esc(meta['mode'])} mode</p>
  <h1>{_esc(meta['name'])}</h1>
  <p class="lede">{_esc(principle['name'])}: {_esc(principle['chose'])}, not {_esc(principle['over'])}.</p>
  <p class="lede">Every value below is a render of <code>dna.json</code> reading the same <code>tokens.css</code>
  a build would import. Click any swatch, token name or value to copy it.</p>
  <div class="meta">
    <span class="chip">{_esc(len(pages))} pages</span>
    <span class="chip">{_esc(len(dna['tokens']))} tokens</span>
    <span class="chip">{_esc(len(dna['evidence']))} evidence</span>
    <span class="chip">captured {_esc(str(meta.get('capturedAt', 'unknown'))[:10])}</span>
    <span class="chip">{_esc(iso)}</span>
  </div>
</header>
<main>
  <div class="bar" role="toolbar" aria-label="Handoff">
    <button class="mini-btn" id="copy-all" data-copy="{_esc(chr(10).join(resolved[t['id']]['resolved'] for t in dna['tokens']))}">Copy all values</button>
    <a class="mini-btn" href="tokens.css" download>tokens.css</a>
    <a class="mini-btn" href="shadcn-theme.css" download>shadcn-theme.css</a>
    <a class="mini-btn" href="agent-rules.md" download>agent-rules.md</a>
    <a class="mini-btn" href="taste.md" download>taste.md</a>
    <span class="grow"></span>
    <label class="mono" for="p-slow" style="color:var(--n-mute)">replay</label>
    <input id="p-slow" type="range" min="0.25" max="4" step="0.25" value="1" aria-label="slow motion factor" style="width:96px">
    <span class="mono" id="p-status" aria-live="polite" style="color:var(--n-mute)"></span>
  </div>

  <section aria-labelledby="s-color">
    <h2 id="s-color">Colour <span class="count">{_esc(len([t for t in dna['tokens'] if t['type'] == 'color']))}</span></h2>
    <p class="sect-note">Roles first, primitives after. Each block is the token's resolved value; the ratio
    beside a real pair is measured from those two values, not estimated from the screenshot.</p>
    {colour_html}
    <h3>Pairs in use</h3>
    <div class="pairs">{pairs_html}</div>
  </section>

  <section aria-labelledby="s-type">
    <h2 id="s-type">Typography</h2>
    <p class="sect-note">Parameters on the left, the specimen on the right at its real size. Web fonts are not
    shipped: the specimen uses the declared stack and falls back where the face is missing.</p>
    {type_rows}
    {weight_rows}
  </section>

  <section aria-labelledby="s-shape">
    <h2 id="s-shape">Radius &amp; depth</h2>
    <div class="grid-2">{''.join(radius_cells)}{''.join(shadow_cells) or '<div class="shape"><div class="cap"><span class="mono">no shadow tokens</span><span class="mono" style="color:var(--n-mute)">this system separates layers with borders</span></div></div>'}</div>
  </section>

  <section aria-labelledby="s-motion">
    <h2 id="s-motion">Motion</h2>
    <p class="sect-note">Each curve is plotted from the token's own cubic-bezier, with its control handles.
    Replay runs the real duration on the track; the slider above slows every replay.</p>
    {''.join(motion_rows)}
    {''.join(ease_list)}
  </section>

  <section aria-labelledby="s-taste">
    <h2 id="s-taste">Taste &amp; guardrails</h2>
    <p class="sect-note">The decision in words, the rule it compiles to, and the machine pattern behind it.
    A build that violates a capsule fails <code>lint_output.py</code>.</p>
    <div class="taste">{''.join(taste_cards)}</div>
  </section>

  <section aria-labelledby="s-source">
    <h2 id="s-source">Source record</h2>
    <p class="sect-note">The screenshots are the captured source pages, kept for comparison: they are not rebuilt by lewitt.</p>
    <div style="display:flex;justify-content:flex-end;margin-bottom:12px">
      <button class="mini-btn" id="p-view-toggle" aria-pressed="true">Side by side</button>
    </div>
    {compare_html}
    {sbs_html}
    <div class="shots">{other_shots}</div>
    <h3>Pages inspected</h3><ul class="plain">{page_list}</ul>
    <h3>Limitations</h3><ul class="plain">{limits}</ul>
  </section>

  <section aria-labelledby="s-tokens">
    <h2 id="s-tokens">Every token</h2>
    <div class="tbl"><table><thead><tr><th>CSS var</th><th>Token</th><th>Layer</th><th>Type</th><th>Value</th><th>Status</th></tr></thead>
    <tbody>{token_rows}</tbody></table></div>
  </section>
</main>
<footer>Rendered by lewitt from dna.json — do not edit by hand. Re-render with build_artifacts.py.</footer>
<script>{vb.COPY_JS}{PREVIEW_JS}</script>
</body>
</html>
"""
