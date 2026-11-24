"""lewitt shared visual base — the neutral, architectural layer used by all three artifacts.

preview.html, system/ (App Shell chrome) and cert.html all read from here, so the three pieces look
like one publication instead of three tools. No external assets: system font stacks, inline SVG,
plain CSS strings only.

Two tones, chosen automatically from the system's own canvas token:

    light  shell #F6F6F5 · rail #FAFAF9 · ink #18181B · mute #71717A
    dark   shell #09090B · rail #0F0F12 · ink #F4F4F5 · mute #8E8E98
"""

from __future__ import annotations

BASE_MONO = "ui-monospace, SFMono-Regular, Menlo, monospace"
BASE_SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif'

TONES = {
    "light": {
        "bg": "#F6F6F5", "panel": "#FFFFFF", "rail": "#FAFAF9",
        "ink": "#18181B", "mute": "#71717A", "faint": "#A1A1AA",
        "line": "rgba(0,0,0,0.08)", "line-strong": "rgba(0,0,0,0.14)",
        "grid": "rgba(0,0,0,0.06)", "hover": "rgba(0,0,0,0.035)",
        "status": {"ok": "#1F7A4D", "warn": "#8A5A00", "bad": "#A33A2B", "neutral": "#52525B"},
    },
    "dark": {
        "bg": "#09090B", "panel": "#111114", "rail": "#0F0F12",
        "ink": "#F4F4F5", "mute": "#8E8E98", "faint": "#5D5D66",
        "line": "rgba(255,255,255,0.08)", "line-strong": "rgba(255,255,255,0.14)",
        "grid": "rgba(255,255,255,0.07)", "hover": "rgba(255,255,255,0.04)",
        "status": {"ok": "#63C08C", "warn": "#D9AE5F", "bad": "#E07A68", "neutral": "#9CA3AF"},
    },
}


