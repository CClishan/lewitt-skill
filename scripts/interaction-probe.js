// ---------- interaction probe (phase B) ----------
// Called three times by the driver with a shared plan, because hover needs the real mouse from
// Node while style reads happen in the page:
//   mode "plan"     -> step list: [{action:"snapshot"|"hover"|"away", ...}]
//   window.lewittSnapshot(locator) -> computed values for the diffed properties
//   window.lewittInteractionReport(measured, steps) -> grouped deltas per target
// Only these properties are diffed: background-color, color, border-color, box-shadow, outline, transform.
window.lewittInteractionProbe = function (targets, mode) {
  if (mode !== "plan") return [];
  const steps = [];
  let i = 0;
  let skipped = 0;
  for (const t of targets || []) {
    const el = (() => { try { return document.querySelector(t.locator); } catch (e) { return null; } })();
    if (!el) { skipped++; continue; }
    el.scrollIntoView({ block: "center", inline: "center" });
    const r = el.getBoundingClientRect();
    const x = Math.round(r.left + r.width / 2);
    const y = Math.round(r.top + r.height / 2);
    const base = { index: i, locator: t.locator, kind: t.kind, x, y };
    steps.push({ ...base, action: "snapshot", phase: "before" });
    steps.push({ ...base, action: "hover", wait: 320 });
    steps.push({ ...base, action: "snapshot", phase: "hover" });
    steps.push({ ...base, action: "away", x: 2, y: 2, wait: 200 });
    steps.push({ ...base, action: "focus", wait: 260 });   // focus happens inside the page
    steps.push({ ...base, action: "snapshot", phase: "focus" });
    i++;
  }
  return steps;
};

window.lewittFocus = function (locator) {
  const el = (() => { try { return document.querySelector(locator); } catch (e) { return null; } })();
  if (!el || !el.matches("button, a[href], input, textarea, select, [tabindex]")) return { focused: false };
  el.focus({ preventScroll: true });
  return { focused: true, focusVisible: el.matches(":focus-visible") };
};

window.lewittSnapshot = function (locator) {
  const PROPS = ["background-color", "color", "border-color", "box-shadow", "outline", "transform"];
  const el = (() => { try { return document.querySelector(locator); } catch (e) { return null; } })();
  if (!el) return null;
  const s = getComputedStyle(el);
  const out = { rect: null, focusVisible: el.matches(":focus-visible") };
  const r = el.getBoundingClientRect();
  out.rect = [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)];
  for (const p of PROPS) out[p] = s.getPropertyValue(p);
  out.transition = s.transition.slice(0, 160);
  return out;
};

window.lewittInteractionReport = function (measured, steps) {
  // steps: the plan the driver executed (see lewittInteractionProbe)
  const byIndex = {};
  for (const m of measured) {
    const step = steps.find((s) => s.locator === m.locator && s.phase === m.phase);
    if (!step) continue;
    byIndex[step.index] = byIndex[step.index] || { locator: m.locator, kind: step.kind, phases: {} };
    byIndex[step.index].phases[m.phase] = m.values;
  }
  const diff = (a, b) => {
    const d = {};
    if (!a || !b) return d;
    for (const k of Object.keys(a)) {
      if (k === "rect" || k === "transition" || k === "focusVisible") continue;
      if (a[k] !== b[k]) d[k] = [a[k], b[k]];
    }
    return d;
  };
  return {
    method: "cdp-mouse hover + element.focus() + getComputedStyle diff",
    targets: Object.values(byIndex).map((t) => ({
      locator: t.locator, kind: t.kind, available: !!t.phases.before,
      before: t.phases.before || null,
      hover: { delta: diff(t.phases.before, t.phases.hover) },
      focus: { delta: diff(t.phases.before, t.phases.focus), focusVisible: t.phases.focus ? t.phases.focus.focusVisible : null },
    })),
  };
};
