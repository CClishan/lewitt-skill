"""lewitt preview.html — the same dual-view long scroll as system/, delivered as one file.

preview.html has no system/ folder: its Live Preview and Specs views are assembled here from
dna.json alone, plus the clips/, capture/ and render files that sit beside it. visual_base and
site_render supply CSS and JS so both books look like one publication; the HTML is assembled in
this module so the file reduces to a single page a reviewer can open from any folder.
"""

from __future__ import annotations

import re

import build_artifacts as ba
import site_render as sr
import visual_base as vb

PREVIEW_CSS_PATCH = """
/* preview.html is one file: the render artifacts it references are listed once, in the Specs overview,
   not in the top bar (the top bar stays three groups). */
.papp { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 4px; }
.papp .mail { font: 500 10.5px/1 var(--n-mono); letter-spacing: .04em; padding: 6px 9px; border-radius: 4px;
  border: 1px solid var(--n-line-strong); color: var(--n-mute); text-decoration: none; }
.papp .mail:hover { color: var(--n-ink); border-color: var(--n-ink); }
"""


def render_preview_html(dna: dict, resolver=None, exists=None, root=None) -> str:
    """Single-file specimen book in two views: Live Preview (01-05) and Specs."""
    global resolve_tokens
    if resolver is not None:
        resolve_tokens = resolver
    meta = dna["meta"]
    modes = meta.get("modes") or ["default"]
    resolved = resolve_tokens(dna["tokens"], modes[0])
    canvas = next((resolved[t["id"]]["resolved"] for t in dna["tokens"] if t["id"] == "color/canvas"), None)
    tone = vb.tone_of(canvas)
    esc = sr._e
    read = sr.reads(resolved)
    text = sr.specimen_text(dna)
    bricks = ba.render_bricks(root) if root is not None else []
    pages = meta.get("crawl", {}).get("pages") or [meta["source"]]
    name = meta.get("name") or meta.get("domain") or "design system"

    def obs(kind: str, label: str = "+ Observed") -> str:
        return f'<button class="tag-obs" data-obs="{esc(kind)}">{esc(label)}</button>'

    # ---------------------------------------------------------------- 01 colour
    def swatches(layer: str) -> str:
        toks = [t for t in dna["tokens"] if t["type"] == "color" and t["layer"] == layer]
        if not toks:
            return ""
        cells = []
        for t in toks:
            v = resolved[t["id"]]["resolved"]
            ground, role = ba.colour_ground(t["id"], resolved)
            if role == "fill":
                chip, grade = "fill · solid", ""
            elif ground == v:
                chip, grade = "canvas · ground", ""
            else:
                label, grade = vb.wcag_badge(v, ground)
                chip = f"{role.replace('-', ' ')} · {label}"
            cells.append(
                f'<div class="swatch"><div class="fill" style="background:{esc(v)}"></div>'
                f'<div class="meta"><span class="tok" data-copy="var(--{esc(t["css"].lstrip("-"))})" role="button" tabindex="0">'
                f'{esc(t["id"])}</span><span class="hex" data-copy="{esc(v)}">{esc(v)}</span></div>'
                f'<div class="sub"><span class="wchip {grade}">{esc(chip)}</span></div></div>')
        return (f'<div class="lp-group"><h3><span>{esc(layer)}</span>'
                f'<span class="scene">{esc(_SCENE.get(layer, ""))} · {len(toks)}</span>'
                f'{obs("palette") if layer == "semantic" else ""}</h3><div class="sw">{"".join(cells)}</div></div>')

    prow = ""
    for label, fg_id, bg_id, where in _PAIRS:
        fg, bg = resolved.get(fg_id, {}).get("resolved"), resolved.get(bg_id, {}).get("resolved")
        if not fg or not bg:
            continue
        wcag, grade = vb.wcag_badge(fg, bg)
        prow += (f'<div class="prow"><div class="sample" style="background:{esc(bg)};color:{esc(fg)}">'
                 f'<span class="cap-label">{esc(label)}</span>Aa 0123 0123456789</div>'
                 f'<div class="pmeta"><span>{esc(where)}</span><span class="wchip {grade}">{esc(wcag)}</span></div></div>')
    live_colour = f"""
<div class="lp-sheet"><span class="lp-num">01</span><h2 class="lp-title">Colour Palette</h2>
<span class="rule"></span><span class="count">{len([t for t in dna['tokens'] if t['type'] == 'color'])} colours</span></div>
<p class="lp-lede">Roles first, primitives last. Ratios are computed from the two token values, not sampled from a
screenshot; a text colour is graded on the ground it actually sits on.</p>
<div class="lp-groups">{swatches("semantic")}{swatches("component")}{swatches("primitive")}</div>
<div class="pairs"><h3>Pairs in use</h3>{prow}</div>"""

    # ---------------------------------------------------------------- 02 type
    type_tokens = [t for t in dna["tokens"] if t["type"] == "dimension" and t["id"].startswith("type/")]
    scale_params = "".join(f'<span>{esc(t["id"].replace("type/", ""))} {esc(resolved[t["id"]]["resolved"])}</span>'
                           for t in type_tokens)
    face = next((str(resolved[t]["resolved"]).split(",")[0].strip('"\' ')
                 for t in ("font/body", "font/sans", "font/ui") if t in resolved), "the declared stack")
    live_type = f"""
<div class="lp-sheet"><span class="lp-num">02</span><h2 class="lp-title">Typography Scale</h2>
<span class="rule"></span><span class="count">{len(type_tokens)} steps</span></div>
<p class="lp-lede">The run's own headline set at every step, at real size, in {esc(face)} and its fallback stack;
the face itself is not shipped. Numeral steps show the run's first figure, text steps its headline.</p>
<div class="type-scale-params">{scale_params}</div>
{sr.type_rows(dna["tokens"], resolved, text, tag_prefix="1")}"""

    # ---------------------------------------------------------------- 03 components
    hero = text["hero"]
    cta = hero.get("primaryCta") or "Primary action"
    form = text["form"] or {}
    fields = form.get("fields") or []
    form_block = ""
    if fields:
        f0 = fields[0]
        title = f'<div class="cap">{esc(form["title"])}</div>' if form.get("title") else ""
        form_block = (f'<div class="block"><div class="cap"><span>Form field</span></div>'
                      f'<div class="lp-form">{title}'
                      f'<label class="ds-field"><span>{esc(f0["label"])}</span>'
                      f'<input class="ds-input" id="demo-email" type="email" placeholder="{esc(f0.get("placeholder", ""))}" '
                      f'data-invalid="{esc(f0.get("invalid", "Enter a valid value"))}" autocomplete="off">'
                      f'<span class="field-note" id="demo-email-note" aria-live="polite"></span></label>'
                      f'<div><button class="ds-btn ds-btn--primary" type="button">{esc(form.get("submit") or "Continue")}</button></div>'
                      f'</div></div>')
    floor = ba.shadow_floor(dna)
    float_line = ('<div class="ds-card ds-card--float">Float card · the run\'s float shadow, because no '
                  'restraint caps it.</div>' if (floor is None or floor >= 4) else
                  '<div class="ds-card">Shadow specimen withheld: this run\'s restraint caps box-shadow '
                  'below 4px, so depth is a hairline here.</div>')
    chips = "".join(
        f'<button class="state-chip" data-state="{cls}" data-state-group="btn" aria-pressed="'
        f'{"true" if cls == "" else "false"}">{esc(label)}{" · forced" if forced else ""}</button>'
        for label, cls, forced in (("default", "", False), ("hover", "is-hover", True),
                                   ("focus-visible", "is-focus", True), ("active", "is-active", True)))
    cards = text["cards"]
    tier_html = ""
    if cards:
        tier_html = '<div class="pricing">' + "".join(
            f'<div class="tier{" featured" if c.get("featured") else ""}"><span class="kind">{esc(c["title"])}</span>'
            f'<span class="price">{esc(c["price"])}'
            + (f'<small>{esc(c["per"])}</small>' if c.get("per") else "")
            + f'</span><span class="note">{esc(c["note"])}</span>'
            + (f'<button class="ds-btn ds-btn--primary" type="button">{esc(c.get("cta") or cta)}</button>'
               if c.get("cta") else "")
            + '</div>' for c in cards) + '</div>'
    table = text["table"]
    table_html = ""
    if table:
        trend = {j for j, c in enumerate(table["columns"]) if re.search(r"trend|change|24h|return|move", c, re.IGNORECASE)}
        rows = ""
        for row in table["rows"]:
            cells = ""
            for j, v in enumerate(row):
                sign = v.strip().startswith("-")
                if j in trend or (j == 2 and v.strip().endswith("%")):
                    cells += f'<td data-trend="{esc("down" if sign else "up")}">{esc(v)}</td>'
                else:
                    cells += f"<td>{esc(v)}</td>"
            rows += f"<tr>{cells}</tr>"
        table_html = (f'<div class="lp-tbl"><table><thead><tr>'
                      f'{"".join(f"<th>{esc(c)}</th>" for c in table["columns"])}</tr></thead>'
                      f'<tbody>{rows}</tbody></table></div>')
    live_components = f"""
<div class="lp-sheet"><span class="lp-num">03</span><h2 class="lp-title">Components &amp; Cards</h2>
<span class="rule"></span><span class="count">real states, not screenshots</span></div>
<p class="lp-lede">Controls read the run's action tokens. Click a state chip to force a state; hover and focus-visible
stay live.</p>
<div class="lp-comp-grid">
  <div class="col">
    <div class="block"><div class="cap"><span>Button</span>{obs("material")}</div>
      <div class="btn-row"><button class="ds-btn ds-btn--primary" id="demo-btn" type="button">{esc(cta)}</button>
      {f'<button class="ds-btn ds-btn--secondary" type="button">{esc(hero["secondaryCta"])}</button>' if hero.get("secondaryCta") else ""}</div>
      <div class="state-row" role="group" aria-label="forced button states">{chips}</div>
      <p class="lp-figcaption">Forced samples sit next to live states; neither replaces the other.</p></div>
    {form_block}
  </div>
  <div class="col">
    {f'<div class="block"><div class="cap"><span>Cards</span><span>{esc("pricing tiers" if any(c.get("per") for c in cards) else "core cards")}</span></div>{tier_html}</div>' if tier_html else ""}
    {f'<div class="block"><div class="cap"><span>Sample rows</span><span>{esc(table.get("caption") or "sample rows")}</span></div>{table_html}</div>' if table_html else ""}
    <div class="block"><div class="cap"><span>Surfaces</span><span>radius {esc(" / ".join(sorted({resolved[t["id"]]["resolved"] for t in dna["tokens"] if t["id"].startswith("radius/")}, key=lambda r: (len(r), r))[:3])) or "none recorded"}</span></div>
      <div class="ds-card">Default card · body copy sits on the surface token.</div>
      <div class="ds-card ds-card--tint">Tint card · the quieter surface.</div>
      {float_line}</div>
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
            f'<div class="mid"><div class="mono" data-copy="var(--{esc(t["css"].lstrip("-"))})" role="button" tabindex="0">'
            f'{esc(t["id"])} · {esc(dur)}</div><div class="track"><span class="dot" id="sym-{i}-dot"></span></div></div>'
            f'<div class="act"><label for="sym-{i}-range">Replay</label>'
            f'<input type="range" id="sym-{i}-range" class="motion-range" min="0" max="1000" value="0" '
            f'aria-label="scrub {esc(t["id"])}">'
            f'<button class="tp-btn" data-sys-replay="sym-{i}-dot" data-dur="{esc(dur)}" data-ease="{esc(spec)}">Play</button>'
            f'</div></div>')
    for t in easings:
        spec = resolved[t["id"]]["resolved"]
        rows.append(
            f'<div class="motion"><div class="plot">{vb.bezier_svg(spec, 168, 88)}</div>'
            f'<div class="mid"><div class="mono" data-copy="var(--{esc(t["css"].lstrip("-"))})" role="button" tabindex="0">'
            f'{esc(t["id"])}</div><div class="spec-val">{esc(spec)}</div></div>'
            f'<div class="act">{obs("motion", t["status"])}</div></div>')
    taste_html, gates = "", ""
    for t in dna["taste"]:
        taste_html += (
            f'<article class="tcard"><div class="head"><span>{esc(t["kind"])}</span>'
            f'<span>{esc(" · ".join(t["evidence"]))}</span><span>{esc(t["status"])}</span></div>'
            f'<h4>{esc(t["name"])}</h4><div class="ab"><div class="v">{esc(t["chose"])}</div>'
            f'<div class="vs">over</div><div class="v over">{esc(t["over"])}</div></div>'
            f'<p class="why">{esc(t["reason"])}</p></article>')
        if t.get("guardrail"):
            gates += (f'<div class="gate-item"><div class="gate-head"><span>{esc(t["name"])}</span>'
                      f'<span class="mono">{esc(t["id"])}</span></div>'
                      f'{sr.guardrail_caps(t["guardrail"], expandable=True)}</div>')
    live_motion = f"""
