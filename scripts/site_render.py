"""lewitt system/ — dual-view immersive long scroll (full mode).

Every value is a render of dna.json: specimens live in `dna.specimens`, layout in one of two views
chosen at the top bar.

    Live Preview   the source site's own voice: --lw-* canvas, text and action fill a numbered
                   long scroll (01 colour · 02 type · 03 components · 04 motion & guardrails ·
                   05 clipped bricks) with the counters that set lewitt apart (Observed tags on
                   proof/spec surfaces, drawn bezier curves, MUST NOT gate capsules, bricks).
    Specs          the engagement record: overview, tokens, measurements, evidence, limits,
                   code and downloads, fidelity.

A third switch, Stress, feeds the same boolean into both views: the preview stands a fixed-width
site frame on a neutral field (the engagement-document metaphor: share a museum specimen, or drop
it into a phone), and the specs table re-cuts its cells.

`specimens.backdrop` names the source's own section rhythm — `canvas`, `surface`, `action`, or one
role per section including `nav` — and `specimens.hero.heightToken` may name a height token. The
renderers read those names; they never move a value from one role to another.
"""

from __future__ import annotations

import re

import build_artifacts as ba
import visual_base as vb

STRESS = (("long", "Long copy"), ("reduced", "Reduced motion"), ("narrow", "Narrow 390"))
VIEWS = (("live", "Live Preview"), ("specs", "Specs &amp; Evidence"))


NAV_LINKS = (("colour", "Colour"), ("type", "Type"), ("components", "Components"),
             ("motion", "Motion"), ("bricks", "Bricks"))


LIVE_NAV = (("hero", "Home"), ("colour", "Colour"), ("type", "Type"), ("components", "Components"),
            ("motion", "Motion"), ("bricks", "Bricks"))


def _is_wordmark(dna: dict) -> bool:
    """True when the captured mark already spells the name (a wordmark), so the nav must not print it twice.

    A letterhead is wide and carries a path per glyph; a geometric symbol is roughly square or a single
    path. The measurement lives in the asset, so it is read, not guessed."""
    asset = (dna.get("specimens") or {}).get("brandSvg")
    if not asset:
        return False
    vb = re.search(r'viewBox="\s*([0-9.]+)[\s,]+([0-9.]+)[\s,]+([0-9.]+)[\s,]+([0-9.]+)', asset)
    glyphs = len(re.findall(r"<path\b", asset))
    if not vb:
        return glyphs >= 4
    w, h = float(vb.group(3)), float(vb.group(4))
    return h > 0 and (w / h) >= 2.2 and glyphs >= 3


def brand_svg(dna: dict, ink: str = "auto") -> str:
    """The mark: the run's own brand-svg asset when it ships one, else lewitt's line study
    painted in the run's roles (ink / brand / up / down)."""
    asset = (dna.get("specimens") or {}).get("brandSvg")
    if asset:
        css = {t["id"]: t["css"].lstrip("-") for t in dna["tokens"]}

        def role(*prefixes):
            for p in prefixes:
                for k, v in css.items():
                    if k.startswith(p):
                        return f"var(--{v})"
            return None
        colour = {"canvas": role("color/canvas"), "screen": role("color/action/fg")}.get(ink) or "currentColor"
        return re.sub(r"<svg\b", f'<svg class="lp-brand-mark" fill="{colour}"', asset, count=1)
    css = {t["id"]: t["css"].lstrip("-") for t in dna["tokens"]}

    def role(*prefixes):
        for p in prefixes:
            for k, v in css.items():
                if k.startswith(p):
                    return f"var(--{v})"
        return None

    ink = role("color/text/heading", "color/text/primary") or "currentColor"
    brand = role("color/brand", "color/action/bg") or ink
    up = role("color/trend/up", "color/up") or brand
    down = role("color/trend/down", "color/down") or brand
    return ('<svg class="lw-mark-live" viewBox="0 0 16 16" aria-hidden="true" focusable="false">'
            '<g fill="none" stroke-width="1" stroke-linecap="square">'
            f'<path d="M7.5 0V7.5" stroke="{ink}"/><path d="M8.5 8.5H16" stroke="{brand}"/>'
            f'<path d="M0.5 8.5L7.5 15.5" stroke="{down}"/><path d="M15.5 8.5L8.5 15.5" stroke="{up}"/>'
            '</g></svg>')


def _live_section(key: str, html: str, role: str = "canvas") -> str:
    """One long-scroll step, painted by the source's own rhythm (specimens.backdrop)."""
    if key == "hero":
        return f'<div class="lp-hero" id="{key}" data-sec="{key}" data-backdrop="{role}">{html}</div>'
    return f'<section class="lp-sec" id="{key}" data-sec="{key}" data-backdrop="{role}">{html}</section>'


def _attr(text) -> str:
    return str(text).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def _e(text) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def app_shell(dna: dict, resolved: dict, live: dict[str, str], specs: dict[str, str], *, pages: int) -> str:
    """live: {section_id: inner HTML}; specs: {panel_id: inner HTML}. Sections render in the given order."""
    meta = dna["meta"]
    canvas = next((resolved[t["id"]]["resolved"] for t in dna["tokens"] if t["id"] == "color/canvas"), None)
    tone = vb.tone_of(canvas)
    name = meta.get("name") or meta.get("domain") or "design system"
    views = "".join(
        f'<button class="tp-seg" role="tab" id="tab-{key}" aria-controls="view-{key}" '
        f'aria-selected="{"true" if key == "live" else "false"}" tabindex="{"0" if key == "live" else "-1"}">'
        f'{label}</button>' for key, label in VIEWS)
    stress = "".join(
        f'<button class="tp-btn tb-menu-item" role="menuitemcheckbox" data-stress-toggle="{key}" '
        f'aria-pressed="false">{label}</button>'
        for key, label in STRESS)
    spec = dna.get("specimens") or {}
    nav_tone = (spec.get("backdrop") or {}).get("nav")
    nav_cls = "lp-nav lp-nav--bar" if nav_tone else "lp-nav"
    mark_ink = "canvas" if nav_tone == "action" else "screen" if nav_tone == "canvas" else "auto"
    links = "".join(f'<a href="#{k}">{lbl}</a>' for k, lbl in LIVE_NAV)
    cta_label = (spec.get("nav") or {}).get("cta") or (spec.get("hero") or {}).get("primaryCta") or "Primary action"
    cta_cls = "ds-btn ds-btn--primary" if nav_tone != "action" else "ds-btn ds-btn--secondary is-on-bar"
    live_body = (
        f'<nav class="{nav_cls}" aria-label="{_e(name)} — specimen faces">'
        f'<span class="lp-nav-brand" aria-label="{_e(name)}">{brand_svg(dna, mark_ink)}'
        + (f'<span class="sr-only">{_e(name)}</span>' if _is_wordmark(dna) else _e(name)) + '</span>'
        f'<span class="lp-nav-links">{links}</span>'
        f'<button class="{cta_cls} lp-nav-cta" type="button">{_e(cta_label)}</button></nav>'
        + "".join(
            _live_section(key, html, (spec.get("backdrop") or {}).get(key, "canvas")) for key, html in live.items())
        + f'<footer class="lp-foot"><span>{_e(name)} · specimen built by lewitt from dna.json</span>'
          f'<span>{len(dna["tokens"])} tokens · {len(dna["evidence"])} evidence</span></footer>')
    specs_body = "".join(f'<section class="sp-panel" id="sp-{key}" data-panel="{key}">{html}</section>'
                         for key, html in specs.items())
    pages_list = meta.get("crawl", {}).get("pages") or [meta["source"]]

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>lewitt — {_e(name)} design system (full mode)</title>
<link rel="stylesheet" href="../tokens.css">
<link rel="stylesheet" href="doc.css">
<link rel="stylesheet" href="site.css">
<link rel="stylesheet" href="system.css">
<script>document.documentElement.classList.add('js');</script>
</head>
<body data-view="live" data-stress="" data-tone="{tone}" data-site="{_attr(name)} design system">
<a class="skip" href="#main">Skip to content</a>
<header class="topbar">
  <div class="tb-left">
    {vb.lines_mark("lw-mark")}
    <span class="tb-site">{_e(name)}</span>
    <span class="fpl" id="fp" aria-hidden="true"></span>
  </div>
  <div class="tb-center">
    <div class="tb-seg" role="tablist" aria-label="View">{views}</div>
  </div>
  <button class="lp-ev" id="lp-ev" type="button" aria-label="observed evidence"></button>
  <div class="tb-right">
    <button class="tp-btn tp-copy" id="copy-theme" aria-label="Copy shadcn-theme.css">Copy shadcn-theme.css</button>
    <div class="tb-stress">
      <button class="tp-btn tb-stress-btn" id="stress-btn" type="button" aria-expanded="false" aria-controls="stress-menu">Stress <span class="caret" aria-hidden="true">▾</span></button>
      <div class="tb-menu" id="stress-menu" role="group" aria-label="Stress controls" hidden>{stress}</div>
    </div>
    <span class="tb-status" id="tb-status" aria-live="polite"></span>
  </div>
</header>
<main id="main">
<div class="view view-live" id="view-live" role="tabpanel" aria-labelledby="tab-live">
  <div class="lp-frame" id="lp-frame">
    <div class="lp-dock" aria-hidden="true"></div>
    <div class="lp-scroll" data-ds>{live_body}</div>
  </div>
</div>
<div class="view view-specs" id="view-specs" role="tabpanel" aria-labelledby="tab-specs" hidden>
  <div class="sp-wrap">{specs_body}</div>
</div>
</main>
<script id="evidence-data" type="application/json">{_json(evidence_for_tags(dna))}</script>
<script id="theme-css" type="text/plain">{_e(render_theme_file(dna))}</script>
<script src="system.js"></script>
</body>
</html>
"""


def _json(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def evidence_for_tags(dna: dict) -> dict:
    """What an Observed tag opens: one real ledger entry per tag class, by theme — colour, type,
    motion or material — plus the entry behind the run's one signature claim."""
    themes = {
        "palette": r"canvas|oatmeal|surface|oatmeal-scale|canvas-light|home-bg|bg$|text-color|ink|brand|accent|up|down|purple",
        "typography": r"font|type|weight|size|heading|h1|h2|h3|h4|body|display",
        "motion": r"motion|ease|duration|transition|reduced|hover",
        "material": r"radius|radii|shadow|depth|ring|pill|button|buttons|pill|border",
    }
    out: dict[str, dict] = {}
    for tag, pattern in themes.items():
        hits = [e for e in dna["evidence"] if re.search(pattern, e["id"] + " " + e.get("locator", ""), re.I)]
        if not hits:
            hits = dna["evidence"][:1]
        entries = [{k: e.get(k) for k in ("id", "url", "locator", "method", "state")} |
                   {"values": dict(list((e.get("values") or {}).items())[:6])} for e in hits[:3]]
        out[tag] = {"primary": entries[0], "also": [x["id"] for x in entries[1:]],
                    "entries": {x["id"]: x for x in entries}}
    return out


def render_theme_file(dna: dict) -> str:
    return ba.render_shadcn_theme(dna)


