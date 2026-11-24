
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