<div class="lp-sheet"><span class="lp-num">04</span><h2 class="lp-title">Motion &amp; Guardrails</h2>
<span class="rule"></span><span class="count">{len(durations)} durations · {len(easings)} curves</span></div>
<p class="lp-lede">Each curve is the token's own cubic-bezier with its handles drawn. Play runs the real duration,
the slider scrubs it, and Reduced motion in the top bar replaces travel with its end state.</p>
<div class="lp-motion">{"".join(rows)}</div>
<p class="lp-motion-legend">dot · direction of travel · curve · measured easing · status · evidence class</p>
<div class="sec-col">
  <div><div class="cap">MUST NOT · mechanical gates</div>
    <p class="lp-figcaption">Every capsule is a machine-readable rule. Expand one to read the regex a build is
    checked against; a generated page that matches it fails <code>lint_output.py</code>.</p>
    <div class="gate-list">{gates or '<p class="lp-figcaption">No restraint carries a machine gate in this run.</p>'}</div></div>
  <div><div class="cap">Taste · decision, and the rejected alternative</div>{taste_html}</div>
</div>"""

    # ---------------------------------------------------------------- 05 bricks
    if bricks:
        cards_html = "".join(ba._brick_card(b, read, esc, obs) for b in bricks)
        bricks_html = (f'<div class="lp-bricks">{cards_html}</div>'
                       f'<p class="provenance">Each brick was recorded twice in the same browser: once normally, once '
                       f'with CDP <code>prefers-reduced-motion: reduce</code>. Screenshots are the real frames from '
                       f'<code>clips/{esc(bricks[0]["slug"])}/shots/</code>.</p>')
        count = f"{len(bricks)} brick{'' if len(bricks) == 1 else 's'}"
    else:
        bricks_html = ('<p class="provenance">No <code>clips/</code> beside this file. A single module can be lifted '
                       'with <code>lewitt clip --find "…" --dest runs/…</code>, and its brick would be shown here.</p>')
        count = "no clips yet"
    live_bricks = f"""