# ------------------------------------------------------------------ helpers shared by both renders
def reads(resolved: dict) -> dict[str, str]:
    """Which CSS variable a specimen should read for each role, decided from the run's own token ids."""
    sem = {t["id"] for t in resolved.values() if t["type"] == "color"} if isinstance(next(iter(resolved.values())), dict) else set()
    ids = set(resolved)

    def pick(prefixes, fallback=None):
        for p in prefixes:
            for i in sorted(ids):
                if i.startswith(p):
                    return f"var(--{(resolved[i]['css'] or '').lstrip('-')})"
        return fallback

    return {
        "surface": pick(("color/surface", "color/well", "color/canvas-tint")),
        "well": pick(("color/well", "color/surface-subtle", "color/canvas-tint")),
        "border": pick(("color/border", "color/ring", "color/surface-subtle")),
        "heading": pick(("color/text/heading", "color/text/primary")),
        "body": pick(("color/text/body", "color/text/secondary")),
        "muted": pick(("color/text/muted", "color/text/tertiary", "color/text/secondary")),
        "link": pick(("color/link", "color/text/heading", "color/text/primary")),
    }


def specimen_text(dna: dict) -> dict:
    """Site-voice copy from dna.specimens; neutral when absent (never another site's sentence)."""
    specs = dna.get("specimens") or {}
    hero = specs.get("hero") or {}
    lines = [ln for ln in (hero.get("headline") or "").split("\n") if ln.strip()]
    sentence = lines[0] if lines else "Specimen copy is set at this step"
    return {
        "hero": hero,
        "headline_lines": lines,
        "sentence": sentence,
        "stats": specs.get("stats") or [],
        "cards": specs.get("cards") or [],
        "table": specs.get("table"),
        "form": specs.get("form"),
        "eyebrow": hero.get("eyebrow"),
        "cta": hero.get("primaryCta"),
        "typeSpecimens": specs.get("typeSpecimens") or {},
        "media": hero.get("media") or "",
        "display_face": "the declared stack",
    }


NUMERIC = re.compile(r"figure|numeric|digit|number|num(?!eral-word)", re.IGNORECASE)


def specimen_for(t: dict, resolved: dict, text: dict) -> tuple[str, str]:
    """(text, extra style) for one type token: the run's per-step copy first, then its first stat /
    headline, and a bare numeral only when the run supplies neither."""
    step = (text.get("typeSpecimens") or {}).get(t["id"])
    size = str(resolved[t["id"]]["resolved"])
    if step:
        return step, ""
    if NUMERIC.search(t["id"].split("/")[-1]):
        stats = text["stats"]
        figure = str(stats[0]["value"]) if stats else "0123456789"
        mono = resolved.get("font/mono", {}).get("resolved") or "var(--n-mono)"
        return figure, f"font-family:{mono};font-variant-numeric:tabular-nums;font-weight:400"
    m = re.match(r"([0-9.]+)", size)
    if m and float(m.group(1)) <= 14:
        stats = text["stats"]
        return (str(stats[1]["value"]) if len(stats) > 1 else "Aa 0123"), ""
    return text["sentence"], ""


def type_rows(tokens: list[dict], resolved: dict, text: dict, *, tag_prefix: str = "") -> str:
    """Parameters on the left, the specimen at its real size on the right (Live Preview: '+ Observed')."""
    light = next((t["id"] for t in tokens if t["type"] == "fontWeight"
                  and t["id"].endswith(("light", "regular", "body"))),
                 next((t["id"] for t in tokens if t["type"] == "fontWeight"), None))
    weight = resolved[light]["resolved"] if light else "400"
    tracking = next((v["resolved"] for k, v in resolved.items() if k.startswith("tracking/") and v["resolved"] != "0em"), "normal")
    rows = []
    for t in tokens:
        if t["type"] != "dimension" or not t["id"].startswith("type/"):
            continue
        size = resolved[t["id"]]["resolved"]
        label, extra = specimen_for(t, resolved, text)
        # steps that are not display sizes carry the reading tracking, not the display cut
        numeric = re.match(r"([0-9.]+)", str(size))
        big = bool(numeric) and float(numeric.group(1)) >= 40
        own_track = tracking if big else "normal"
        own_weight = weight if ("display" in t["id"] or "headline" in t["id"]) else "400"
        obs = ('<button class="tag-obs" data-obs="typography">+ Observed</button>'
               if tag_prefix else "")
        rows.append(
            f'<div class="type-row"><div class="type-params">'
            f'<span class="mono" data-copy="var(--{_e(t["css"].lstrip("-"))})" role="button" tabindex="0">'
            f'{_e(t["id"])}</span>'
            f'<dl><dt>size</dt><dd>{_e(size)}</dd><dt>weight</dt><dd>{_e(own_weight)}</dd>'
            f'<dt>tracking</dt><dd>{_e(own_track)}</dd></dl>{obs}</div>'
            f'<div class="type-specimen"><span class="spec" style="font-size:{_e(size)};font-weight:{_e(own_weight)};'
            f'letter-spacing:{_e(own_track)}{extra}">{_e(label)}</span></div></div>'
        )
    return "".join(rows)


def weight_rows(tokens: list[dict], resolved: dict, text: dict) -> str:
    rows = []
    for t in tokens:
        if t["type"] != "fontWeight":
            continue
        w = resolved[t["id"]]["resolved"]
        rows.append(
            f'<div class="type-row"><div class="type-params">'
            f'<span class="mono" data-copy="var(--{_e(t["css"].lstrip("-"))})">{_e(t["id"])}</span>'
            f'<dl><dt>weight</dt><dd>{_e(w)}</dd></dl></div>'
            f'<div class="type-specimen"><span class="spec" style="font-size:32px;font-weight:{_e(w)}">'
            f'{_e(text["sentence"])}</span></div></div>'
        )
    return "".join(rows)


def guardrail_caps(j: dict, *, expandable: bool, tag: str = "gate-regex") -> str:
    """MUST NOT capsules. `expandable` folds the regex / json behind a <details> (Live Preview)."""
    if not j:
        return ""
    caps: list[str] = []
    reg = ""
    for prop in j.get("forbidCss") or []:
        caps.append(f'<li class="gate forbid">must not · <code>{_e(prop)}</code></li>')
    if j.get("forbidClass"):
        patterns = "".join(f"<li><code>{_e(p)}</code></li>" for p in j["forbidClass"])
        if expandable:
            reg = (f'<li class="gate forbid {tag}"><details><summary>must not · '
                   f'{len(j["forbidClass"])} class regex</summary><ul class="regex">{patterns}</ul>'
                   f'</details></li>')
        else:
            caps.append(f'<li class="gate forbid">must not · {len(j["forbidClass"])} class pattern(s)</li>')
    for prop in j.get("requireCss") or []:
        caps.append(f'<li class="gate require">must · <code>{_e(prop)}</code></li>')
    for prop, bound in (j.get("max") or {}).items():
        caps.append(f'<li class="gate max">max · <code>{_e(prop)}</code> ≤ '
                    f'{_e(bound.get("value"))}{_e(bound.get("unit", ""))}</li>')
    if j.get("note"):
        caps.append(f'<li class="gate note">{_e(j["note"])}</li>')
    return f'<ul class="gates">{"".join(caps)}{reg}</ul>'


def bezier_track(spec: str, dur: str, *, prefix: str) -> str:
    """One motion row: the curve drawn from the token, a track the Replay slider drives, a scrubber."""
    dot = f"{prefix}-dot"
    return (f'<div class="motion"><div class="plot">{vb.bezier_svg(spec)}</div>'
            f'<div class="mid"><div class="mono">{_e(spec)}</div>'
            f'<div class="track" data-track id="{dot}-track"><span class="dot" id="{dot}"></span></div></div>'
            f'<div class="act"><label class="mono" for="{dot}-range">Replay</label>'
            f'<input type="range" id="{dot}-range" class="motion-range" min="0" max="1000" value="0" '
            f'aria-label="scrub the motion timeline">'
            f'<button class="tp-btn" data-sys-replay="{dot}" data-dur="{_e(dur)}" data-ease="{_e(spec)}">'
            f'Play</button></div></div>')