def color_rgb(value: str | None):
    """'#RRGGBB', '#RGB' or 'rgb(r, g, b)' -> (r, g, b) in 0..255, else None."""
    v = (value or "").strip().lower()
    if v.startswith("#"):
        h = v[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        if len(h) >= 6:
            try:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            except ValueError:
                return None
    if v.startswith("rgb"):
        digits = [p.strip() for p in v[v.find("(") + 1:v.find(")")].replace("/", ",").split(",")]
        try:
            return tuple(int(float(d)) for d in digits[:3])
        except (ValueError, IndexError):
            return None
    return None


def relative_luminance(colour: str | None) -> float | None:
    c = color_rgb(colour)
    if not c:
        return None

    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def tone_of(colour: str | None) -> str:
    """Pick the shell tone from the system's canvas colour (light when unknown)."""
    lum = relative_luminance(colour)
    if lum is None:
        return "light"
    return "light" if lum > 0.5 else "dark"


def contrast(a: str | None, b: str | None) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    if la is None or lb is None:
        return 0.0
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def wcag_badge(a: str | None, b: str | None) -> tuple[str, str]:
    """('16.4:1 · AAA', 'ok'|'warn'|'bad') — grade is the WCAG 2.2 text contrast tier."""
    ratio = contrast(a, b)
    if ratio >= 7:
        return f"{ratio:.1f}:1 · AAA", "ok"
    if ratio >= 4.5:
        return f"{ratio:.1f}:1 · AA", "ok"
    if ratio >= 3:
        return f"{ratio:.1f}:1 · AA-large", "warn"
    return f"{ratio:.1f}:1 · FAIL", "bad"


def cubic_points(spec: str):
    """Parse 'cubic-bezier(a,b,c,d)' (or a keyword) into control points."""
    named = {
        "ease": (0.25, 0.1, 0.25, 1.0),
        "ease-in": (0.42, 0.0, 1.0, 1.0),
        "ease-out": (0.0, 0.0, 0.58, 1.0),
        "ease-in-out": (0.42, 0.0, 0.58, 1.0),
        "linear": (0.0, 0.0, 1.0, 1.0),
    }
    s = (spec or "").strip().lower()
    if s in named:
        return named[s]
    if s.startswith("cubic-bezier("):
        body = s[s.find("(") + 1:s.rfind(")")]
        parts = [p.strip() for p in body.split(",")]
        if len(parts) == 4:
            try:
                return tuple(float(p) for p in parts)
            except ValueError:
                return None
    return None


def bezier_svg(spec: str, w: int = 168, h: int = 88, pad: int = 10) -> str:
    """Deterministic inline SVG plot of a cubic-bezier: grid, handles, curve, end points."""
    pts = cubic_points(spec)
    if not pts:
        return ""
    x1, y1, x2, y2 = pts
    iw, ih = w - pad * 2, h - pad * 2

    def X(t):
        return pad + t * iw

    def Y(v):
        return pad + (1 - v) * ih

    d = (f"M {X(0):.1f} {Y(0):.1f} C {X(x1):.1f} {Y(y1):.1f} "
         f"{X(x2):.1f} {Y(y2):.1f} {X(1):.1f} {Y(1):.1f}")
    grid = "".join(f'<line x1="{X(i / 4):.1f}" y1="{pad}" x2="{X(i / 4):.1f}" y2="{h - pad}" />' for i in range(5))
    grid += "".join(f'<line x1="{pad}" y1="{Y(i / 4):.1f}" x2="{w - pad}" y2="{Y(i / 4):.1f}" />' for i in range(5))
    handles = (
        f'<line class="hz" x1="{X(0):.1f}" y1="{Y(0):.1f}" x2="{X(x1):.1f}" y2="{Y(y1):.1f}" />'
        f'<line class="hz" x1="{X(1):.1f}" y1="{Y(1):.1f}" x2="{X(x2):.1f}" y2="{Y(y2):.1f}" />'
        f'<circle class="hn" cx="{X(x1):.1f}" cy="{Y(y1):.1f}" r="2" />'
        f'<circle class="hn" cx="{X(x2):.1f}" cy="{Y(y2):.1f}" r="2" />'
    )
    return (
        f'<svg class="bezier" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
        f'aria-label="cubic-bezier {x1:g} {y1:g} {x2:g} {y2:g}: progress over time">'
        f'<g class="bg">{grid}</g>{handles}<path class="curve" d="{d}" />'
        f'<circle class="end" cx="{X(0):.1f}" cy="{Y(0):.1f}" r="2.5" />'
        f'<circle class="end" cx="{X(1):.1f}" cy="{Y(1):.1f}" r="2.5" />'
        f'<line class="axis" x1="{pad}" y1="{h - pad}" x2="{w - pad}" y2="{h - pad}" />'
        "</svg>"
    )


def _base_tokens(t: dict, scope: str) -> str:
    st = t["status"]
    return (
        "/* ---- neutral base (" + scope + ") ---------------------------------------------------\n"
        "   Every colour here is a neutral: the artifact's own system colour lives inside a Stage. */\n"
        + scope + " {\n"
        f"  --n-bg: {t['bg']}; --n-panel: {t['panel']}; --n-rail: {t['rail']};\n"
        f"  --n-ink: {t['ink']}; --n-mute: {t['mute']}; --n-faint: {t['faint']};\n"
        f"  --n-line: {t['line']}; --n-line-strong: {t['line-strong']};\n"
        f"  --n-grid: {t['grid']}; --n-hover: {t['hover']};\n"
        f"  --n-ok: {st['ok']}; --n-warn: {st['warn']}; --n-bad: {st['bad']}; --n-neutral: {st['neutral']};\n"
        f"  --n-sans: {BASE_SANS};\n"
        f"  --n-mono: {BASE_MONO};\n"
        "  --n-rail-w: 240px; --n-gutter: 48px;\n"
        "}\n"
    )


BASE_RULES = """
* { box-sizing: border-box; }
body { margin: 0; background: var(--n-bg); color: var(--n-ink);
  font: 15px/1.55 var(--n-sans); -webkit-font-smoothing: antialiased; }
a { color: inherit; }
:focus-visible { outline: 2px solid var(--n-ink); outline-offset: 2px; }
.num, .mono, td, th, code { font-variant-numeric: tabular-nums; }
.mono { font-family: var(--n-mono); font-size: 12px; }

.eyebrow { font-size: 11px; letter-spacing: .08em; text-transform: uppercase;
  color: var(--n-mute); font-weight: 500; margin: 0 0 12px; }

.chip { display: inline-flex; align-items: center; gap: 5px; font: 500 10.5px/1 var(--n-mono);
  letter-spacing: .04em; text-transform: uppercase; padding: 3px 7px; border-radius: 999px;
  border: 1px solid var(--n-line-strong); color: var(--n-mute); white-space: nowrap; }
.chip.ok { color: var(--n-ok); border-color: color-mix(in srgb, var(--n-ok) 45%, transparent); }
.chip.warn { color: var(--n-warn); border-color: color-mix(in srgb, var(--n-warn) 45%, transparent); }
.chip.bad { color: var(--n-bad); border-color: color-mix(in srgb, var(--n-bad) 45%, transparent); }

.stage { position: relative; border: 1px solid var(--n-line); border-radius: 2px;
  background: var(--n-panel); overflow: hidden; }
.stage-head { display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 10px 16px; border-bottom: 1px solid var(--n-line);
  font: 500 11px/1.2 var(--n-mono); letter-spacing: .06em; text-transform: uppercase; color: var(--n-mute); }
.stage-body { padding: 48px; position: relative;
  background-image: radial-gradient(circle at 1px 1px, var(--n-grid) 1px, transparent 0);
  background-size: 14px 14px; }
.stage-body.tight { padding: 24px 32px; }
.stage-note { padding: 10px 16px; border-top: 1px solid var(--n-line); color: var(--n-mute); font-size: 12px; }

table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; font: 500 11px/1.2 var(--n-mono); letter-spacing: .06em; text-transform: uppercase;
  color: var(--n-mute); padding: 0 16px 8px 0; border-bottom: 1px solid var(--n-line-strong); }
td { padding: 12px 16px 12px 0; border-bottom: 1px solid var(--n-line); vertical-align: top; color: var(--n-ink); }
tr:hover td { background: var(--n-hover); }
table code { font-family: var(--n-mono); font-size: 12px; }

/* a wide spec table scrolls in place; the page never overflows sideways */
@media (max-width: 900px) {
  .tbl { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .tbl table { min-width: 520px; }
}

[data-copy] { cursor: copy; }
.copied-note { position: fixed; z-index: 60; pointer-events: none; transform: translate(-50%, -140%);
  font: 500 11px/1 var(--n-mono); letter-spacing: .04em; text-transform: uppercase;
  background: var(--n-ink); color: var(--n-bg); padding: 6px 8px; border-radius: 2px;
  opacity: 1; transition: opacity .35s ease; }
.copied-note.out { opacity: 0; }

details { border-top: 1px solid var(--n-line); margin-top: 12px; padding-top: 10px; }
summary { cursor: pointer; font: 500 11px/1.4 var(--n-mono); letter-spacing: .06em;
  text-transform: uppercase; color: var(--n-mute); }
summary:hover { color: var(--n-ink); }
details pre { margin: 10px 0 0; padding: 12px 14px; background: var(--n-bg); border: 1px solid var(--n-line);
  border-radius: 2px; overflow-x: auto; font: 11.5px/1.6 var(--n-mono); color: var(--n-mute);
  white-space: pre-wrap; overflow-wrap: anywhere; }

.code { position: relative; border: 1px solid var(--n-line); border-radius: 2px; background: var(--n-bg); }
.code-head { display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 8px 12px; border-bottom: 1px solid var(--n-line);
  font: 500 11px/1 var(--n-mono); letter-spacing: .06em; text-transform: uppercase; color: var(--n-mute); }
.code pre { margin: 0; padding: 14px 16px; overflow: auto; max-height: 320px;
  font: 12px/1.65 var(--n-mono); color: var(--n-ink); white-space: pre; }

.mini-btn { font: 500 11px/1 var(--n-mono); letter-spacing: .05em; text-transform: uppercase;
  background: transparent; color: var(--n-mute); border: 1px solid var(--n-line-strong);
  border-radius: 2px; padding: 5px 8px; cursor: pointer; text-decoration: none; }
.mini-btn:hover { color: var(--n-ink); border-color: var(--n-ink); }
.mini-btn[aria-pressed="true"] { color: var(--n-ink); border-color: var(--n-ink); }

.bezier .bg line { stroke: var(--n-line); stroke-width: .5; }
.bezier .hz { stroke: var(--n-line-strong); stroke-width: .75; stroke-dasharray: 2 3; }
.bezier .hn { fill: var(--n-panel); stroke: var(--n-mute); stroke-width: 1; }
.bezier .curve { fill: none; stroke: var(--n-ink); stroke-width: 1.5; stroke-linecap: round; }
.bezier .end { fill: var(--n-ink); }
.bezier .axis { stroke: var(--n-line-strong); stroke-width: .75; }

@media (max-width: 900px) {
  .stage-body { padding: 28px 20px; }
}
@media (prefers-reduced-motion: reduce) {
  * { animation-duration: .001ms !important; transition-duration: .001ms !important; }
}
"""


def base_css(tone: str, *, scope: str = "body") -> str:
    """Neutral tokens + reset + shared primitives, for the given tone."""
    pin = ":root { color-scheme: %s; }\n" % tone if scope == "body" else ""
    return pin + _base_tokens(TONES[tone], scope) + BASE_RULES


# ---------------------------------------------------------------------------- brand fingerprint
# The source site's own role colours in measured proportions; the shell stays neutral around them.
FINGERPRINT = (("canvas", 60), ("surface", 25), ("action", 10), ("accent", 5))


def fingerprint_css(stops: list[tuple[str | None, int]], *, selector: str) -> str:
    """3px band: one gradient stop per role, in proportion, read from the run's semantic colours."""
    if not stops:
        return ""
    parts, acc = [], 0
    for colour, ratio in stops:
        acc += ratio
        parts.append(f"{colour or 'var(--n-line-strong)'} {acc - ratio}% {acc}%")
    return (".fpl { height: 3px; flex: none; }\n"
            f"{selector} {{ background: linear-gradient(90deg, {', '.join(parts)}); }}\n")


def fingerprint_stops(resolved: dict, dna: dict) -> list[tuple[str | None, int]]:
    """canvas 60 · surface 25 · action 10 · one accent 5, from the run's own colour tokens.

    Roles come first; a system that is almost monochrome (Linear: canvas #08090A, action white)
    falls back to its declared brand surfaces and primitives so the band still names the site.
    """
    semantic = [t["id"] for t in dna["tokens"] if t["type"] == "color" and t["layer"] == "semantic"]
    everything = [t["id"] for t in dna["tokens"] if t["type"] == "color" and not t["id"].startswith("color/text")]

    def val(*ids):
        for i in ids:
            v = (resolved.get(i) or {}).get("resolved")
            if color_rgb(v):
                return v
        return None

    def first(*prefixes, pool=None):
        for p in prefixes:
            for i in (pool or semantic):
                if i.startswith(p) and color_rgb(resolved[i]["resolved"]):
                    return resolved[i]["resolved"]
        return None

    canvas = val("color/canvas")
    surface = val("color/surface", "color/surface-subtle", "color/canvas-tint", "color/well")
    surface = surface or first("color/wash", "color/neutral/900", "color/slate/900", "color/panel", pool=everything)
    action = val("color/action/bg", "color/action/bg-alt")
    action = action or first("color/white", "color/brand", "color/gold", "color/indigo", pool=everything)
    accent = first("color/link", "color/trend/up", "color/canvas-tint", "color/brand", "color/ring",
                   "color/border-strong")
    accent = accent or first("color/ring", "color/canvas-tint", "color/neutral/850", "color/neutral/800",
                             "color/slate/600", "color/primary", "color/indigo", pool=everything)
    picked = (("canvas", canvas), ("surface", surface), ("action", action), ("accent", accent))
    seen: list[str] = []
    out = []
    for (label, colour), ratio in zip(picked, (r for _, r in FINGERPRINT)):
        if colour and colour not in seen:
            seen.append(colour)
            out.append((colour, ratio))
    return out


LINES_SVG = (
    '<svg class="lw-mark" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">'
    '<g fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="square">'
    '<path d="M7.5 0V7.5"/><path d="M8.5 8.5H16"/>'
    '<path d="M0.5 8.5L7.5 15.5"/><path d="M15.5 8.5L8.5 15.5"/>'
    "</g></svg>"
)
"""Sol LeWitt four-quadrant line study: one line per quadrant, set off a 1px cross, in currentColor."""


def lines_mark(cls: str = "lw-mark") -> str:
    return LINES_SVG.replace('class="lw-mark"', f'class="{cls}"')


COPY_JS = r"""
// shared copy affordance: click any [data-copy], a note fades away next to it
(function () {
  function note(el, text) {
    var old = document.querySelector('.copied-note');
    if (old) old.remove();
    var r = el.getBoundingClientRect();
    var n = document.createElement('span');
    n.className = 'copied-note';
    n.textContent = text || 'Copied';
    n.style.left = Math.round(r.left + r.width / 2) + 'px';
    n.style.top = Math.round(r.top) + 'px';
    document.body.appendChild(n);
    window.setTimeout(function () { n.classList.add('out'); }, 1000);
    window.setTimeout(function () { n.remove(); }, 1400);
  }
  function copy(el, text) {
    var done = function () { note(el, text.indexOf('\n') > -1 ? 'Copied block' : 'Copied'); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { note(el, 'Clipboard blocked'); });
    } else { note(el, 'Clipboard unavailable'); }
  }
  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-copy]');
    if (!el) return;
    if (el.matches('button, a')) { e.preventDefault(); e.stopPropagation(); }
    copy(el, el.getAttribute('data-copy'));
  }, true);
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var el = e.target.closest('[data-copy][tabindex]');
    if (!el) return;
    e.preventDefault();
    copy(el, el.getAttribute('data-copy'));
  });
})();
"""
