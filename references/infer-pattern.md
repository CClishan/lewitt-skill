# Step 2 — Pattern (找规律)

Turn measurements into **governed rules**, not observations. "H1 is 64px" is a measurement;
"display sizes jump from 16px straight to 48/64 with nothing between" is a pattern.

Inputs: Step 1 measurements. No screenshot needed — this step works on numbers.

## What qualifies

A pattern holds **across** the surface: repetition, ratio, constraint, or a deliberate absence.
It must cite measurements (by id or value). If you cannot tie it to numbers, drop it.

## Categories to look through

1. **Layout density** — sparse vs dense; whitespace per content unit.
2. **Spacing rhythm** — strict base unit? ratio of small : medium : large gaps?
3. **Type system** — ramp ratio, two-band jump, count of sizes.
4. **Hierarchy carriers** — size, weight, colour, or position; which does the work?
5. **Colour restraint** — where saturated colour is allowed and where it is refused.
6. **Depth system** — rings vs shadows, consistency across similar components.
7. **Card usage** — cards only where content is comparable/actionable, or as the default box?
8. **Section rhythm** — breathing room inside vs between sections; divider strategy.
9. **Media role** — decorative, atmospheric, functional, or product-as-illustration.
10. **Alignment** — dominant alignment, and whether it changes per section deliberately.
11. **Motion quality** — only transform/opacity? feedback-only or decorative? reduced motion?
12. **Absences** — what comparable sites do that this one does not (this feeds step 3).

## Entry shape

```json
{"id": "p-ui-band", "name": "Tight UI band, wide display jumps",
 "rule": "86% of text sits in 12–16px; display sizes jump straight to 20/32/48/64.",
 "goal": "Treats UI chrome as one texture and the marketing headline as a poster line.",
 "evidence": ["e-size-dist", "e-size-dist-pricing"]}
```

Rules:

- 5–8 patterns; more is noise, fewer misses the system;
- `rule` one sentence, `goal` states the function for the reader — not philosophy;
- every entry cites at least one evidence id that exists;
- cross-page agreement outranks single-page evidence — say so in `rule` when it applies.

## Output marker

Begin with `### Step 2 Output — Patterns`.
