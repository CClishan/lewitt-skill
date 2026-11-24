
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

// replay dots for the system/ motion panel
(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function msFrom(d) { var m = /([0-9.]+)\s*(ms|s)/i.exec(String(d)); return m ? (m[2].toLowerCase() === 's' ? parseFloat(m[1]) * 1000 : parseFloat(m[1])) : 300; }
  Array.prototype.forEach.call(document.querySelectorAll('[data-sys-replay]'), function (btn) {
    var dot = document.getElementById(btn.getAttribute('data-sys-replay'));
    if (!dot) return;
    var dur = btn.getAttribute('data-dur'), ease = btn.getAttribute('data-ease');
    btn.addEventListener('click', function () {
      dot.style.transition = 'none'; dot.style.transform = 'translateX(0)'; void dot.offsetWidth;
      if (reduce) return;
      dot.style.transition = 'transform ' + dur + ' ' + ease;
      dot.style.transform = 'translateX(calc(100% - 12px))';
    });
  });
})();
