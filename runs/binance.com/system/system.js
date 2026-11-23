// lewitt system/ — local interactions only. No network calls, nothing submitted to the source site.
(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // --- primary CTA: real local state change, announced
  var cta = document.getElementById('cta-signup');
  var ctaStatus = document.getElementById('cta-status');
  if (cta && ctaStatus) {
    cta.addEventListener('click', function () {
      var signed = cta.dataset.signed === '1';
      cta.dataset.signed = signed ? '0' : '1';
      cta.textContent = signed ? 'Sign Up' : 'Signed up (demo)';
      ctaStatus.textContent = signed ? 'Signed out again.' : 'Sign-up recorded locally — demo only, nothing was sent.';
    });
  }

  // --- market tabs: roving focus, arrow keys, aria-selected
  var tablist = document.getElementById('mkt-tabs');
  if (tablist) {
    var tabs = Array.prototype.slice.call(tablist.querySelectorAll('[role="tab"]'));
    function select(i, focus) {
      tabs.forEach(function (t, j) {
        var on = i === j;
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        t.tabIndex = on ? 0 : -1;
        var panel = document.getElementById(t.getAttribute('aria-controls'));
        if (panel) panel.hidden = !on;
        if (on && focus) t.focus();
      });
    }
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { select(i, false); });
      t.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
          e.preventDefault();
          var next = e.key === 'ArrowRight' ? (i + 1) % tabs.length : (i - 1 + tabs.length) % tabs.length;
          select(next, true);
        } else if (e.key === 'Home') { e.preventDefault(); select(0, true); }
        else if (e.key === 'End') { e.preventDefault(); select(tabs.length - 1, true); }
      });
    });
  }

  // --- convert: real computed output instead of a static fake
  var from = document.getElementById('from');
  var to = document.getElementById('to');
  var convert = document.getElementById('convert');
  var convertStatus = document.getElementById('convert-status');
  if (from && to && convert) {
    var RATE = 1; // 1 BTC -> RATE ETH-equivalent placeholder rate, labelled below
    convert.addEventListener('click', function () {
      var n = parseFloat(String(from.value).replace(/[^0-9.]/g, ''));
      if (!isFinite(n) || n <= 0) {
        to.value = '—';
        convertStatus.textContent = 'Enter an amount above 0 to preview.';
        convert.setAttribute('aria-invalid', 'false');
        from.setAttribute('aria-invalid', 'true');
        return;
      }
      from.removeAttribute('aria-invalid');
      to.value = (n * RATE).toFixed(8) + ' ETH';
      convertStatus.textContent = 'Rate ' + RATE + ' (demo rate, not a quote).';
    });
  }

  // --- motion replays; reduced motion collapses them
  function replay(id, el, frames) {
    var btn = document.getElementById(id);
    if (!btn || !el) return;
    btn.addEventListener('click', function () {
      el.style.transition = 'none';
      el.style.transform = 'translateX(0)';
      void el.offsetWidth;
      if (reduce) return;
      el.style.transition = frames;
      el.style.transform = frames.indexOf('700ms') > -1 ? 'translateX(24px)' : 'translateY(-2px)';
      window.setTimeout(function () { el.style.transform = ''; }, 720);
    });
  }
  replay('replay-panel', document.getElementById('panel-demo'),
    'transform var(--lw-motion-panel) var(--lw-easing-panel)');
  var primary = document.querySelector('.ds-btn--primary');
  replay('replay-hover', primary, 'background-color var(--lw-motion-hover) var(--lw-easing-standard)');
  replay('replay-micro', document.querySelector('.ds-tab'), 'color var(--lw-motion-micro) linear');
})();
