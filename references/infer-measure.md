# Step 1 — Measure (量体)

You are a meter, not a critic. Produce **what** and **how much**, never **why**. Each finding
becomes one `measurements[]` entry with exact values and the evidence ids that prove it.

Inputs: `capture/dom.json` (+ `dom-N.json`) and the screenshots. If a number exists only in the
screenshot, write `~approx` and mark the entry `inferred`.

## Categories (17)

Write only the categories the page actually exercises; mark the rest absent explicitly.

1. **Color roles** — canvas, raised surface, overlay, border/ring, and their share of sampled
   area (`areaPct`). Separate colours under ~5% surface as decorative.
2. **Text colours** — primary / body / muted / disabled, with usage counts.
3. **Accent surface** — total share of saturated colour on controls; list what an accent is
   actually used for (never "brand colour" unless it appears as a control background).
4. **Font families** — every family and where it appears; note the rendered family when
   computed `font-family` lists differ from what visibly renders.
5. **Type scale** — every distinct size with role and count; state whether it is a ramp, two
   bands, or arbitrary.
6. **Line height & measure** — display and body line heights; any `ch`/`max-width` measure.
7. **Weights** — every distinct weight with count; note sub-400 or variable weights.
8. **Tracking** — letter-spacing at display vs body, in px and as % of size.
9. **Radii** — every radius value, which component uses it, and parent/child pairs (nested).
10. **Depth** — every shadow: layers, offset, blur, spread, alpha, tint (pure black vs tinted);
    classify as ring / inset / soft float / imperceptible (≤3% alpha).
11. **Spacing** — base unit, the actual distribution, and whether gaps come from `gap` or
    margins.
12. **Layout width & grid** — container max-width or fluidity, column templates, gutters.
13. **Section rhythm** — vertical gaps between consecutive sections; whether breathing space is
    inside sections (padding) or between them (margin).
14. **Media** — image/card aspect ratios, role (hero / feature / thumbnail), crops.
15. **Motion** — properties animated, duration(s), easing, reduced-motion branch.
16. **Interaction affordances** — `:focus-visible` vs `:focus`, touch targets, state carried in
    the URL, disabled/loading treatments.
17. **Component inventory** — what actually repeats (buttons, cards, badges, nav items) and
    whether their geometry is consistent.

## Entry shape

```json
{"id": "m-bg", "category": "Color / canvas",
 "value": "rgb(8, 9, 10) = #08090A",
 "status": "observed", "evidence": ["e-home-bg", "e-pricing-bg"]}
```

Rules:

- values are strings with units (`64px`, `-0.022em`, `1.6`, `#08090A`, `232px 1072px`);
- max 5 most significant values per entry — this is a report, not a dump;
- a distribution beats a single sample (`12px x186, 14px x180, 13px x121`);
- conflicting pages keep both values and say which won;
- no adjectival summary inside `value`; the words belong in patterns.

## Output marker

Begin with `### Step 1 Output — Measurements`, then the entries. Stop. Do not infer intent.
