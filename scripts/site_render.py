"""lewitt system/ — the reference App Shell (full mode).

The shell chrome is neutral and tone-aware; the system's own colour only appears inside Stages that
carry [data-ds] and sit on var(--lw-canvas). Written by build_artifacts.py, never by hand.

Panels come from the run's data (panels.py); this module owns chrome, panels wiring and the router.
"""

from __future__ import annotations

import re

import visual_base as vb

STRESS = (("long", "Long copy"), ("nogradient", "No gradient"),
          ("nomedia", "Missing media"), ("reduced", "Reduced motion"))


def app_shell(dna: dict, resolved: dict, panels: dict[str, str], *, pages: int) -> str:
    """panels: {panel_id: inner HTML}; ids are rendered in the fixed order below."""
    meta = dna["meta"]
    canvas = next((resolved[t["id"]]["resolved"] for t in dna["tokens"] if t["id"] == "color/canvas"), None)
    tone = vb.tone_of(canvas)
    t = vb.TONES[tone]
    name = meta.get("name") or meta.get("domain") or "design system"

    groups = (
        ("Foundations", (("overview", "Overview"), ("colour", "Colour"),
                         ("typography", "Typography"), ("shape", "Radius &amp; Depth"),
                         ("type-scale", "Type Scale"))),
        ("Interactive Lab", (("components", "Components &amp; States"), ("compositions", "Compositions"),
                             ("states", "Field States"), ("motion", "Motion"),
                             ("fidelity", "Fidelity vs Source"))),
        ("Specs &amp; Handoff", (("system", "System &amp; Taste"), ("specs", "Evidence &amp; Downloads"))),
    )
    groups = tuple((label, tuple((pid, title) for pid, title in items if pid in panels)) for label, items in groups)
    groups = tuple((label, items) for label, items in groups if items)

    nav = "".join(
        f'<div class="nav-group"><div class="group-label">{label}</div>'
        + "".join(f'<a class="nav-item" href="#{pid}">{title}</a>' for pid, title in items)
        + "</div>"
        for label, items in groups
    )
    stress = "".join(f'<button class="tb-btn" data-stress-toggle="{key}" aria-pressed="false">{label}</button>'
                     for key, label in STRESS)
    body = "".join(
        f'<section class="panel" id="{pid}" data-panel="{pid}">{html}</section>'
        for pid, html in panels.items()
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>lewitt — {name} design system (full mode)</title>
<link rel="stylesheet" href="../tokens.css">
<link rel="stylesheet" href="doc.css">
<link rel="stylesheet" href="system.css">
<link rel="stylesheet" href="site.css">
<script>document.documentElement.classList.add('js');</script>
</head>
<body data-view="panel" data-site="{_attr(name)} design system" data-tone="{tone}">
<a class="skip" href="#canvas">Skip to canvas</a>
<div class="shell">
  <aside class="rail" id="rail" aria-label="Sections">
    <div class="brand"><span class="brand-name">lewitt<span class="rail-x"> · </span>{name}</span>
      <small>{pages} pages · full mode</small></div>
    <button class="chip-btn rail-toggle" id="rail-toggle" aria-expanded="false" aria-controls="rail-nav">Menu</button>
    <nav id="rail-nav">{nav}</nav>
    <div class="rail-actions">
      <button class="chip-btn" id="view-print" aria-pressed="false">Print view</button>
    </div>
  </aside>
  <div class="canvas">
    <div class="toolbar" role="toolbar" aria-label="Stress controls">
      <span class="tb-label">Stress</span>
      {stress}
      <button class="tb-btn" id="viewport-390" aria-pressed="false">Narrow 390</button>
      <span class="tb-status" id="tb-status" aria-live="polite"></span>
    </div>
    <div class="scroll" id="canvas" tabindex="-1">{body}</div>
  </div>
</div>
<script src="system.js"></script>
</body>
</html>
"""


def _attr(text: str) -> str:
    return str(text).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


# --------------------------------------------------------------------------- chrome CSS
CHROME_CSS = """
/* Chrome: neutral, tone-aware, never louder than the specimen it frames.
   The system's own colour lives inside [data-ds] Stages on var(--lw-canvas). */
:root { --shell-rail: var(--n-rail-w); }
body { overflow: hidden; }
.shell { display: grid; grid-template-columns: var(--n-rail-w) minmax(0, 1fr); height: 100vh; }

.rail { display: flex; flex-direction: column; background: var(--n-rail);
  border-right: 1px solid var(--n-line); padding: 22px 0 16px; overflow: hidden; }
.brand { padding: 0 20px 18px; font-size: 13px; letter-spacing: -.01em; }
.brand .brand-name { color: var(--n-ink); }
.brand .rail-x { color: var(--n-faint); }
.brand small { display: block; margin-top: 4px; color: var(--n-mute); font: 11px/1.4 var(--n-mono); }
.rail-toggle { display: none; }
.rail nav { flex: 1; overflow-y: auto; padding-bottom: 12px; }
.nav-group { padding: 14px 0 6px; }
.nav-group + .nav-group { border-top: 1px solid var(--n-line); }
.group-label { padding: 0 20px 8px; font-size: 11px; letter-spacing: .08em; text-transform: uppercase;
  color: var(--n-faint); font-weight: 500; }
.skip { position: absolute; left: -9999px; }
.skip:focus { left: 12px; top: 8px; z-index: 50; background: var(--n-ink); color: var(--n-bg);
  padding: 8px 12px; font: 500 11px/1 var(--n-mono); text-transform: uppercase; letter-spacing: .06em; }
.chip-btn { font: 500 11px/1 var(--n-mono); letter-spacing: .05em; text-transform: uppercase;
  background: transparent; color: var(--n-mute); border: 1px solid var(--n-line-strong); border-radius: 2px;
  padding: 6px 9px; cursor: pointer; }
.chip-btn:hover { color: var(--n-ink); border-color: var(--n-ink); }
.chip-btn[aria-pressed="true"] { background: var(--n-ink); color: var(--n-bg); border-color: var(--n-ink); }
.nav-item { display: block; position: relative; padding: 7px 20px 7px 20px; font-size: 13px;
  color: var(--n-mute); text-decoration: none; line-height: 1.3; }
.nav-item:hover { color: var(--n-ink); background: var(--n-hover); }
.nav-item[aria-current="page"] { color: var(--n-ink); }
.nav-item[aria-current="page"]::before { content: ""; position: absolute; left: 0; top: 6px; bottom: 6px;
  width: 2px; background: var(--n-ink); }
.rail-actions { padding: 12px 20px 0; border-top: 1px solid var(--n-line); }

.canvas { display: grid; grid-template-rows: auto minmax(0, 1fr); min-width: 0; background: var(--n-bg); }
.toolbar { display: flex; align-items: center; gap: 6px; padding: 10px 24px;
  border-bottom: 1px solid var(--n-line); background: var(--n-bg); }
.tb-label { font: 500 11px/1 var(--n-mono); letter-spacing: .08em; text-transform: uppercase;
  color: var(--n-faint); margin-right: 8px; }
.tb-btn { font: 500 11.5px/1 var(--n-mono); letter-spacing: .02em; padding: 6px 9px;
  background: transparent; color: var(--n-mute); border: 1px solid var(--n-line-strong);
  border-radius: 2px; cursor: pointer; }
.tb-btn:hover { color: var(--n-ink); border-color: var(--n-ink); }
.tb-btn[aria-pressed="true"] { background: var(--n-ink); color: var(--n-bg); border-color: var(--n-ink); }
.tb-status { margin-left: auto; font: 11px/1 var(--n-mono); color: var(--n-mute); }

.scroll { overflow-y: auto; scroll-behavior: smooth; scroll-padding-top: 24px; }
.panel { display: none; padding: 52px var(--n-gutter) 120px; max-width: 1180px; }
.panel[data-active] { display: block !important; }
.js .panel { display: none; }
.panel[data-active] { display: block; }
.panel h1, .panel h2, .panel h3, .panel h4 { color: var(--n-ink); }
.panel h1 { font-size: 30px; font-weight: 400; letter-spacing: -.02em; margin: 0 0 10px; }
.panel > h1:not(:first-child) { margin-top: 56px; }
.panel h2 { font-size: 13px; font-weight: 500; letter-spacing: .08em; text-transform: uppercase;
  margin: 40px 0 6px; color: var(--n-ink); }
.panel h3 { font-size: 12px; font-weight: 500; letter-spacing: .05em; text-transform: uppercase;
  color: var(--n-mute); margin: 28px 0 10px; }
.lede, .sect-note { color: var(--n-mute); font-size: 13.5px; margin: 0 0 22px; max-width: 74ch; }
.note { border-left: 2px solid var(--n-ink); padding: 10px 14px; background: var(--n-hover);
  color: var(--n-mute); font-size: 13px; margin: 18px 0; max-width: 74ch; }
.count { font-family: var(--n-mono); font-size: 11px; letter-spacing: 0; color: var(--n-faint);
  text-transform: none; }

/* badges keep their meaning on both tones */
.badge { font: 500 10.5px/1 var(--n-mono); letter-spacing: .05em; text-transform: uppercase;
  padding: 3px 6px; border-radius: 2px; border: 1px solid var(--n-line-strong); color: var(--n-mute); }
.badge.observed { color: var(--n-ok); border-color: color-mix(in srgb, var(--n-ok) 45%, transparent); }
.badge.inferred { color: var(--n-warn); border-color: color-mix(in srgb, var(--n-warn) 45%, transparent); }
.badge.unverified, .badge.unknown { color: var(--n-bad); border-color: color-mix(in srgb, var(--n-bad) 45%, transparent); }

/* stage: the system's own canvas, framed by neutral chrome */
.stage { border: 1px solid var(--n-line); border-radius: 2px; overflow: hidden; background: var(--n-panel); }
.stage-head { display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 10px 16px; border-bottom: 1px solid var(--n-line); color: var(--n-mute);
  font: 500 11px/1.2 var(--n-mono); letter-spacing: .06em; text-transform: uppercase; }
.stage-body { padding: 48px; background-image: radial-gradient(circle at 1px 1px, var(--n-grid) 1px, transparent 0);
  background-size: 14px 14px; }
.stage-body > [data-ds], .stage-body .ds-scope { border-radius: 2px; }
.stage-note { padding: 10px 16px; border-top: 1px solid var(--n-line); color: var(--n-mute); font-size: 12px; }

/* the system's surface: [data-ds] carries the tokens, never the chrome */
[data-ds] { background: var(--lw-canvas); color: var(--lw-text-body); font-family: var(--lw-font-body); }
.matrix { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; align-items: end; }
.matrix figure { margin: 0; }

/* editorial tables inside panels */
.panel table { width: 100%; border-collapse: collapse; font-size: 13px; }
.panel th { text-align: left; font: 500 11px/1.2 var(--n-mono); letter-spacing: .06em; text-transform: uppercase;
  color: var(--n-mute); padding: 0 16px 8px 0; border-bottom: 1px solid var(--n-line-strong); }
.panel td { padding: 12px 16px 12px 0; border-bottom: 1px solid var(--n-line); vertical-align: top; }
.panel tr:hover td { background: var(--n-hover); }
.panel code, .panel .mono { font-family: var(--n-mono); font-size: 12px; font-variant-numeric: tabular-nums; }
.panel ul { color: var(--n-mute); font-size: 13px; padding-left: 18px; }

/* stress toggles act on the whole canvas */
.scroll[data-stress~="long"] .ds-stressable { max-width: 46ch; }
.scroll[data-stress~="nogradient"] .ds-hero-band::after { display: none; }
.scroll[data-stress~="nomedia"] .ds-media { background: repeating-linear-gradient(45deg, var(--n-hover) 0 8px, transparent 8px 16px); color: transparent; }
.scroll[data-stress~="reduced"] *, .scroll[data-stress~="reduced"] *::before, .scroll[data-stress~="reduced"] *::after {
  transition-duration: .001ms !important; animation-duration: .001ms !important; }

/* fidelity: split compare */
.compare { position: relative; border: 1px solid var(--n-line); overflow: hidden; background: var(--n-panel); }
.compare img { display: block; width: 100%; }
.compare .layer.b { position: absolute; inset: 0; clip-path: inset(0 50% 0 0); }
.compare .handle { position: absolute; top: 0; bottom: 0; left: 50%; width: 1px; background: var(--n-ink);
  pointer-events: none; }
.compare .handle::after { content: ""; position: absolute; top: 50%; left: 50%; width: 28px; height: 28px;
  margin: -14px 0 0 -14px; border-radius: 50%; border: 1px solid var(--n-ink); background: var(--n-bg); }
.compare input[type=range] { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0;
  cursor: ew-resize; margin: 0; }
.compare .lab { position: absolute; bottom: 10px; font: 10.5px/1 var(--n-mono); letter-spacing: .06em;
  text-transform: uppercase; background: var(--n-bg); color: var(--n-mute); padding: 5px 7px;
  border: 1px solid var(--n-line-strong); }
.compare .lab.l { left: 10px; } .compare .lab.r { right: 10px; }
.sbs { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: var(--n-line); border: 1px solid var(--n-line); }
.sbs figure { margin: 0; background: var(--n-panel); padding: 12px; }
.sbs figcaption { font: 11px/1.4 var(--n-mono); color: var(--n-mute); margin-top: 8px; }

/* specs: sub-tabs + copyable code */
.subtabs { display: flex; gap: 0; border-bottom: 1px solid var(--n-line); margin: 0 0 20px; }
.subtabs button { font: 500 11.5px/1 var(--n-mono); letter-spacing: .05em; text-transform: uppercase;
  background: transparent; border: 0; border-bottom: 2px solid transparent; color: var(--n-mute);
  padding: 10px 14px; cursor: pointer; }
.subtabs button[aria-selected="true"] { color: var(--n-ink); border-bottom-color: var(--n-ink); }
.tabpanel[hidden] { display: none; }
.code { border: 1px solid var(--n-line); border-radius: 2px; background: var(--n-panel); }
.code-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 8px 12px;
  border-bottom: 1px solid var(--n-line); font: 500 11px/1 var(--n-mono); letter-spacing: .06em;
  text-transform: uppercase; color: var(--n-mute); }
