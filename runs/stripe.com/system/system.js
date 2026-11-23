// lewitt system/ — local interaction only. No network calls, nothing is submitted to the source site.
(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- motion replay (uses the token durations declared in the page)
  Array.prototype.forEach.call(document.querySelectorAll('[data-replay]'), function (btn) {
    var box = document.getElementById(btn.getAttribute('data-replay'));
    if (!box) return;
    var dur = btn.getAttribute('data-dur'), ease = btn.getAttribute('data-ease');
    btn.addEventListener('click', function () {
      box.style.transition = 'none';
      box.style.transform = 'none';
      box.style.opacity = '1';
      void box.offsetWidth;
      if (reduce) return;
      box.style.transition = 'transform ' + dur + ' ' + ease + ', opacity ' + dur + ' ' + ease;
      box.style.transform = 'translateY(-6px)';
      box.style.opacity = '0.6';
      window.setTimeout(function () { box.style.transform = 'none'; box.style.opacity = '1'; }, parseFloat(dur) * 1000 + 60);
    });
  });

  // ---- live email validation (real invalid state, not a forced sample)
  var email = document.getElementById('live-email');
  var help = document.getElementById('live-email-help');
  if (email) {
    email.addEventListener('blur', function () {
      var v = email.value.trim();
      var ok = v === '' || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v);
      email.setAttribute('aria-invalid', ok ? 'false' : 'true');
      help.textContent = ok ? (v ? 'Looks valid.' : '') : 'Enter a valid email address.';
    });
  }

  // ---- checkout demo: local validation, nothing submitted
  var form = document.getElementById('checkout');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var card = document.getElementById('card'), mail = document.getElementById('email'), msg = document.getElementById('card-help');
      var digits = (card.value || '').replace(/\D/g, '');
      var emailOk = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(mail.value || '');
      card.setAttribute('aria-invalid', digits.length >= 12 ? 'false' : 'true');
      mail.setAttribute('aria-invalid', emailOk ? 'false' : 'true');
      msg.textContent = digits.length >= 12 && emailOk
        ? 'Demo complete — no payment was sent.'
        : 'Check the card number and email, then try again.';
    });
  }

  // ---- stress toggles
  var stage = document.getElementById('stage');
  var inner = document.getElementById('stage-inner');
  function apply() {
    if (!stage) return;
    var on = Array.prototype.filter.call(stage.querySelectorAll ? [stage] : [], Boolean);
    var flags = [];
    Array.prototype.forEach.call(document.querySelectorAll('[data-stress-toggle]'), function (b) {
      if (b.getAttribute('aria-pressed') === 'true') flags.push(b.getAttribute('data-stress-toggle'));
    });
    stage.setAttribute('data-stress', flags.join(' '));
  }
  Array.prototype.forEach.call(document.querySelectorAll('[data-stress-toggle]'), function (btn) {
    btn.addEventListener('click', function () {
      var on = btn.getAttribute('aria-pressed') === 'true';
      btn.setAttribute('aria-pressed', on ? 'false' : 'true');
      apply();
    });
  });
  var v390 = document.getElementById('viewport-390');
  if (v390 && inner) {
    v390.addEventListener('click', function () {
      var on = v390.getAttribute('aria-pressed') === 'true';
      v390.setAttribute('aria-pressed', on ? 'false' : 'true');
      inner.style.width = on ? '' : '390px';
      inner.style.margin = on ? '' : '0 auto';
    });
  }
})();