# ------------------------------------------------------------------ CSS (the template)
CSS = """
/* ============================================================ system/ — dual-view long scroll
   Chrome is neutral (visual_base); the source's own colour lives only inside [data-ds],
   which is everything under the Live Preview frame. */

:root { --sp-max: 1240px; --lp-max: 1180px; }
body { margin: 0; background: var(--n-bg); }

/* ---------------------------------------------------------------- sticky minimal top bar */
.topbar { position: sticky; top: 0; z-index: 30; display: flex; align-items: center; gap: 16px;
  min-height: 54px; padding: 8px 20px; background: color-mix(in srgb, var(--n-bg) 88%, transparent);
  -webkit-backdrop-filter: saturate(140%) blur(10px); backdrop-filter: saturate(140%) blur(10px);
  border-bottom: 1px solid var(--n-line); }
.tb-left { display: flex; align-items: center; gap: 10px; min-width: 0; }
.tb-left .lw-mark { color: var(--n-ink); flex: none; }
.tb-site { font-size: 13px; color: var(--n-ink); letter-spacing: -.01em; white-space: nowrap; }
.tb-left .fpl { width: 56px; height: 3px; flex: none; border-radius: 2px; }
.tb-meta { font: 10.5px/1 var(--n-mono); letter-spacing: .04em; text-transform: uppercase;
  color: var(--n-faint); white-space: nowrap; }
.tb-center { margin: 0 auto; }
.tb-seg { display: inline-flex; padding: 3px; gap: 2px; border: 1px solid var(--n-line-strong); border-radius: 999px; }
.tp-seg { font: 500 12px/1 var(--n-sans); letter-spacing: .01em; padding: 7px 14px; border: 0; border-radius: 999px;
  background: transparent; color: var(--n-mute); cursor: pointer; white-space: nowrap; }
.tp-seg[aria-selected="true"] { background: var(--n-ink); color: var(--n-bg); }
.tp-seg:hover:not([aria-selected="true"]) { color: var(--n-ink); }
.tb-right { display: flex; align-items: center; gap: 8px; margin-left: auto; }
/* one compact Stress control opens to the three booleans; the buttons keep data-stress-toggle */
.tb-stress { position: relative; }
.tb-stress-btn { color: var(--n-ink); border-color: var(--n-ink); display: inline-flex; align-items: center; gap: 6px; }
.tb-stress-btn[aria-expanded="true"] { background: var(--n-ink); color: var(--n-bg); }
.tb-stress-btn[aria-expanded="true"] .caret { transform: rotate(180deg); }
.tb-stress-btn .caret { display: inline-block; font-size: 9px; opacity: .7; transition: transform .15s ease; }
.tb-stress-btn.has-on::after { content: ""; width: 5px; height: 5px; border-radius: 50%; background: var(--n-ok); }
.tb-menu { position: absolute; right: 0; top: calc(100% + 6px); z-index: 50; min-width: 180px; display: grid; gap: 2px;
  padding: 6px; border-radius: 8px; background: var(--n-panel); border: 1px solid var(--n-line-strong); }
.tb-menu[hidden] { display: none; }
.tb-menu-item { text-align: left; border-color: transparent; color: var(--n-mute); padding: 8px 10px; border-radius: 5px; }
.tb-menu-item:hover { background: var(--n-hover); color: var(--n-ink); }
.tb-menu-item[aria-pressed="true"] { color: var(--n-ink); border-color: transparent; background: var(--n-hover); }
.tb-menu-item[aria-pressed="true"]::before { content: "✓"; display: inline-block; width: 12px; font-size: 10px; margin-right: 4px; }
.tb-menu-item[aria-pressed="false"]::before { content: ""; display: inline-block; width: 12px; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
.tb-meta { font: 10.5px/1 var(--n-mono); letter-spacing: .04em; text-transform: uppercase; color: var(--n-faint); }
.tp-btn { font: 500 11px/1 var(--n-mono); letter-spacing: .04em; padding: 7px 10px; background: transparent;
  color: var(--n-mute); border: 1px solid var(--n-line-strong); border-radius: 4px; cursor: pointer;
  white-space: nowrap; }
.tp-btn:hover { color: var(--n-ink); border-color: var(--n-ink); }
.tp-btn[aria-pressed="true"] { background: var(--n-ink); color: var(--n-bg); border-color: var(--n-ink); }
.tp-copy { color: var(--n-ink); border-color: var(--n-ink); }
.tp-copy.ok { background: var(--n-ink); color: var(--n-bg); }
.tb-status { font: 10.5px/1 var(--n-mono); color: var(--n-mute); max-width: 120px; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; }
.tb-status:empty { display: none; }
.skip { position: absolute; left: -9999px; }
.skip:focus { left: 12px; top: 8px; z-index: 50; background: var(--n-ink); color: var(--n-bg);
  padding: 8px 12px; font: 500 11px/1 var(--n-mono); text-transform: uppercase; letter-spacing: .06em; }

@keyframes lw-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
@keyframes lw-pulse { 0% { transform: translateX(0); } 50% { transform: translateX(calc(100% - 10px)); } 100% { transform: translateX(0); } }

/* ---------------------------------------------------------------- Live Preview: frame + dock */
.view-live { position: relative; }
.lp-frame { position: relative; margin: 22px auto 60px; max-width: var(--lp-max); width: calc(100% - 40px);
  border-radius: 10px; overflow: hidden; border: 1px solid var(--n-line); }
body[data-stress~="narrow"] .lp-frame { width: 790px; max-width: none; margin-left: auto; }
.lp-scroll { background: var(--lw-canvas); color: var(--lw-text-body, var(--lw-text-primary));
  font-family: var(--lw-font-body); animation: lw-rise .5s ease both; }
body[data-stress~="narrow"] .lp-scroll { width: 390px; }
.lp-dock { display: none; }

/* the same mark, in the source's canvas colours */
.lw-mark-live { width: 18px; height: 18px; flex: none; vertical-align: -3px; }
.lp-nav-brand .lw-mark-live { width: 17px; height: 17px; }
.lp-nav-brand .lp-brand-mark { height: 22px; width: auto; display: block; }
.lp-nav--bar { background: var(--nav-bg); border-bottom-color: var(--nav-line); }
.lp-nav--bar .lp-nav-brand, .lp-nav--bar .lp-nav-links a { color: var(--nav-fg); }
.lp-nav--bar .ds-btn--secondary.is-on-bar { color: var(--nav-fg); border-color: color-mix(in srgb, var(--nav-fg) 32%, transparent); background: transparent; }
.lp-nav--bar .ds-btn--secondary.is-on-bar:hover { background: color-mix(in srgb, var(--nav-fg) 10%, transparent); }
.lp-hero .hero-copy .lw-mark-live { width: 22px; height: 22px; margin-bottom: 14px; }
.lp-hero .hero-note .tag-obs { margin-left: 6px; vertical-align: 1px; }

/* specimens.backdrop: the source's section rhythm, painted from named roles only */
.lp-sec[data-backdrop], /* specimens.backdrop: the source's own section rhythm, painted from named roles only.
   The section itself carries the pair (--bd-bg / --bd-fg); its children inherit the colour. */
[data-backdrop] { --bd-bg: var(--lw-canvas); --bd-fg: var(--lw-text-primary); }
[data-backdrop="canvas"] { --bd-bg: var(--lw-canvas); --bd-fg: var(--lw-text-primary); }
[data-backdrop="surface"] { --bd-bg: var(--lw-surface); --bd-fg: var(--lw-text-heading, var(--lw-text-primary)); }
[data-backdrop="action"] { --bd-bg: var(--lw-action-bg); --bd-fg: var(--lw-action-fg); }
.lp-sec[data-backdrop], .lp-hero[data-backdrop] { background: var(--bd-bg); color: var(--bd-fg); }
[data-backdrop="action"].lp-sec .lp-lede, [data-backdrop="action"].lp-sec .lp-num,
[data-backdrop="action"].lp-sec .lp-group h3 .scene, [data-backdrop="action"].lp-sec .hero-note,
[data-backdrop="action"].lp-sec .tcard .why, [data-backdrop="action"].lp-sec .graphic-cap,
[data-backdrop="action"].lp-sec .lp-figcaption { color: var(--bd-fg); opacity: .86; }
[data-backdrop="action"].lp-sec .lp-title, [data-backdrop="action"].lp-sec .lp-group h3,
[data-backdrop="action"].lp-sec .tcard h4, [data-backdrop="action"].lp-sec .gate,
[data-backdrop="action"].lp-sec .gate code { color: var(--bd-fg); }
[data-backdrop="action"].lp-sec .swatch { background: var(--lw-canvas); }
[data-backdrop="action"].lp-sec .tcard { background: var(--lw-canvas); }
[data-backdrop="action"].lp-sec .gate { border-color: color-mix(in srgb, var(--bd-fg) 26%, transparent);
  background: color-mix(in srgb, var(--bd-fg) 7%, transparent); }
[data-backdrop="action"].lp-sec .regex { background: color-mix(in srgb, var(--lw-canvas) 12%, transparent); }
[data-backdrop="action"].lp-sec .track { background: color-mix(in srgb, var(--bd-fg) 28%, transparent); }
[data-backdrop="action"].lp-sec .track .dot { background: var(--bd-fg); border-color: var(--bd-bg); }
[data-backdrop="action"].lp-sec .motion-range { accent-color: var(--bd-fg); }
[data-backdrop="action"].lp-sec .motion .act label,
[data-backdrop="action"].lp-sec .motion .spec-val { color: var(--bd-fg); opacity: .8; }
[data-backdrop="action"].lp-sec .motion .act .tp-btn { color: var(--bd-fg); border-color: color-mix(in srgb, var(--bd-fg) 45%, transparent); }
[data-backdrop="action"].lp-sec .sw, [data-backdrop="action"].lp-sec .lp-sheet .rule,
[data-backdrop="action"].lp-sec .motion, [data-backdrop="action"].lp-sec .pairs .prow {
  border-color: color-mix(in srgb, var(--bd-fg) 20%, transparent); }
[data-backdrop="action"].lp-sec .tag-obs { color: var(--bd-fg); border-color: color-mix(in srgb, var(--bd-fg) 40%, transparent); }
[data-backdrop="action"].lp-sec .tag-obs::before { background: var(--bd-fg); }
[data-backdrop="action"].lp-sec .tag-obs[aria-disabled="true"] { opacity: .8; cursor: default; }
.lp-hero[data-height-token] { min-height: min(var(--hero-height, 640px), 78vh); }
.lp-hero.hero-card [data-backdrop] {}

/* preview nav + footer: the site's own furniture, in the site's own tokens */
.lp-nav { display: flex; align-items: center; gap: 28px; padding: 18px 56px; border-bottom: 1px solid;
  border-color: var(--lw-border, transparent); font-size: var(--lw-type-ui); }
.lp-nav-brand { display: inline-flex; align-items: center; gap: 9px; font-weight: var(--lw-weight-ui-strong, 600);
  letter-spacing: var(--lw-tracking-hero, -.01em); color: var(--lw-text-heading, var(--lw-text-primary)); }
.lp-nav-links { display: flex; gap: 22px; margin-left: auto; }
.lp-nav-links a { color: var(--lw-text-body, var(--lw-text-primary)); text-decoration: none; opacity: .85; }
.lp-nav-links a:hover { opacity: 1; }
.lp-nav-cta { padding: 9px 16px; border: 0; }
.lp-foot { display: flex; justify-content: space-between; gap: 16px; padding: 22px 56px; border-top: 1px solid;
  border-color: var(--lw-border, transparent); font: 10.5px/1.5 var(--n-mono);
  color: var(--lw-text-muted, var(--lw-text-body)); }
body[data-stress~="narrow"] .lp-nav-links { display: none; }
body[data-stress~="narrow"] .lp-nav, body[data-stress~="narrow"] .lp-foot { padding-left: 24px; padding-right: 24px; }

/* section rhythm */
.lp-sec { padding: 64px 56px 76px; border-top: 1px solid; border-color: var(--lw-border, var(--lw-canvas-tint));
  scroll-margin-top: 64px; }
.lp-sec:first-child { border-top: 0; }
.lp-sheet { display: flex; align-items: baseline; gap: 14px; margin: 0 0 10px; }
.lp-num { font: 500 11px/1 var(--n-mono); letter-spacing: .1em; color: var(--lw-text-muted, var(--lw-text-body)); }
.lp-title { margin: 0; font-size: var(--lw-type-h3); font-weight: inherit;
  color: var(--lw-text-heading, var(--lw-text-primary)); letter-spacing: var(--lw-tracking-h2, normal); }
.lp-sheet .rule { flex: 1; height: 1px; background: var(--lw-border, var(--lw-canvas-tint)); align-self: center; }
.lp-sheet .count { font: 11px/1 var(--n-mono); color: var(--lw-text-muted, var(--lw-text-body)); }
.lp-swatches-hint { display: none; }
.lp-lede { margin: 0 0 34px; max-width: 64ch; font-size: var(--lw-type-body); line-height: var(--lw-leading-prose, 1.5);
  color: var(--lw-text-body, var(--lw-text-primary)); }

/* proof / spec garment: the Observed tag and its evidence card */
.tag-obs { display: inline-flex; align-items: center; gap: 5px; font: 500 9.5px/1 var(--n-mono);
  letter-spacing: .08em; text-transform: uppercase; padding: 4px 7px; border-radius: 999px;
  border: 1px solid; border-color: var(--lw-border-strong, var(--lw-border, currentColor));
  background: transparent; color: var(--lw-text-muted, var(--lw-text-body)); cursor: pointer; }
.tag-obs::before { content: ""; width: 5px; height: 5px; border-radius: 50%; background: var(--lw-trend-up, currentColor); }
.tag-obs:hover { color: var(--lw-text-heading, var(--lw-text-primary)); }
.lp-ev { display: none; position: fixed; z-index: 40; width: min(380px, calc(100vw - 24px)); padding: 14px 16px 12px;
  border-radius: 8px; border: 1px solid var(--n-line-strong); background: var(--n-panel); color: var(--n-ink);
  font: 12px/1.5 var(--n-sans); }
.lp-ev[data-open] { display: block; }
.lp-ev .ev-head { display: flex; justify-content: space-between; gap: 10px; align-items: baseline;
  font: 500 10px/1 var(--n-mono); letter-spacing: .08em; text-transform: uppercase; color: var(--n-mute); }
.lp-ev .ev-id { font: 12px/1.4 var(--n-mono); color: var(--n-ink); margin: 10px 0 2px; word-break: break-all; }
.lp-ev .ev-loc { color: var(--n-mute); font-size: 12px; margin: 0 0 8px; }
.lp-ev dl { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 3px 14px; font: 11.5px/1.45 var(--n-mono); }
.lp-ev dt { color: var(--n-mute); } .lp-ev dd { margin: 0; word-break: break-word; }
.lp-ev .ev-x { border: 0; background: transparent; color: var(--n-mute); font: 11px/1 var(--n-mono); cursor: pointer; }
.lp-ev .ev-again { margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--n-line);
  font: 10.5px/1.5 var(--n-mono); color: var(--n-mute); }

/* ---------------------------------------------------------------- hero (first screen = brand) */
.lp-hero--solo { grid-template-columns: minmax(0, 1fr); }
.lp-hero--solo .hero-copy { max-width: none; }
.lp-hero.lp-hero--solo .h1 block { display: block; }
.lp-hero--solo h1 { font-size: var(--lw-type-display-xl, var(--lw-type-hero)); }
.lp-hero { display: grid; grid-template-columns: minmax(0, 1fr); gap: 0; align-items: start;
  padding: 44px 56px 48px; background: var(--bd-bg, var(--lw-canvas)); }
.lp-hero--solo { grid-template-columns: minmax(0, 1fr); }
.lp-hero .hero-before { display: none; }
.lp-hero .hero-copy { display: grid; gap: 0; align-content: start; justify-items: start; }
.lp-hero .hero-note { grid-column: 1 / -1; margin: 18px 0 0; font: 10.5px/1.5 var(--n-mono);
  color: var(--lw-text-muted, var(--lw-text-body)); }
.lp-hero .hero-note code { font-family: var(--n-mono); }
.graphic-cap { display: block; margin: 26px 0 0 6px; font: 10.5px/1.5 var(--n-mono);
  color: var(--lw-text-muted, var(--lw-text-body)); max-width: 44ch; }
.lp-hero .eyebrow { display: inline-flex; align-items: center; gap: 8px; margin: 0 0 26px; padding: 5px 16px 5px 5px;
  min-height: 42px; border-radius: var(--lw-radius-pill, 999px); border: 1px solid var(--lw-border, var(--lw-border-strong));
  font: 400 13px/1.4 var(--lw-font-body, var(--n-sans)); color: var(--lw-text-primary, var(--lw-text-heading));
  letter-spacing: normal; text-transform: none; }
.lp-hero .eyebrow::before { content: ""; width: 30px; height: 30px; border-radius: 50%; flex: none;
  background: var(--lw-accent, var(--lw-brand, var(--lw-action-bg)));
  clip-path: polygon(36% 27%, 78% 50%, 36% 73%); }
.lp-hero h1 { margin: 0 0 22px; font-size: var(--lw-type-display-xl, var(--lw-type-hero)); line-height: 1;
  font-weight: inherit; letter-spacing: normal; color: var(--lw-text-primary, var(--lw-text-heading));
  max-width: 22ch; }
.lp-hero h1 span { display: block; }
.lp-hero .sub { margin: 26px 0 32px; max-width: 44ch; font-size: var(--lw-type-lead, var(--lw-type-body));
  line-height: var(--lw-leading-prose, 1.5); color: var(--lw-text-primary, var(--lw-text-body)); }
.lp-hero .hero-band { width: 100%; height: 190px; margin: 36px 0 0; border-radius: var(--lw-radius-card, 8px);
  overflow: hidden; border: 1px solid var(--lw-border, transparent); background: var(--lw-surface); }
.lp-hero .hero-band img { width: 100%; height: 100%; object-fit: cover; object-position: 50% 22%; display: block; }
.lp-hero .ctas { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
.graphic { position: relative; padding: 6px 0 0; }
.twin-card { position: relative; overflow: hidden; isolation: isolate; border-radius: var(--lw-radius-card, 12px);
  border: 1px solid; border-color: var(--lw-border, var(--lw-border-strong)); background: var(--lw-surface, var(--lw-well));
  aspect-ratio: 4 / 3.1; display: flex; flex-direction: column; transform: rotate(-4deg);
  box-shadow: var(--lw-depth-float, none); }
.twin-card .band { height: 46%; background: linear-gradient(112deg,
  color-mix(in srgb, var(--lw-trend-up, var(--lw-brand)) 32%, var(--lw-surface)) 0%,
  var(--lw-brand, var(--lw-action-bg)) 58%, color-mix(in srgb, var(--lw-trend-down, #c46a3a) 40%, var(--lw-canvas)) 100%);
  position: relative; }
.twin-card .bandlines { position: absolute; inset: 0; background: repeating-linear-gradient(90deg,
  color-mix(in srgb, var(--lw-canvas) 55%, transparent) 0 1px, transparent 1px 46px); opacity: .5; }
.twin-card .silhouette { position: absolute; left: 26%; bottom: 0; width: 30%; height: 78%;
  border-radius: 48% 48% 0 0; background: color-mix(in srgb, var(--lw-canvas) 16%, transparent);
  border: 1px solid color-mix(in srgb, var(--lw-canvas) 45%, transparent); border-bottom: 0; }
.twin-card .body { flex: 1; padding: 18px 20px; display: grid; align-content: start; gap: 10px; }
.twin-card .status { display: flex; align-items: center; gap: 8px; font: 11px/1 var(--n-mono);
  letter-spacing: .05em; color: var(--lw-text-muted, var(--lw-text-body)); }
.twin-card .status i { width: 7px; height: 7px; border-radius: 50%; background: var(--lw-brand, var(--lw-action-bg)); }
.twin-card .bar { height: 4px; border-radius: 2px; background: var(--lw-border, rgba(0,0,0,.12)); overflow: hidden; }
.twin-card .bar span { display: block; height: 100%; width: 25%; background: var(--lw-action-bg); }
.twin-card .name { font-size: var(--lw-type-title, var(--lw-type-ui)); color: var(--lw-text-heading, var(--lw-text-primary)); }
.twin-card .ghost { height: 76px; border-radius: 8px;
  background: color-mix(in srgb, var(--lw-canvas) 9%, var(--lw-text-heading, var(--lw-text-primary)) 0%); }
.twin-card .pill { position: absolute; right: 16px; top: 16px; padding: 6px 10px; border-radius: 999px;
  font: 500 10.5px/1 var(--n-mono); background: color-mix(in srgb, var(--lw-canvas) 86%, transparent);
  color: var(--lw-text-heading, var(--lw-text-primary)); border: 1px solid; border-color: var(--lw-border, transparent); }
.hero-side { display: grid; gap: 14px; margin-top: 8px; font: 10.5px/1.5 var(--n-mono); color: var(--lw-text-muted, var(--lw-text-body)); }
.hero-side .tag-obs { justify-self: start; }
.stat-strip { display: grid; grid-column: 1 / -1; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1px; margin-top: 32px; border-radius: 10px; overflow: hidden;
  background: var(--lw-border, var(--lw-canvas-tint)); border: 1px solid; border-color: var(--lw-border, var(--lw-canvas-tint)); }
.stat { padding: 18px 20px; background: var(--lw-canvas); display: grid; gap: 6px; }
.stat .v { font-size: var(--lw-type-headline, var(--lw-type-figure)); font-variant-numeric: tabular-nums;
  color: var(--lw-text-heading, var(--lw-text-primary)); letter-spacing: var(--lw-tracking-h2, normal); }
.stat .k { font: 11px/1.4 var(--n-mono); letter-spacing: .05em; text-transform: uppercase; color: var(--lw-text-muted, var(--lw-text-body)); }

/* ---------------------------------------------------------------- 01 colour */
.lp-groups { display: grid; gap: 30px; }
.lp-group h3 { display: flex; align-items: baseline; gap: 12px; margin: 0 0 12px; font: 500 12px/1 var(--n-mono);
  letter-spacing: .1em; text-transform: uppercase; color: var(--lw-text-heading, var(--lw-text-primary)); }
.lp-group h3 .scene { font: normal normal 11px/1.4 var(--n-sans); letter-spacing: 0; text-transform: none;
  color: var(--lw-text-muted, var(--lw-text-body)); }
.lp-group h3 .tag-obs { margin-left: auto; text-transform: none; }
.sw { display: grid; grid-template-columns: repeat(auto-fill, minmax(144px, 1fr)); width: 100%; box-sizing: border-box;
  border-radius: 8px; overflow: hidden; border: 1px solid; border-color: var(--lw-border, var(--lw-canvas-tint)); }
.swatch { background: var(--lw-canvas); padding: 12px 14px 12px; display: grid; gap: 8px; min-width: 0;
  border-right: 1px solid; border-bottom: 1px solid; border-color: var(--lw-border, var(--lw-canvas-tint)); }
.swatch .fill.is-translucent { background-image: linear-gradient(45deg, rgba(0,0,0,.10) 25%, transparent 25%, transparent 75%, rgba(0,0,0,.10) 75%),
  linear-gradient(45deg, rgba(0,0,0,.10) 25%, transparent 25%, transparent 75%, rgba(0,0,0,.10) 75%);
  background-size: 10px 10px; background-position: 0 0, 5px 5px; }
.swatch .fill { height: 66px; border-radius: 5px; border: 1px solid; border-color: color-mix(in srgb, var(--lw-text-heading, #000) 10%, transparent); }
.swatch .meta { display: flex; justify-content: space-between; gap: 8px; align-items: baseline; }
.swatch .tok { font: 11.5px/1.3 var(--n-mono); color: var(--lw-text-heading, var(--lw-text-primary)); overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; }
.swatch .hex { font: 11px/1.3 var(--n-mono); color: var(--lw-text-muted, var(--lw-text-body)); }
.swatch .sub { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
/* the ratio chip sits on a .swatch (canvas): its own pair - canvas fill + ink label - so the
   numerator/denominator it states is the pair it is painted with on both light and dark runs */
.wchip { font: 500 9.5px/1 var(--n-mono); letter-spacing: .05em; padding: 3px 6px; border-radius: 4px;
  border: 1px solid; white-space: nowrap;
  background: var(--lw-canvas); color: var(--lw-text-primary, var(--lw-text-heading));
  border-color: color-mix(in srgb, var(--lw-text-primary, var(--lw-text-heading)) 28%, var(--lw-canvas)); }
.wchip.ok, .wchip.warn, .wchip.bad { color: var(--lw-text-primary, var(--lw-text-heading));
  border-color: color-mix(in srgb, var(--lw-text-primary, var(--lw-text-heading)) 28%, var(--lw-canvas)); }
.wchip.ok::before { content: ""; display: inline-block; width: 5px; height: 5px; border-radius: 50%; margin-right: 5px;
  vertical-align: 1px; background: var(--n-ok); }
.wchip.warn::before { content: ""; display: inline-block; width: 5px; height: 5px; border-radius: 50%; margin-right: 5px;
  vertical-align: 1px; background: var(--n-warn); }
.wchip.bad::before { content: ""; display: inline-block; width: 5px; height: 5px; border-radius: 50%; margin-right: 5px;
  vertical-align: 1px; background: var(--n-bad); }
.pairs { margin-top: 26px; }
.pairs h3 { margin: 0 0 10px; font: 500 12px/1 var(--n-mono); letter-spacing: .1em; text-transform: uppercase;
  color: var(--lw-text-heading, var(--lw-text-primary)); }
.lp-groups .lp-group h3 .tag-obs { font-size: 9.5px; }
.pairs .prow { display: grid; grid-template-columns: minmax(0, 1fr) 220px; align-items: center;
  border-bottom: 1px solid; border-color: var(--lw-border, var(--lw-canvas-tint)); }
.pairs .prow .sample { padding: 18px; font-size: var(--lw-type-ui); line-height: 1.35; }
.pairs .prow .sample .cap-label { font: 10.5px/1 var(--n-mono); letter-spacing: .06em; text-transform: uppercase;
  opacity: .72; margin-bottom: 8px; display: block; }
.pairs .prow .pmeta { padding: 12px 0 12px 18px; display: grid; gap: 6px; align-content: center; justify-items: start;
  font: 11px/1.4 var(--n-mono); color: var(--lw-text-muted, var(--lw-text-body)); }

/* ---------------------------------------------------------------- 02 typography */
.type-scale-params { display: flex; flex-wrap: wrap; gap: 8px; margin: -18px 0 18px; font: 11px/1 var(--n-mono);
  color: var(--lw-text-muted, var(--lw-text-body)); }
.type-scale-params span { padding: 5px 8px; border-radius: 4px; border: 1px solid;
  border-color: var(--lw-border, var(--lw-canvas-tint)); }
.type-row { display: grid; grid-template-columns: 210px minmax(0, 1fr); align-items: center;
  border-top: 1px solid; border-color: var(--lw-border, var(--lw-canvas-tint)); }
.type-row:last-child { border-bottom: 1px solid; border-color: var(--lw-border, var(--lw-canvas-tint)); }
.type-params { padding: 14px 22px 14px 0; display: grid; gap: 8px; }
.type-params .mono { font: 11.5px/1.3 var(--n-mono); color: var(--lw-text-heading, var(--lw-text-primary)); cursor: copy; }
.type-params dl { margin: 0; display: flex; flex-wrap: wrap; gap: 2px 14px; font: 10.5px/1.4 var(--n-mono); }
.type-params dt { color: var(--lw-text-muted, var(--lw-text-body)); } .type-params dd { margin: 0; color: var(--lw-text-heading, var(--lw-text-primary)); }
.type-params .tag-obs { justify-self: start; }
.type-specimen { padding: 12px 0; overflow: hidden; }
.type-specimen .spec { display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.08;
  color: var(--lw-text-heading, var(--lw-text-primary)); }

/* ---------------------------------------------------------------- 03 components */
.lp-comp-grid { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr); gap: 22px; align-items: start; }
.btn-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.ds-btn { font: inherit; font-size: var(--lw-type-ui); font-weight: var(--lw-weight-ui-strong, 500); line-height: 1.2;
  padding: 12px 22px; border-radius: var(--lw-radius-control); border: 1px solid; border-color: transparent;
  cursor: pointer; }
.ds-btn--primary { background: var(--lw-action-bg); color: var(--lw-action-fg); }
.ds-btn--primary:hover { background: var(--lw-action-bg-alt, var(--lw-action-bg)); }
.ds-btn--primary.is-hover { background: var(--lw-action-bg-alt, var(--lw-action-bg)); }
.ds-btn--primary.is-active { transform: translateY(1px); filter: brightness(.94); }
.ds-btn--primary:disabled { opacity: .45; cursor: not-allowed; }
.ds-btn--secondary { background: transparent; color: var(--lw-text-heading, var(--lw-text-primary)); border-color: var(--lw-action-bg); }
.ds-btn--secondary:hover { background: color-mix(in srgb, var(--lw-action-bg) 8%, transparent); }
.ds-btn--secondary.is-hover { background: color-mix(in srgb, var(--lw-action-bg) 8%, transparent); }
.ds-btn--ghost { background: transparent; color: var(--lw-text-muted, var(--lw-text-body)); border-color: var(--lw-border, transparent); }
.ds-btn:focus-visible { outline: 3px solid color-mix(in srgb, var(--lw-action-bg) 60%, transparent); outline-offset: 2px; }
.ds-btn--primary.is-focus { outline: 3px solid color-mix(in srgb, var(--lw-action-bg) 60%, transparent); outline-offset: 2px; }
.state-row { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
.lp-form .cap { font: 500 10.5px/1 var(--n-mono); letter-spacing: .08em; text-transform: uppercase;
  color: var(--lw-text-muted, var(--lw-text-body)); }
.state-chip { font: 10.5px/1 var(--n-mono); letter-spacing: .05em; color: var(--lw-text-muted, var(--lw-text-body));
  padding: 5px 8px; border-radius: 4px; border: 1px dashed; border-color: var(--lw-border, transparent); cursor: pointer; background: transparent; }
.state-chip[aria-pressed="true"] { border-style: solid; color: var(--lw-text-heading, var(--lw-text-primary)); }
.ds-field { display: grid; gap: 6px; font-size: var(--lw-type-body); color: var(--lw-text-muted, var(--lw-text-body)); }
.ds-input { font: inherit; font-size: var(--lw-type-ui); padding: 11px 14px; border-radius: var(--lw-radius-control);
  background: var(--lw-canvas); color: var(--lw-text-heading, var(--lw-text-primary)); border: 1px solid;
  border-color: var(--lw-border-strong, var(--lw-border)); width: 100%; }
.ds-input::placeholder { color: var(--lw-text-muted, var(--lw-text-body)); opacity: .7; }
.ds-input:focus { outline: 2px solid var(--lw-action-bg); outline-offset: 1px; }
.ds-input.is-invalid { border-color: var(--lw-trend-down, var(--lw-action-bg)); }
.field-note { font-size: var(--lw-type-caption, 11px); color: var(--lw-text-muted, var(--lw-text-body)); }
.field-note.bad { color: var(--lw-trend-down, var(--lw-action-bg)); }
.pricing { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; align-items: start; }
.tier { padding: 20px 18px; border-radius: var(--lw-radius-card, 12px); border: 1px solid;
  border-color: var(--lw-border, var(--lw-canvas-tint)); background: var(--lw-surface, var(--lw-canvas)); display: grid; gap: 10px; align-content: start; }
.tier.featured { background: var(--lw-text-heading, var(--lw-text-primary)); color: var(--lw-canvas); border-color: var(--lw-text-heading, var(--lw-text-primary)); }
.tier .kind { font: 500 10.5px/1 var(--n-mono); letter-spacing: .08em; text-transform: uppercase;
  color: var(--lw-text-muted, var(--lw-text-body)); }
.tier.featured .kind { color: color-mix(in srgb, var(--lw-canvas) 80%, transparent); }
.tier .price { font-size: var(--lw-type-h3); line-height: 1.05; letter-spacing: var(--lw-tracking-h2, normal);
  color: inherit; font-variant-numeric: tabular-nums; }
.tier .price small { font-size: var(--lw-type-caption, 11px); font-family: var(--n-mono); letter-spacing: 0;
  color: var(--lw-text-muted, var(--lw-text-body)); margin-left: 6px; }
.tier.featured .price small { color: color-mix(in srgb, var(--lw-canvas) 80%, transparent); }
.tier .note { font-size: var(--lw-type-body); line-height: var(--lw-leading-prose, 1.45); color: inherit; opacity: .82; }
.tier .ds-btn { margin-top: 6px; justify-self: start; }
.tier.featured .ds-btn--primary { background: var(--lw-canvas); color: var(--lw-text-heading, var(--lw-text-primary)); }
.lp-card-surfaces { display: grid; gap: 10px; margin-top: 18px; }
.ds-card { padding: 16px 18px; border-radius: var(--lw-radius-card, 12px); background: var(--lw-surface, var(--lw-canvas)); border: 1px solid; border-color: var(--lw-border, transparent); }
.ds-card--tint { background: var(--lw-well, var(--lw-surface)); }
.ds-card--float { background: var(--lw-canvas); box-shadow: var(--lw-depth-float, none); }
.lp-figcaption { margin: 10px 0 0; font: 10.5px/1.5 var(--n-mono); color: var(--lw-text-muted, var(--lw-text-body)); }
.lp-comp-grid .col { display: grid; gap: 26px; align-content: start; }
.lp-comp-grid .block { display: grid; gap: 12px; }
.lp-comp-grid .block > .cap { display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 4px 14px;
  font: 500 10.5px/1.4 var(--n-mono); letter-spacing: .08em; text-transform: uppercase; color: var(--lw-text-heading, var(--lw-text-primary)); }
.lp-comp-grid .block > .cap > span { white-space: nowrap; }
.lp-tbl { border-radius: 8px; overflow: hidden; border: 1px solid; border-color: var(--lw-border, transparent); }
.lp-tbl table { width: 100%; border-collapse: collapse; font-size: var(--lw-type-ui); }
.lp-tbl th { text-align: left; padding: 9px 12px; font: 500 10.5px/1 var(--n-mono); letter-spacing: .06em;
  text-transform: uppercase; color: var(--lw-text-muted, var(--lw-text-body)); background: var(--lw-well, var(--lw-surface)); }
.lp-tbl td { padding: 10px 12px; border-top: 1px solid; border-color: var(--lw-border, transparent); color: var(--lw-text-heading, var(--lw-text-primary)); font-variant-numeric: tabular-nums; }
.lp-tbl td[data-trend] { text-align: right; font: 500 12px/1 var(--n-mono); }
.lp-tbl td[data-trend="up"] { color: var(--lw-trend-up, inherit); }
.lp-tbl td[data-trend="down"] { color: var(--lw-trend-down, inherit); }
.lp-form { padding: 18px; border-radius: var(--lw-radius-card, 12px); border: 1px solid; border-color: var(--lw-border, transparent);
  background: var(--lw-surface, var(--lw-canvas)); display: grid; gap: 14px; }

/* ---------------------------------------------------------------- 04 motion & guardrails */
.lp-motion { display: grid; gap: 0; }
.motion { display: grid; grid-template-columns: 190px minmax(0, 1fr) 190px; gap: 0; align-items: center;
  border-top: 1px solid; border-color: var(--lw-border, var(--lw-canvas-tint)); }
.motion:last-child { border-bottom: 1px solid; border-color: var(--lw-border, var(--lw-canvas-tint)); }
.motion .plot { padding: 12px 20px 12px 0; display: flex; }
.motion .plot .bezier { --st-dash: currentColor; }
[data-backdrop="action"].lp-sec .motion .plot .bezier .curve { stroke: var(--bd-fg); }
[data-backdrop="action"].lp-sec .motion .plot .bezier .hn { fill: var(--bd-bg); stroke: var(--bd-fg); }
[data-backdrop="action"].lp-sec .motion .plot .bezier .bg line { stroke: var(--bd-fg); opacity: .18; }
[data-backdrop="action"].lp-sec .motion .plot .bezier .hz { stroke: var(--bd-fg); opacity: .4; }
.motion .plot .bezier .curve { stroke: var(--lw-text-heading, currentColor); }
.motion .plot .bezier .bg line { stroke: var(--lw-border, currentColor); opacity: .6; }
.motion .plot .bezier .hz { stroke: var(--lw-border-strong, currentColor); opacity: .7; }
.motion .plot .bezier .hn, .motion .plot .bezier .end { fill: var(--lw-canvas); stroke: var(--lw-text-heading, currentColor); }
.motion .mid { padding: 12px 20px; display: grid; gap: 8px; }
.motion .mid .mono { font: 11.5px/1.3 var(--n-mono); color: var(--lw-text-heading, var(--lw-text-primary)); word-break: break-all; }
.motion .act { padding: 12px 0; display: grid; gap: 8px; justify-items: end; justify-content: end; }
.motion .spec-val { font: 11px/1.45 var(--n-mono); color: var(--lw-text-muted, var(--lw-text-body)); word-break: break-all; }
.rows { display: grid; gap: 5px; }
.rows .row { display: flex; justify-content: space-between; gap: 12px; align-items: baseline; font: 10.5px/1.45 var(--n-mono);
  color: var(--lw-text-muted, var(--lw-text-body)); }
.rows .row b { color: var(--lw-text-heading, var(--lw-text-primary)); font-weight: 500; text-align: right; flex: 0 1 auto; min-width: 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.rows { min-width: 0; }
.motion .act label { font: 10px/1 var(--n-mono); letter-spacing: .08em; text-transform: uppercase; color: var(--lw-text-muted, var(--lw-text-body)); }
.motion-range { width: 150px; accent-color: var(--lw-action-bg); cursor: pointer; }
.motion .act .tp-btn { color: var(--lw-text-heading, var(--lw-text-primary)); border-color: var(--lw-border-strong, var(--lw-border)); }
.track { height: 3px; border-radius: 2px; background: var(--lw-border, var(--lw-canvas-tint)); position: relative; }
.track .dot { position: absolute; top: -5px; left: 0; width: 13px; height: 13px; border-radius: 50%;
  background: var(--lw-action-bg); border: 1px solid var(--lw-canvas); }
.lp-motion-legend { margin: 14px 0 40px; font: 10.5px/1.6 var(--n-mono); color: var(--lw-text-muted, var(--lw-text-body)); }

.gate-list { display: grid; gap: 20px; }
.gate-head { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; margin-bottom: 8px; }
.gate-head span:first-child { font-size: var(--lw-type-body); color: var(--lw-text-heading, var(--lw-text-primary)); }
.gate-head .mono { font: 10px/1.4 var(--n-mono); color: var(--lw-text-muted, var(--lw-text-body)); }
.gate-item .cap { margin-bottom: 8px; font: 500 10.5px/1.4 var(--n-mono); letter-spacing: .06em;
  text-transform: uppercase; color: var(--lw-text-muted, var(--lw-text-body)); }
.gates { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.gate { padding: 10px 12px; border-radius: 6px; border: 1px solid; font-size: var(--lw-type-body);
  border-color: var(--lw-border, var(--lw-canvas-tint)); color: var(--lw-text-body, var(--lw-text-primary)); }
.gate code { font-family: var(--n-mono); font-size: 11px; }
.gate.forbid { border-left: 3px solid var(--lw-trend-down, currentColor); }
.gate.max { border-left: 3px solid var(--lw-brand, var(--lw-action-bg)); }
.gate.require { border-left: 3px solid var(--lw-trend-up, currentColor); }
.gate.note { border-left: 3px solid var(--lw-text-muted, currentColor); font-size: var(--lw-type-caption, 11px); }
.gate details summary { cursor: pointer; list-style: none; }
.gate details summary::marker { content: ""; }
.gate details summary::after { content: " ▾"; color: var(--lw-text-muted, currentColor); }
.gate details[open] summary::after { content: " ▴"; }
.regex { margin: 8px 0 0; padding: 8px 10px; list-style: none; border-radius: 4px; background: var(--lw-well, rgba(0,0,0,.05));
  font: 11px/1.7 var(--n-mono); overflow-wrap: anywhere; }
.lp-taste { display: grid; gap: 16px; }
.tcard { padding: 18px 20px; border-radius: var(--lw-radius-card, 10px); border: 1px solid;
  border-color: var(--lw-border, var(--lw-canvas-tint)); background: var(--lw-surface, var(--lw-canvas)); display: grid; gap: 12px; }
.tcard .head { display: flex; align-items: center; flex-wrap: wrap; gap: 8px;
  font: 10.5px/1 var(--n-mono); letter-spacing: .05em; color: var(--lw-text-muted, var(--lw-text-body)); }
.tcard h4 { margin: 0; font-size: var(--lw-type-title, var(--lw-type-ui)); color: var(--lw-text-heading, var(--lw-text-primary)); font-weight: inherit; }
.tcard .ab { display: grid; grid-template-columns: 1fr auto 1fr; gap: 10px; align-items: center; font-size: var(--lw-type-body); }
.tcard .ab .v { padding: 9px 12px; border-radius: 6px; border: 1px solid; border-color: var(--lw-border, transparent); color: var(--lw-text-heading, inherit); }
.tcard .ab .over { color: var(--lw-text-muted, inherit); text-decoration: line-through; }
.tcard .ab .vs { font: 10px/1 var(--n-mono); color: var(--lw-text-muted, inherit); }
.tcard .why { margin: 0; font-size: var(--lw-type-body); color: var(--lw-text-muted, var(--lw-text-body)); line-height: var(--lw-leading-prose, 1.5); }
.sec-col { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 40px; align-items: start; }
.sec-col > div { display: grid; gap: 10px; }
.sec-col > div > .cap { font: 500 11px/1 var(--n-mono); letter-spacing: .08em; text-transform: uppercase; color: var(--lw-text-heading, var(--lw-text-primary)); }

/* ---------------------------------------------------------------- 05 clipped bricks */
.lp-bricks { display: grid; gap: 22px; }
.brick-card { border-radius: var(--lw-radius-card, 12px); border: 1px solid; border-color: var(--lw-border, var(--lw-canvas-tint));
  overflow: hidden; background: var(--lw-surface, var(--lw-canvas)); }
.brick-card .bh { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: baseline; padding: 14px 18px;
  border-bottom: 1px solid; border-color: var(--lw-border, var(--lw-canvas-tint)); font: 11px/1.4 var(--n-mono);
  color: var(--lw-text-muted, var(--lw-text-body)); }
.brick-card .bh .name { font: 500 13px/1.2 var(--n-mono); color: var(--lw-text-heading, var(--lw-text-primary)); }
.brick-live { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 1px; background: var(--lw-border, var(--lw-canvas-tint)); }
.brick-stage { padding: 34px 28px; background: var(--lw-canvas); display: grid; gap: 18px; align-content: center; }
.brick-stage .cap { font: 10.5px/1 var(--n-mono); letter-spacing: .08em; text-transform: uppercase; color: var(--lw-text-muted, var(--lw-text-body)); }
.brick-shots { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; padding: 12px; background: var(--lw-canvas); }
.brick-shots figure { margin: 0; display: grid; gap: 6px; }
.brick-shots img { width: 100%; border-radius: 6px; border: 1px solid; border-color: var(--lw-border, var(--lw-canvas-tint)); display: block; }
.brick-shots .trim { position: relative; aspect-ratio: 1440 / 620; overflow: hidden; border-radius: 6px;
  border: 1px solid var(--lw-border, var(--lw-canvas-tint)); background: var(--lw-canvas); }
.brick-shots .trim img { position: absolute; left: 0; top: 0; width: 100%; transform: translateY(calc(-1 * var(--crop-y, 0%))); }
.brick-shots .trim::after { content: ""; position: absolute; inset: 0; border-radius: 6px;
  outline: 2px solid var(--lw-accent, var(--lw-action-bg)); outline-offset: -2px; pointer-events: none; }
.brick-shots figcaption { font: 10px/1.4 var(--n-mono); color: var(--lw-text-muted, var(--lw-text-body)); text-transform: uppercase; letter-spacing: .05em; }
.brick-meta { padding: 18px 20px; display: grid; gap: 12px; align-content: start; background: var(--lw-well, var(--lw-surface)); min-width: 0; }
.brick-meta > .cap { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.brick-meta .row { display: flex; justify-content: space-between; gap: 10px; font: 11px/1.4 var(--n-mono); color: var(--lw-text-body, var(--lw-text-primary)); }
.brick-meta .row b { color: var(--lw-text-heading, var(--lw-text-primary)); font-weight: 500; }
.brick-meta .nodes { display: grid; gap: 6px; font: 10.5px/1.45 var(--n-mono); color: var(--lw-text-muted, var(--lw-text-body)); }
.brick-meta .verdict { padding: 8px 10px; border-radius: 6px; border: 1px solid; border-color: var(--lw-border, transparent);
  font: 11px/1.4 var(--n-mono); color: var(--lw-text-heading, var(--lw-text-primary)); }
.brick-meta .verdict.bad { border-left: 3px solid var(--lw-trend-down, currentColor); }
.brick-meta .verdict.ok { border-left: 3px solid var(--lw-trend-up, currentColor); }
.brick-meta .verdict.manual { border-left: 3px solid var(--lw-brand, var(--lw-action-bg)); }
.brick-cta-row { display: grid; justify-items: start; padding: 6px 0 4px; }
.brick-cta { font: inherit; font-size: var(--lw-type-ui); font-weight: var(--lw-weight-ui-strong, 600); line-height: 1.2;
  padding: 12px 24px; border-radius: var(--brick-radius, var(--lw-radius-control)); border: 1px solid;
  border-color: var(--lw-border, transparent); background: var(--brick-bg); color: var(--brick-fg);
  position: relative; overflow: hidden; cursor: pointer; isolation: isolate; }
.brick-cta::before { content: ""; position: absolute; inset: 0; z-index: -1; transform: translateY(110%) skew(-15deg);
  background: var(--lw-brand, var(--lw-action-bg-alt, var(--lw-action-bg))); transition: var(--brick-transition); }
.brick-cta:hover::before, .brick-cta:focus-visible::before { transform: translateY(0) skew(-15deg); }
body[data-stress~="reduced"] .brick-cta::before { transition: none !important; transform: translateY(0) skew(-15deg); }
.brick-cta:focus-visible { outline: 2px solid var(--lw-action-bg); outline-offset: 3px; }
.brick-shots .cap-row { display: none; }
.brick-card .bh + .brick-live .cap, .brick-stage > .cap, .brick-meta > .cap {
  font: 500 10.5px/1.4 var(--n-mono); letter-spacing: .08em; text-transform: uppercase;
  color: var(--lw-text-muted, var(--lw-text-body)); display: flex; justify-content: space-between; gap: 10px; align-items: center; }
.brick-meta .mono-line { font: 10.5px/1.55 var(--n-mono); color: var(--lw-text-muted, var(--lw-text-body)); overflow-wrap: anywhere; }
.provenance { margin: 0; padding: 14px 18px; border-radius: 10px; border: 1px dashed; border-color: var(--lw-border-strong, var(--lw-border));
  font: 11.5px/1.6 var(--n-mono); color: var(--lw-text-muted, var(--lw-text-body)); }

/* ---------------------------------------------------------------- Specs view */
.sp-wrap { max-width: var(--sp-max); margin: 0 auto; padding: 30px 28px 110px; display: grid; gap: 1px; }
.sp-panel { padding: 34px 0 44px; border-bottom: 1px solid var(--n-line); }
.sp-panel:last-child { border-bottom: 0; }
.sp-panel h1 { font-size: 30px; font-weight: 400; letter-spacing: -.02em; margin: 0 0 10px; color: var(--n-ink); }
.sp-panel h2 { font-size: 12px; font-weight: 500; letter-spacing: .08em; text-transform: uppercase;
  margin: 34px 0 8px; color: var(--n-ink); }
.sp-panel h3 { font-size: 11.5px; font-weight: 500; letter-spacing: .05em; text-transform: uppercase; color: var(--n-mute); margin: 24px 0 10px; }
.sp-panel p, .sp-panel li { color: var(--n-mute); font-size: 13px; }
.sp-panel .lede { margin: 0 0 18px; max-width: 74ch; }
.sp-panel .note { border-left: 2px solid var(--n-ink); padding: 10px 14px; background: var(--n-hover);
  color: var(--n-mute); font-size: 13px; margin: 14px 0; max-width: 76ch; }
.sp-ledger { display: flex; flex-wrap: wrap; gap: 6px 14px; margin: -6px 0 18px; }
.sp-sec-head { display: flex; align-items: baseline; gap: 12px; }
.sp-sec-head h2 { margin-bottom: 14px; }
.sp-stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1px; margin: 0 0 8px;
  border: 1px solid var(--n-line); background: var(--n-line); }
.sp-stat { background: var(--n-bg); padding: 16px 18px; display: grid; gap: 6px; }
.sp-stat .v { font-size: 26px; letter-spacing: -.02em; color: var(--n-ink); }
.sp-stat .k { font: 10.5px/1 var(--n-mono); letter-spacing: .06em; text-transform: uppercase; color: var(--n-faint); }
.sp-stat .d { font-size: 12px; color: var(--n-mute); }
.gates-flat { margin: 12px 0; display: grid; gap: 8px; }
.gates-flat .gate { border: 1px solid var(--n-line); border-radius: 4px; padding: 9px 12px; font-size: 12.5px; color: var(--n-ink); }
.sp-panel table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.sp-panel th { text-align: left; font: 500 10.5px/1.2 var(--n-mono); letter-spacing: .06em; text-transform: uppercase;
  color: var(--n-mute); padding: 0 14px 8px 0; border-bottom: 1px solid var(--n-line-strong); }
.sp-panel td { padding: 9px 14px 9px 0; border-bottom: 1px solid var(--n-line); vertical-align: top; color: var(--n-ink); }
.sp-panel tr:hover td { background: var(--n-hover); }
.sp-panel code, .sp-panel .mono { font-family: var(--n-mono); font-size: 11.5px; font-variant-numeric: tabular-nums; }
.tbl { overflow-x: auto; }
.tbl table { min-width: 640px; }
.badge { font: 500 10.5px/1 var(--n-mono); letter-spacing: .05em; text-transform: uppercase; padding: 3px 6px;
  border-radius: 3px; border: 1px solid var(--n-line-strong); color: var(--n-mute); }
.badge.observed { color: var(--n-ok); border-color: color-mix(in srgb, var(--n-ok) 45%, transparent); }
.badge.inferred { color: var(--n-warn); border-color: color-mix(in srgb, var(--n-warn) 45%, transparent); }
.badge.unverified, .badge.unknown { color: var(--n-bad); border-color: color-mix(in srgb, var(--n-bad) 45%, transparent); }
.dl { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 6px; }
.code { border: 1px solid var(--n-line); border-radius: 4px; background: var(--n-panel); margin-top: 10px; }
.code-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 8px 12px;
  border-bottom: 1px solid var(--n-line); font: 500 11px/1 var(--n-mono); letter-spacing: .06em;
  text-transform: uppercase; color: var(--n-mute); }
.code pre { margin: 0; padding: 14px 16px; overflow: auto; max-height: 280px; font: 11.5px/1.65 var(--n-mono);
  color: var(--n-ink); white-space: pre; }
.compare { position: relative; border: 1px solid var(--n-line); overflow: hidden; background: var(--n-panel); }
.compare img { display: block; width: 100%; }
.compare .layer.b { position: absolute; inset: 0; clip-path: inset(0 50% 0 0); }
.compare .handle { position: absolute; top: 0; bottom: 0; left: 50%; width: 1px; background: var(--n-ink); pointer-events: none; }
.compare .handle::after { content: ""; position: absolute; top: 50%; left: 50%; width: 26px; height: 26px;
  margin: -13px 0 0 -13px; border-radius: 50%; border: 1px solid var(--n-ink); background: var(--n-bg); }
.compare input[type=range] { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; cursor: ew-resize; margin: 0; }
.compare .lab { position: absolute; bottom: 10px; font: 10px/1 var(--n-mono); letter-spacing: .06em; text-transform: uppercase;
  background: var(--n-bg); color: var(--n-mute); padding: 5px 7px; border: 1px solid var(--n-line-strong); }
.compare .lab.l { left: 10px; } .compare .lab.r { right: 10px; }
.fid { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 1px; align-items: start;
  background: var(--n-line); border: 1px solid var(--n-line); }
.fid > * { background: var(--n-bg); }
.src-shot { overflow: hidden; } .src-shot img { display: block; width: 100%; }
.fid-note { padding: 18px 20px; display: grid; gap: 10px; align-content: start; }
.fid-note h3 { margin: 0; }
.deviations { display: grid; gap: 1px; border: 1px solid var(--n-line); background: var(--n-line); }
.deviation { background: var(--n-bg); padding: 12px 14px; font-size: 12.5px; color: var(--n-mute); }
.deviation strong { display: block; color: var(--n-ink); font: 500 11px/1.4 var(--n-mono); letter-spacing: .02em; }
.sbs { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: var(--n-line); border: 1px solid var(--n-line); }
.sbs figure { margin: 0; background: var(--n-panel); padding: 12px; }
.sbs img { width: 100%; display: block; }
.sbs figcaption { font: 10.5px/1.4 var(--n-mono); color: var(--n-mute); margin-top: 8px; }

/* ---------------------------------------------------------------- stress: the same booleans in both views */
body[data-stress~="long"] .lp-scroll { max-width: 46ch; margin: 0 auto; }
body[data-stress~="long"] .sp-wrap { max-width: 620px; }
body[data-stress~="long"] .sp-wrap .tbl table { min-width: 0; }
body[data-stress~="reduced"] .lp-scroll *, body[data-stress~="reduced"] .lp-scroll *::before, body[data-stress~="reduced"] .lp-scroll *::after {
  transition-duration: .001ms !important; animation-duration: .001ms !important; animation-delay: 0s !important; }
/* the narrow frame: the site, rebuilt at 390 — the site's own mobile rules apply, not a squeezed desktop */
body[data-stress~="narrow"] .lp-scroll { max-width: 390px; margin: 0 auto; }
body[data-stress~="narrow"] .lp-nav-links, body[data-stress~="narrow"] .lp-hero .hero-before { display: none; }
body[data-stress~="narrow"] .lp-nav { padding: 12px 16px; gap: 10px; }
body[data-stress~="narrow"] .lp-nav-cta { margin-left: auto; padding: 7px 12px; }
body[data-stress~="narrow"] .lp-hero h1 { font-size: var(--lw-type-display-lg, 44px); }
body[data-stress~="narrow"] .lp-hero { padding: 24px 20px 32px; }
body[data-stress~="narrow"] .stat-strip { grid-template-columns: 1fr 1fr; }
body[data-stress~="narrow"] .lp-hero, body[data-stress~="narrow"] .lp-comp-grid, body[data-stress~="narrow"] .sec-col,
body[data-stress~="narrow"] .brick-live { grid-template-columns: 1fr; }
body[data-stress~="narrow"] .lp-sec, body[data-stress~="narrow"] .lp-hero { padding-left: 24px; padding-right: 24px; }
body[data-stress~="narrow"] .type-row { grid-template-columns: 1fr; }
body[data-stress~="narrow"] .sw { grid-template-columns: 1fr 1fr; }
body[data-stress~="narrow"] .motion { grid-template-columns: 1fr; }
body[data-stress~="narrow"] .sp-wrap { max-width: 420px; padding-left: 18px; padding-right: 18px; }

@media (max-width: 1080px) {
  .tb-meta { display: none; }
  .lp-hero { grid-template-columns: 1fr; gap: 36px; }
  .graphic { min-height: 0; max-width: 520px; }
  .lp-comp-grid, .sec-col, .brick-live { grid-template-columns: 1fr; }
  .sp-wrap { padding-left: 20px; padding-right: 20px; }
  .motion { grid-template-columns: 1fr; }
  .brick-shots { grid-template-columns: 1fr; }
}
@media (max-width: 860px) {
  .topbar { flex-wrap: wrap; gap: 8px; padding: 10px 14px; }
  .tb-left .fpl { display: none; }
  .tp-btn { padding: 6px 7px; font-size: 10px; }
  .lp-frame { width: calc(100% - 16px); }
  .tb-center { order: 3; width: 100%; }
  .tb-seg { width: 100%; }
  .tp-seg { flex: 1; }
  .tb-status { display: none; }
  .lp-sec { padding: 44px 24px 52px; }
  .lp-hero { padding: 30px 24px 52px; }

  .lp-frame { width: calc(100% - 20px); }
  .type-row { grid-template-columns: 1fr; }
  .fid, .sbs { grid-template-columns: 1fr; }
}
@media print {
  .topbar, .lp-dock { display: none; }
  #view-specs { display: block !important; }
}
"""


