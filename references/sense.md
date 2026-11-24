# Sense — capture with an honest evidence ledger

## Isolation is a correctness requirement

A design analysis run in a logged-in browser captures the wrong surface: linear.app becomes the
app dashboard, not the marketing page. So capture must start from a fresh context.

`scripts/capture.py` enforces this:

- order of preference: **node playwright** (`launchPersistentContext` in a temp profile, CDP
  `Runtime.evaluate`) → an **external driver** you provide (`--driver` / `DD_CAPTURE_CMD`, which
  must promise a fresh context and speak `open / eval / shot`);
- no silent fallback: no driver, no capture. `capture/meta.json` records
  `captureIsolated: true` only when the driver really is isolated;
- if a non-isolated path is ever used, set `meta.captureIsolated: false` **and**
  `meta.isolationNote` — `build_artifacts.py` rejects an undisclosed non-isolated run.

Evaluation goes through CDP on purpose: `page.evaluate(string)` proved unreliable across
Playwright versions/agent transport (`undefined` with no error), which is exactly the kind of
silent failure that produces a beautiful, empty report. `eval_cdp.js` returns the value or
raises the page exception.

## Capture budget

Entry page + up to 3 additional public same-origin pages (depth ≤ 2), chosen from real nav
links, skipping auth/checkout paths. Pick one representative per visible family (product,
pricing, customers, docs, changelog). Stop early when two consecutive pages add no new component,
layout, asset, or behaviour family. Report the unvisited queue — never call a sample "the whole
site". A user-requested exhaustive crawl overrides this; say so in `meta.crawl.budget`.

## What the driver writes

| File | Use |
| --- | --- |
| `capture/dom.json` | extract.js payload of the main page (values, distributions, errors[]) |
| `capture/dom-N.json` | same for extra pages |
| `capture/viewport.png` | 1440×900 — the composition reference |
| `capture/fullpage.png` | only if page ≤ 6 viewport heights; otherwise absent by design |
| `capture/meta.json` | driver, isolation, pages, capturedAt, viewport, extract errors |
| `dom.json > interactions` | forced hover / focus-visible before→after values per representative |

`extract.js` measures only: colours with `areaPct`, text-colour counts, accent candidates,
font families, heading styles, size/weight/spacing distributions, radii, shadows, transitions,
cards, images, section gaps, largest grid, button typography, `:focus-visible` and
`prefers-reduced-motion` presence, plus `errors[]` per section and a 60KB trim guard. If a
section fails, its measurements are `inferred` from the screenshot or `unknown` — never invented.

## Interaction probe

After the measurement pass, `capture_node.js` picks up to five representatives (2 buttons, 1 link,
1 card, 1 input) from `dom.json > interactionTargets`, then:

1. scrolls each into view and dispatches a **real** `Input.dispatchMouseEvent` move to its centre;
2. reads the diffed properties after the transition settles, then moves the mouse away;
3. calls `element.focus()` (checks `:focus-visible` too) and reads again.

Only `background-color, color, border-color, box-shadow, outline, transform` are compared; the
method string in the payload records what was done. Hover is skipped when the page reports
`(hover: none)`. If the probe fails, `interactions.error` says why and you record nothing rather
than guessing.

## Screenshot vs DOM: how to resolve

| Question | Verdict source |
| --- | --- |
| Exact value (px, hex, ratio, duration) | DOM / computed style |
| What dominates the page, section boundaries, imperceptible shadows | screenshot |
| Is this colour a brand colour? | both: in DOM **and** ≥ ~5% visible surface |
| Are these two elements one component? | screenshot first, DOM confirms |

When they disagree, record it: add an evidence entry with `"method": "screenshot+screenshot-dom
conflict"`, keep both values, and say which one the recommendation follows.

## Evidence ledger

Every `observed`/`inferred` claim points at an evidence id:

```json
{
  "id": "e-nav-cta",
  "url": "https://linear.app/",
  "locator": "top-right primary action (Sign up)",
  "viewport": {"width": 1440, "height": 900},
  "state": "default",
  "method": "computed-style+viewport-screenshot",
  "capturedAt": "2026-11-23T10:51:27+00:00",
  "values": {"bg": "rgb(255,255,255)", "text": "rgb(8,9,10)"},
  "status": "observed",
  "artifact": "capture/viewport.png",
  "limitations": []
}
```

- `id` is stable and semantic (`e-<where>-<what>`); ids are never reused for a different fact.
- `state` is `default | hover | focus | pressed | disabled | open | empty | error` — say what you
  actually forced. A hover screenshot does not prove keyboard behaviour.
- `artifact` is a real path or `null`. Never invent one.
- Exclude credentials, session ids, private content.
- Incremental runs keep frozen evidence verbatim; new evidence gets new ids.

## States and motion you may probe

Safe: hover, focus-visible, open a menu/disclosure/tab, scroll. **Do not** submit forms, buy,
change account data, or log in. Unreachable state = `unknown`, listed in `meta.limitations`.

## When capture is degraded

| Case | Do |
| --- | --- |
| `dom.json` missing or empty | Stop. Capture failed (`capture.py` exits non-zero); do not author `dna.json`. |
| `dom.errors` non-empty | Mark the affected measurements `inferred`, cite the screenshot, list sections in `meta.limitations`. |
| Truncated payload | Low-signal fields were trimmed; note it, prefer `sizeDistribution` / `radii` / `shadows` top-N. |
| Cloudflare / verify wall | Report; ask for alternative page or screenshots. No fictional system. |
| Only screenshots available | ~approx every geometry value, `unknown` for CSS declarations and behaviour. |