.code pre { margin: 0; padding: 14px 16px; overflow: auto; max-height: 300px; font: 12px/1.65 var(--n-mono);
  color: var(--n-ink); white-space: pre; }
.dl { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 20px; }

.rule-cap { display: inline-block; font: 500 10.5px/1 var(--n-mono); letter-spacing: .06em;
  text-transform: uppercase; padding: 3px 6px; border-radius: 2px; border: 1px solid var(--n-line-strong);
  color: var(--n-mute); margin: 0 4px 4px 0; }
.rule-cap.forbid { color: var(--n-bad); border-color: color-mix(in srgb, var(--n-bad) 45%, transparent); }
.rule-cap.max { color: var(--n-warn); border-color: color-mix(in srgb, var(--n-warn) 45%, transparent); }

/* print view: every panel, one column, chrome kept for orientation */
body[data-view="print"] .rail nav, body[data-view="print"] .toolbar { display: none; }
body[data-view="print"] .shell { grid-template-columns: 1fr; height: auto; }
body[data-view="print"] body { overflow: auto; }
body[data-view="print"] .scroll { overflow: visible; }
body[data-view="print"] .panel { display: block; }

@media (max-width: 900px) {
  .toolbar { flex-wrap: wrap; padding: 8px 12px; }
  .tb-label, .tb-status { display: none; }
  .toolbar .tb-btn { padding: 6px 7px; }
  .shell { grid-template-columns: 1fr; grid-template-rows: auto minmax(0, 1fr); }
  .rail { flex-direction: row; align-items: center; gap: 8px; padding: 8px 12px; border-right: 0;
    border-bottom: 1px solid var(--n-line); }
  .brand { padding: 0; }
  .brand small { display: none; }
  .rail-toggle { display: inline-block; margin-left: auto; }
  .rail nav { display: none; position: absolute; top: 56px; left: 0; right: 0; z-index: 30;
    background: var(--n-rail); border-bottom: 1px solid var(--n-line); max-height: 60vh; }
  .rail[data-open] nav { display: block; }
  .rail-actions { display: none; }
  .panel { padding: 28px 20px 90px; }
  .stage-body { padding: 24px 16px; }
  .sbs { grid-template-columns: 1fr; }
}
"""


ROUTER_JS = r"""
// lewitt system/ — panel router, stress toolbar, sub-tabs, fidelity slider, copy affordances.
(function () {
  var PANELS = Array.prototype.map.call(document.querySelectorAll('.panel'), function (p) { return p.id; });
  var canvas = document.getElementById('canvas');
  var navLinks = Array.prototype.slice.call(document.querySelectorAll('.rail a.nav-item'));
  var STATUS = document.getElementById('tb-status');
  function say(t) { if (STATUS) STATUS.textContent = t; }

  function currentPanel() {
    var id = (location.hash || '#' + (PANELS[0] || 'overview')).replace('#', '').split('/')[0];
    return PANELS.indexOf(id) > -1 ? id : PANELS[0];
  }
  function showPanel(id, focus) {
    PANELS.forEach(function (p) {
      var s = document.getElementById(p);
      if (p === id) s.setAttribute('data-active', ''); else s.removeAttribute('data-active');
    });
    navLinks.forEach(function (a) {
      if (a.getAttribute('href') === '#' + id) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });
    document.title = 'lewitt — ' + id + ' — ' + (document.body.dataset.site || 'design system');
    if (canvas) canvas.scrollTop = 0;
    var sub = (location.hash || '').split('/')[1];
    if (id === 'specs' && sub) selectSubTab(sub);
    setMobileOpen(false);
  }
  window.addEventListener('hashchange', function () { showPanel(currentPanel(), false); });
  showPanel(currentPanel(), false);
  navLinks.forEach(function (a) {
    a.addEventListener('click', function (e) {
      var id = a.getAttribute('href').slice(1);
      if (currentPanel() === id) { e.preventDefault(); showPanel(id, true); }
    });
  });

  var rail = document.getElementById('rail'), toggle = document.getElementById('rail-toggle');
  function setMobileOpen(open) {
    if (!rail || !toggle) return;
    if (open) rail.setAttribute('data-open', ''); else rail.removeAttribute('data-open');
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  if (toggle) toggle.addEventListener('click', function () { setMobileOpen(!rail.hasAttribute('data-open')); });

  var printBtn = document.getElementById('view-print');
  if (printBtn) printBtn.addEventListener('click', function () {
    var on = document.body.dataset.view === 'print';
    document.body.dataset.view = on ? 'panel' : 'print';
    printBtn.setAttribute('aria-pressed', on ? 'false' : 'true');
    printBtn.textContent = on ? 'Print view' : 'Exit print view';
    if (on) showPanel(currentPanel(), false);
    else PANELS.forEach(function (p) { document.getElementById(p).setAttribute('data-active', ''); });
  });

  // stress toolbar: one state for the whole canvas
  var active = {};
  function applyStress() {
    var on = Object.keys(active).filter(function (k) { return active[k]; });
    canvas.setAttribute('data-stress', on.join(' '));
    var narrow = document.getElementById('viewport-390').getAttribute('aria-pressed') === 'true';
    Array.prototype.forEach.call(document.querySelectorAll('.panel'), function (el) {
      el.style.maxWidth = narrow ? '390px' : ''; el.style.margin = narrow ? '0 auto' : '';
    });
    say(on.length ? 'stress: ' + on.join(', ') + (narrow ? ' · 390px' : '') : (narrow ? '390px preview' : ''));
  }
  Array.prototype.forEach.call(document.querySelectorAll('[data-stress-toggle]'), function (btn) {
    btn.addEventListener('click', function () {
      var key = btn.getAttribute('data-stress-toggle');
      active[key] = !active[key];
      btn.setAttribute('aria-pressed', active[key] ? 'true' : 'false');
      applyStress();
    });
  });
  var narrowBtn = document.getElementById('viewport-390');
  if (narrowBtn) narrowBtn.addEventListener('click', function () {
    var on = narrowBtn.getAttribute('aria-pressed') === 'true';
    narrowBtn.setAttribute('aria-pressed', on ? 'false' : 'true');
    applyStress();
  });

  // specs sub-tabs, reachable as #specs/tokens
  var subTabs = Array.prototype.slice.call(document.querySelectorAll('.subtabs [role="tab"]'));
  function selectSubTab(key) {
    var idx = typeof key === 'number' ? key : subTabs.findIndex(function (b) {
      return b.id === 'tab-' + key || b.getAttribute('aria-controls') === 'sub-' + key;
    });
    if (idx < 0) idx = 0;
    subTabs.forEach(function (t, i) {
      var on = i === idx;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
      var panel = document.getElementById(t.getAttribute('aria-controls'));
      if (panel) panel.hidden = !on;
    });
  }
  subTabs.forEach(function (t, i) {
    t.addEventListener('click', function () { selectSubTab(i); });
    t.addEventListener('keydown', function (e) {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      e.preventDefault();
      var next = e.key === 'ArrowRight' ? (i + 1) % subTabs.length : (i - 1 + subTabs.length) % subTabs.length;
      selectSubTab(next); subTabs[next].focus();
    });
  });
  if (subTabs.length) selectSubTab(0);

  // fidelity split compare
  var range = document.getElementById('split');
  if (range) {
    var cmp = document.getElementById('compare');
    var apply = function () {
      var b = cmp.querySelector('.layer.b'), h = cmp.querySelector('.handle');
      if (b) b.style.clipPath = 'inset(0 ' + (100 - range.value) + '% 0 0)';
      if (h) h.style.left = range.value + '%';
    };
    range.addEventListener('input', apply); apply();
    var t = document.getElementById('compare-toggle');
    if (t) t.addEventListener('click', function () {
      var split = t.getAttribute('aria-pressed') === 'true';
      t.setAttribute('aria-pressed', split ? 'false' : 'true');
      document.getElementById('compare').hidden = !split;
      document.getElementById('sbs').hidden = split;
    });
  }

  // copy affordance
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
    if (e.key === 'Escape' && document.body.dataset.view === 'print' && printBtn) printBtn.click();
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var el = e.target.closest('[data-copy][tabindex]');
    if (!el) return;
    e.preventDefault();
    el.click();
  });
})();
"""


def _esc(value) -> str:
    return (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


# --------------------------------------------------------------------------- stage helpers
def stage(title: str, inner: str, *, meta: str = "", note: str = "", tone: str = "light") -> str:
    """One specimen on its own field. `inner` lands in the system surface, not the chrome."""
    head = f'<div class="stage-head"><span>{title}</span><span>{meta}</span></div>' if title or meta else ""
    tail = f'<div class="stage-note">{note}</div>' if note else ""
    return (f'<div class="stage"><div class="stage-body"><div data-ds>{inner}</div></div>{tail}</div>'
            if not head else
            f'<div class="stage">{head}<div class="stage-body"><div data-ds>{inner}</div></div>{tail}</div>')


def type_scale_rows(tokens: list[dict], resolved: dict) -> str:
    """Specimen rows: parameters left, real-size specimen right."""
    rows = []
    for t in tokens:
        if t["type"] != "dimension" or not t["id"].startswith("type/"):
            continue
        size = resolved[t["id"]]["resolved"]
        rows.append(
            f'<div class="type-row"><div class="type-params"><span class="mono" data-copy="var(--{_esc(t["css"].lstrip("-"))})">'
            f'{_esc(t["id"])}</span><dl><dt>size</dt><dd>{_esc(size)}</dd></dl></div>'
            f'<div class="type-specimen"><span class="spec" style="font-size:{_esc(size)}">{_esc("Financial infrastructure to grow your revenue")}</span></div></div>'
        )
    return "".join(rows)


def spec_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