JS = r"""
// lewitt system/ — dual view, stress booleans, Observed evidence cards, motion scrubbers, copy.
(function () {
  var body = document.body;
  var STATUS = document.getElementById('tb-status');
  function say(t) { if (STATUS) STATUS.textContent = t || ''; }

  // ---------------------------------------------------------------- view: live | specs (#hash keeps it)
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.tb-seg [role="tab"]'));
  var views = { live: document.getElementById('view-live'), specs: document.getElementById('view-specs') };
  function setView(name, remember) {
    if (!views[name]) name = 'live';
    body.dataset.view = name;
    tabs.forEach(function (t) {
      var on = t.getAttribute('aria-controls') === 'view-' + name;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
    });
    views.live.hidden = name !== 'live';
    views.specs.hidden = name !== 'specs';
    if (remember) {
      var h = '#' + name;
      if (location.hash !== h) history.replaceState(null, '', h);
    }
  }
  function hashView() { var h = location.hash.replace('#', ''); return h === 'specs' ? 'specs' : null; }
  tabs.forEach(function (t, i) {
    t.addEventListener('click', function () {
      setView(t.getAttribute('aria-controls').replace('view-', ''), true);
      location.hash = (t.getAttribute('aria-controls') === 'view-live') ? '' : 'specs';
      if (t.getAttribute('aria-controls') === 'view-live') history.replaceState(null, '', location.pathname + '#live');
    });
    t.addEventListener('keydown', function (e) {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      e.preventDefault();
      var next = e.key === 'ArrowRight' ? (i + 1) % tabs.length : (i - 1 + tabs.length) % tabs.length;
      tabs[next].click(); tabs[next].focus();
    });
  });
  setView(hashView() || 'live', false);

  // ---------------------------------------------------------------- stress: three booleans, both views
  var stress = {};
  var stressBtn = document.getElementById('stress-btn');
  var stressMenu = document.getElementById('stress-menu');
  function setMenu(open) {
    if (!stressMenu || !stressBtn) return;
    stressMenu.hidden = !open;
    stressBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  if (stressBtn) stressBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    setMenu(stressMenu.hidden);
  });
  document.addEventListener('click', function (e) {
    if (stressMenu && !stressMenu.hidden && !stressMenu.contains(e.target) && e.target !== stressBtn) setMenu(false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { setMenu(false); if (stressBtn) stressBtn.focus(); }
  });
  function applyStress() {
    var on = Object.keys(stress).filter(function (k) { return stress[k]; });
    body.dataset.stress = on.join(' ');
    if (stressBtn) {
      stressBtn.classList.toggle('has-on', on.length > 0);
      stressBtn.firstChild.textContent = on.length ? 'Stress · ' + on.length : 'Stress ';
    }
    say(on.length ? on.join(' + ') : '');
    var slowInput = document.getElementById('p-slow');
    if (on.indexOf('reduced') > -1 && slowInput && +slowInput.value !== 1) {
      slowInput.value = 1; slowInput.dispatchEvent(new Event('input'));
    }
  }
  Array.prototype.forEach.call(document.querySelectorAll('[data-stress-toggle]'), function (btn) {
    btn.addEventListener('click', function () {
      var k = btn.getAttribute('data-stress-toggle');
      stress[k] = !stress[k];
      btn.setAttribute('aria-pressed', stress[k] ? 'true' : 'false');
      applyStress();
    });
  });
  // honour the OS preference on load as a starting state, never overriding a user click
  var mq = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (mq.matches) {
    stress.reduced = true;
    var rb = document.querySelector('[data-stress-toggle="reduced"]');
    if (rb) rb.setAttribute('aria-pressed', 'true');
    applyStress();
  }

  // ---------------------------------------------------------------- Observed evidence cards
  var EV = (function () { try { return JSON.parse(document.getElementById('evidence-data').textContent); } catch (e) { return {}; } })();
  var evCard = document.getElementById('lp-ev');
  var OPEN = -1;   // evCard / OPEN: unique names — an IIFE-wide var would be shadowed by a later one
  document.addEventListener('click', function (e) {
    var tag = e.target.closest('[data-obs]');
    if (!tag) return;
    var ms = Array.prototype.slice.call(document.querySelectorAll('[data-obs="' + tag.getAttribute('data-obs') + '"]'));
    OPEN = ms.indexOf(tag);
    var tagCard = evCard;
    if (!tagCard) return;
    var pack = EV[tag.getAttribute('data-obs')] || {}, ev = pack.primary || {};
    var rows = Object.keys(ev.values || {}).map(function (k) {
      return '<dt>' + esc(k) + '</dt><dd>' + esc(String(ev.values[k])) + '</dd>';
    }).join('');
    tagCard.innerHTML =
      '<div class="ev-head"><span>observed · measured in the browser</span>' +
      '<button class="ev-x" aria-label="close evidence">close</button></div>' +
      '<div class="ev-id">' + esc(ev.id || 'no evidence id') + '</div>' +
      '<div class="ev-loc">' + esc(ev.locator || '') + '</div>' +
      '<dl>' + rows +
      (ev.method ? '<dt>method</dt><dd>' + esc(ev.method) + '</dd>' : '') +
      (ev.url ? '<dt>page</dt><dd>' + esc(ev.url.replace('https://', '')) + '</dd>' : '') + '</dl>' +
      (pack.also && pack.also.length ? '<div class="ev-again">with: ' + pack.also.map(esc).join(' · ') + '</div>' : '');
    var r = tag.getBoundingClientRect();
    tagCard.setAttribute('data-open', '');
    var w = tagCard.offsetWidth, h = tagCard.offsetHeight;
    tagCard.style.left = Math.max(10, Math.min(window.innerWidth - w - 10, r.left + r.width / 2)) + 'px';
    tagCard.style.top = Math.max(70, r.bottom + 8) + 'px';
  });
  document.addEventListener('click', function (e) {
    if (!evCard) return;
    if (!e.target.closest('.lp-ev') && !e.target.closest('[data-obs]')) evCard.removeAttribute('data-open');
  });
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

  // ---------------------------------------------------------------- legacy panel router (kept for older runs)
  var PANELS = Array.prototype.map.call(document.querySelectorAll('.sp-panel'), function (p) { return p.id; });

  // ---------------------------------------------------------------- motion: replay + scrub
  var slow = 1;
  var slowEl = document.getElementById('p-slow');   // preview.html only; system/ has no speed slider
  if (slowEl) slowEl.addEventListener('input', function () {
    slow = parseFloat(slowEl.value) || 1;
    if (stress.reduced) { slow = 1; slowEl.value = 1; }
    say('replay ×' + slow);
  });
  function msFrom(d) { var m = /([0-9.]+)\s*(ms|s)/i.exec(String(d)); return m ? (m[2].toLowerCase() === 's' ? parseFloat(m[1]) * 1000 : parseFloat(m[1])) : 300; }
  var reduceMQ = mq;
  function reducedOn() { return stress.reduced || body.dataset.stress.indexOf('reduced') > -1; }
  Array.prototype.forEach.call(document.querySelectorAll('[data-sys-replay]'), function (btn) {
    var dot = document.getElementById(btn.getAttribute('data-sys-replay'));
    var range = document.getElementById(btn.getAttribute('data-sys-replay') + '-range');
    if (!dot) return;
    var dur = btn.getAttribute('data-dur'), ease = btn.getAttribute('data-ease');
    var run = function () {
      var ms = msFrom(dur) * slow;
      dot.style.transition = 'none'; dot.style.transform = 'translateX(0)'; void dot.offsetWidth;
      if (reducedOn()) { if (range) range.value = 1000; dot.style.transform = 'translateX(calc(100% - 13px))'; say('reduced · end state only'); return; }
      dot.style.transition = 'transform ' + ms + 'ms ' + ease;
      dot.style.transform = 'translateX(calc(100% - 13px))';
      if (range && range.dataset.sync) { range.value = 0; }
      say('replay ' + Math.round(ms) + 'ms');
    };
    btn.addEventListener('click', run);
    if (range) range.addEventListener('input', function () {
      var p = +range.value / 1000;
      dot.style.transition = 'none';
      dot.style.transform = 'translateX(' + (p * 100) + '% )'.replace('% )', '%)');
    });
  });

  // ---------------------------------------------------------------- 03 components: real state toggle + field
  Array.prototype.forEach.call(document.querySelectorAll('[data-state]'), function (chip) {
    chip.addEventListener('click', function () {
      var group = chip.getAttribute('data-state-group');
      Array.prototype.forEach.call(document.querySelectorAll('[data-state-group="' + group + '"]'), function (c) {
        c.setAttribute('aria-pressed', c === chip ? 'true' : 'false');
      });
      var btn = document.getElementById('demo-btn');
      if (btn) btn.className = 'ds-btn ds-btn--primary ' + chip.getAttribute('data-state');
    });
  });
  var field = document.getElementById('demo-email');
  if (field) {
    var fieldNote = document.getElementById('demo-email-note');
    var validate = function () {
      var bad = field.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(field.value);
      field.classList.toggle('is-invalid', !!bad);
      field.setAttribute('aria-invalid', bad ? 'true' : 'false');
      if (fieldNote) {
        fieldNote.textContent = bad ? (field.getAttribute('data-invalid') || 'Enter a valid address') : '';
        fieldNote.classList.toggle('bad', !!bad);
      }
    };
    field.addEventListener('input', validate); validate();
  }

  // ---------------------------------------------------------------- copy affordances
  function note(el, text) {
    var old = document.querySelector('.copied-note');
    if (old) old.remove();
    var r = el.getBoundingClientRect();
    var n = document.createElement('span');
    n.className = 'copied-note'; n.textContent = text || 'Copied';
    n.style.left = Math.round(r.left + r.width / 2) + 'px'; n.style.top = Math.round(r.top) + 'px';
    document.body.appendChild(n);
    window.setTimeout(function () { n.classList.add('out'); }, 1000);
    window.setTimeout(function () { n.remove(); }, 1400);
  }
  var themeBtn = document.getElementById('copy-theme');
  if (themeBtn) themeBtn.addEventListener('click', function () {
    var text = document.getElementById('theme-css').textContent;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        themeBtn.classList.add('ok'); themeBtn.textContent = 'Copied';
        window.setTimeout(function () { themeBtn.classList.remove('ok'); themeBtn.textContent = 'Copy shadcn-theme.css'; }, 1400);
      }, function () { note(themeBtn, 'Blocked'); });
    } else { note(themeBtn, 'Unavailable'); }
  });
  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-copy]');
    if (!el) return;
    e.preventDefault();
    var text = el.getAttribute('data-copy');
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { note(el); }, function () { note(el, 'Blocked'); });
    } else { note(el, 'Unavailable'); }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && evCard) evCard.removeAttribute('data-open');
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var el = e.target.closest('[data-copy][tabindex], [data-state], .tag-obs');
    if (!el) return;
    e.preventDefault();
    el.click();
  });

  // ---------------------------------------------------------------- fidelity split compare
  var range = document.getElementById('split');
  if (range) {
    var cmp = document.getElementById('compare');
    var apply = function () {
      var b = cmp.querySelector('.layer.b'), h = cmp.querySelector('.handle');
      if (b) b.style.clipPath = 'inset(0 ' + (100 - range.value) + '% 0 0)';
      if (h) h.style.left = range.value + '%';
    };
    range.addEventListener('input', apply); apply();
  }

  // ---------------------------------------------------------------- Specs: section links from the jump rail
  var specLinks = Array.prototype.slice.call(document.querySelectorAll('[data-spec-jump]'));
  specLinks.forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      setView('specs', false);
      history.replaceState(null, '', '#specs');
      var t = document.getElementById(a.getAttribute('data-spec-jump'));
      if (t) window.scrollTo({ top: t.getBoundingClientRect().top + window.scrollY - 70, behavior: 'smooth' });
    });
  });

  window.addEventListener('hashchange', function () {
    if (location.hash === '#specs') setView('specs', false);
    else if (location.hash === '#live') setView('live', false);
  });
})();
"""