<div class="lp-sheet"><span class="lp-num">05</span><h2 class="lp-title">Clipped Bricks</h2>
<span class="rule"></span><span class="count">{esc(count)}</span></div>
<p class="lp-lede">One module with its interaction, skin stripped and mapped onto this run's slots. The live module
on the left is rebuilt from the slot mapping; on the right is what the browser recorded on the source.</p>
{bricks_html}"""

    live = {"hero": _hero(dna, resolved, text, esc, obs), "colour": live_colour, "type": live_type,
            "components": live_components, "motion": live_motion, "bricks": live_bricks}
    # every artifact lives in the same folder as this file, so the run folder stands in for `dest`
    specs = ba._specs_panels(dna, root, resolved, pages, bricks, esc) if root is not None else \
        ba._specs_panels(dna, _NoFolder(), resolved, pages, bricks, esc)
    specs["downloads"] = specs["downloads"].replace("../", "")

    shell = sr.app_shell(dna, resolved, live, specs, pages=len(pages))
    shell = shell.replace('<link rel="stylesheet" href="../tokens.css">',
                          '<link rel="stylesheet" href="tokens.css">')
    shell = shell.replace('<title>lewitt — ', '<title>lewitt preview — ')
    for link in ('<link rel="stylesheet" href="doc.css">\n', '<link rel="stylesheet" href="site.css">\n',
                 '<link rel="stylesheet" href="system.css">\n'):
        shell = shell.replace(link, "")
    shell = shell.replace('<script src="system.js"></script>', f'<script>{vb.COPY_JS}{sr.JS}</script>')
    shell = shell.replace('</head>', "<style>" + vb.base_css(tone, scope=":root") + "\n" + sr.CSS
                          + PREVIEW_CSS_PATCH + "</style>"
                          + '<script id="evidence-data" type="application/json">'
                          + sr._json(sr.evidence_for_tags(dna)) + "</script></head>")
    # the right slot: copies of the renders beside the file, then the stress booleans
    files = "".join(f'<a class="mail" href="{f}" download>{f}</a>' for f in _SIDE)
    # preview.html: the Files links sit in the (hidden) Specs panel, not the top bar
    shell = shell.replace('<h1>Overview</h1>', '<h1>Overview</h1><p class="papp" aria-label="files beside this page">'
                          + files + '</p>', 1)
    return shell


_SCENE = {"semantic": "roles: where ink, surface and action may appear",
          "component": "inside a control: fill, label, ring",
          "primitive": "the raw palette behind the roles"}
_PAIRS = [("heading / canvas", "color/text/heading", "color/canvas", "display copy"),
          ("primary / canvas", "color/text/primary", "color/canvas", "headlines and labels"),
          ("body / canvas", "color/text/body", "color/canvas", "paragraphs"),
          ("secondary / canvas", "color/text/secondary", "color/canvas", "supporting rows"),
          ("muted / surface", "color/text/muted", "color/surface", "captions on raised rows"),
          ("muted / well", "color/text/tertiary", "color/well", "captions on the deepest surface"),
          ("action-fg / action-bg", "color/action/fg", "color/action/bg", "primary button"),
          ("link / canvas", "color/link", "color/canvas", "inline links")]
_SIDE = ("tokens.css", "shadcn-theme.css", "agent-rules.md", "taste.md", "VERIFY.md")


class _NoFolder:
    """No files beside the page: empty downloads, a stated absence of capture/clips."""

    name = "preview"

    def __truediv__(self, name):
        return self

    def exists(self):
        return False

    def glob(self, pattern):
        return []

    def read_text(self, **kw):
        return ""


def _hero(dna: dict, resolved: dict, text: dict, esc, obs) -> str:
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
    return f"""
<div class="hero-copy">
  {sr.brand_svg(dna)}
  {f'<p class="eyebrow">{esc(hero["eyebrow"])}</p>' if hero.get("eyebrow") else ""}
  <h1>{"".join(f"<span>{esc(ln)}</span>" for ln in lines)}</h1>
  {f'<p class="sub">{esc(hero["subhead"])}</p>' if hero.get("subhead") else ""}
  <div class="ctas">{ctas}</div>
  <p class="hero-note">canvas <code>{esc(canvas_v)}</code> · every specimen here reads <code>tokens.css</code>,
  the deterministic render of dna.json — not a screenshot {obs("palette")}</p>
</div>
<div class="graphic">
  <div class="twin-card"><div class="band"><span class="bandlines"></span><span class="silhouette"></span></div>
    <div class="body"><div class="status"><i></i>signature module · rendering</div>
      <div class="bar"><span></span></div><div class="name">{esc(lines[0])}</div><div class="ghost"></div></div></div>
  <span class="graphic-cap">brand colour enters only here, in the hero artwork — every control stays ink-and-action.</span>
</div>
{strip}"""
