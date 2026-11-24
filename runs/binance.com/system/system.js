// lewitt system/ — App Shell behaviour. Local only; nothing is submitted to the source site.
(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.documentElement.classList.toggle('os-reduce', reduce);

  var STATUS = document.getElementById('tb-status');
  function say(t) { if (STATUS) STATUS.textContent = t; }

  // ---------- panel routing (hash <-> panel, Back/Forward, deep links)
  var PANELS = ['overview', 'colour', 'typography', 'shape', 'components', 'compositions', 'motion', 'fidelity', 'system', 'specs'];
  var canvas = document.getElementById('canvas');
  var navLinks = Array.prototype.slice.call(document.querySelectorAll('.rail a.nav-item'));

  function currentPanel() {
    var id = (location.hash || '#overview').slice(1).split('/')[0];
    return PANELS.indexOf(id) > -1 ? id : 'overview';
  }

  function showPanel(id, focus) {
    PANELS.forEach(function (p) {
      var section = document.getElementById(p);
      if (!section) return;
      if (p === id) section.setAttribute('data-active', ''); else section.removeAttribute('data-active');
    });
    navLinks.forEach(function (a) {
      if (a.getAttribute('href') === '#' + id) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });
    document.title = 'lewitt — ' + id + ' — ' + (document.body.dataset.site || 'design system');
    if (canvas) {
      canvas.scrollTop = 0;
      var head = document.querySelector('#' + id + ' h1');
      var toolbar = document.querySelector('.toolbar');
      var offset = toolbar ? toolbar.getBoundingClientRect().height + 12 : 0;
      if (head) {
        var top = head.getBoundingClientRect().top - canvas.getBoundingClientRect().top + canvas.scrollTop - offset;
        canvas.scrollTop = Math.max(0, top);
      }
    }
    if (focus) {
      var h = document.querySelector('#' + id + ' h1');
      if (h) h.setAttribute('tabindex', '-1'), h.focus({ preventScroll: true });
    }
    // a panel can carry its own sub-tab in the hash: #specs/tokens
    var sub = (location.hash || '').split('/')[1];
    if (id === 'specs' && sub) selectSubTab(sub);
    if (document.body.dataset.view === 'print') document.body.dataset.view = 'panel';
    setMobileOpen(false);
  }

  window.addEventListener('hashchange', function () { showPanel(currentPanel(), false); });
  showPanel(currentPanel(), false);

  navLinks.forEach(function (a) {
    a.addEventListener('click', function (e) {
      var id = a.getAttribute('href').slice(1);
      if (currentPanel() === id) {           // same panel: still move focus, no history churn
        e.preventDefault();
        showPanel(id, true);
      }
    });
  });

  // ---------- mobile drawer
  var rail = document.getElementById('rail');
  var toggle = document.getElementById('rail-toggle');
  function setMobileOpen(open) {
    if (!rail || !toggle) return;
    if (open) rail.setAttribute('data-open', ''); else rail.removeAttribute('data-open');
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  if (toggle) toggle.addEventListener('click', function () { setMobileOpen(!rail.hasAttribute('data-open')); });

  // ---------- print / expand-all view
  var printBtn = document.getElementById('view-print');
  if (printBtn) {
    printBtn.addEventListener('click', function () {
      var on = document.body.dataset.view === 'print';
      document.body.dataset.view = on ? 'panel' : 'print';
      printBtn.setAttribute('aria-pressed', on ? 'false' : 'true');
      printBtn.textContent = on ? 'Print view' : 'Exit print view';
      if (!on) PANELS.forEach(function (p) { var s = document.getElementById(p); if (s) s.setAttribute('data-active', ''); });
      else showPanel(currentPanel(), false);
      say(on ? 'showing current panel' : 'print view: all panels expanded');
    });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && document.body.dataset.view === 'print' && printBtn) printBtn.click();
  });

  // ---------- sticky stress toolbar (applies to the whole canvas; reusable on every panel)
  var STRESS = { long: 'Long copy', nogradient: 'No gradient', nomedia: 'Missing media', reduced: 'Reduced motion' };
  var active = {};
  function applyStress() {
    var on = Object.keys(active).filter(function (k) { return active[k]; });
    if (!canvas) return;
    canvas.setAttribute('data-stress', on.join(' '));
    // legacy selectors in system.css were scoped to [data-stress=…]; mirror them here
    Object.keys(STRESS).forEach(function (k) { canvas.classList.toggle('stress-' + k, !!active[k]); });
    var narrow = document.getElementById('viewport-390').getAttribute('aria-pressed') === 'true';
    canvas.style.paddingRight = narrow ? '0' : '';
    var w = narrow ? 390 : null;
    var probes = document.querySelectorAll('[data-stressable-panel]');
    Array.prototype.forEach.call(probes, function (el) {
      if (w) { el.style.maxWidth = w + 'px'; el.style.margin = '0 auto'; }
      else { el.style.maxWidth = ''; el.style.margin = ''; }
    });
    say(on.length ? 'stress: ' + on.join(', ') + (narrow ? ' · 390px' : '') : (narrow ? '390px preview' : 'stress off'));
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

  // ---------- sub-tabs inside the Specs panel
  var subTabs = Array.prototype.slice.call(document.querySelectorAll('.subtabs [role="tab"]'));
  function selectSubTab(idOrIndex) {
    var idx = typeof idOrIndex === 'number' ? idOrIndex
      : subTabs.findIndex(function (b) { return b.getAttribute('aria-controls') === 'sub-' + idOrIndex || b.id === 'tab-' + idOrIndex; });
    if (idx < 0) idx = 0;
    subTabs.forEach(function (t, i) {
      var on = i === idx;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
      var panel = document.getElementById(t.getAttribute('aria-controls'));
      if (panel) panel.hidden = !on;
    });
  }
  window.lewittSelectSubTab = selectSubTab;
  subTabs.forEach(function (t, i) {
    t.addEventListener('click', function () {
      selectSubTab(i);
      var sub = t.getAttribute('aria-controls').replace('sub-', '');
      if (currentPanel() === 'specs') history.replaceState(null, '', '#specs/' + sub);
    });
    t.addEventListener('keydown', function (e) {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      e.preventDefault();
      var next = e.key === 'ArrowRight' ? (i + 1) % subTabs.length : (i - 1 + subTabs.length) % subTabs.length;
      selectSubTab(next);
      subTabs[next].focus();
    });
  });

  // ---------- motion replay
  Array.prototype.forEach.call(document.querySelectorAll('[data-replay]'), function (btn) {
    var box = document.getElementById(btn.getAttribute('data-replay'));
    if (!box) return;
    var dur = btn.getAttribute('data-dur'), ease = btn.getAttribute('data-ease');
    btn.addEventListener('click', function () {
      box.style.transition = 'none';
      box.style.transform = 'none';
      box.style.opacity = '1';
      void box.offsetWidth;
      if (reduce || active.reduced) { say('reduced motion: replay skipped'); return; }
      box.style.transition = 'transform ' + dur + ' ' + ease + ', opacity ' + dur + ' ' + ease;
      box.style.transform = 'translateY(-6px)';
      box.style.opacity = '0.6';
      window.setTimeout(function () { box.style.transform = 'none'; box.style.opacity = '1'; }, msFrom(dur) + 60);
    });
  });
  function msFrom(d) {
    var m = /^ *([0-9.]+) *(ms|s)? *$/i.exec(String(d));
    if (!m) return 300;
    return m[2] && m[2].toLowerCase() === 's' ? parseFloat(m[1]) * 1000 : parseFloat(m[1]);
  }

  // ---------- live states (input validation, checkout demo)
  var email = document.getElementById('live-email');
  var help = document.getElementById('live-email-help');
  if (email && help) email.addEventListener('blur', function () {
    var v = email.value.trim();
    var ok = v === '' || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v);
    email.setAttribute('aria-invalid', ok ? 'false' : 'true');
    help.textContent = ok ? (v ? 'Looks valid.' : '') : 'Enter a valid email address.';
  });
  var form = document.getElementById('checkout');
  if (form) form.addEventListener('submit', function (e) {
    e.preventDefault();
    var card = document.getElementById('card'), mail = document.getElementById('email'), msg = document.getElementById('card-help');
    var digits = (card.value || '').replace(/\D/g, '');
    var emailOk = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(mail.value || '');
    card.setAttribute('aria-invalid', digits.length >= 12 ? 'false' : 'true');
    mail.setAttribute('aria-invalid', emailOk ? 'false' : 'true');
    msg.textContent = digits.length >= 12 && emailOk ? 'Demo complete — no payment was sent.' : 'Check the card number and email, then try again.';
  });
})();
