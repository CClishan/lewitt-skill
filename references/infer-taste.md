# Step 3 — Taste (推理品味)

Taste is visible in **trade-offs**. Each principle answers: what did this designer deliberately
choose, and what plausible alternative did they reject?

Inputs: Step 1 measurements + Step 2 patterns.

## The test that kills slop

For every candidate, ask: *could I have written this without ever seeing this specific site?*
If yes, delete it. A principle must be falsifiable: cite values that would break it if changed.

## Three kinds

- **restraint** — something the designer could have added and refused (no accent hue, no shadow
  ladder, no second font, no card chrome, no illustration).
- **craft** — effort spent on subtle refinement (tinted greys, concentric radii, tuned tracking,
  mathematical spacing).
- **system** — a consistency rule chosen over local optimisation (two-band type scale, strict
  palette, one radius family).

At least one principle must be `restraint`. Restraint is usually the strongest signal and it is
the only kind that can be turned into an enforceable guardrail.

## Entry shape

```json
{
  "id": "t-white-as-accent",
  "name": "Brand lives in white, not in colour",
  "kind": "restraint",
  "status": "observed",
  "trigger": "Deciding the action colour on a near-black marketing page.",
  "decision": "Use white on #08090A for the only high-contrast action; everything else grey.",
  "chose": "white-on-black primary action",
  "over": "a branded accent hue across CTAs, links and states",
  "reason": "On #08090A a white pill is already the loudest element; a coloured button reads as a template and competes with the product screenshot.",
  "evidence": ["e-nav-cta", "e-text-pink-hero"],
  "patterns": ["p-accent-restraint"],
  "guardrail": {
    "forbidCss": [],
    "forbidClass": ["(^|-)bg-(?!white|black|transparent|gray|neutral|zinc|slate|none)[a-z]+-(4|5|6|7)\\d\\d$"],
    "max": {},
    "note": "Saturated fills belong to illustration only, never to a control."
  }
}
```

Rules:

- `chose` and `over` must both be defensible choices another designer would really make. "Chose
  readable text over unreadable text" is not a trade-off.
- `reason` states a human effect (attention, rest, trust, speed), not an industry platitude.
- cite both `evidence` (ids that exist) and `patterns` (ids that exist).
- produce 4–6 candidates first, one line each, then keep the best 3–4.

## Guardrails — the executable exit

Every `restraint` must carry a `guardrail`, otherwise the principle is decorative prose and
`build_artifacts.py` rejects it. Keys:

| Key | Values | Meaning |
| --- | --- | --- |
| `forbidCss` | `["background-image"]` | CSS properties that must not appear (prefix match: `box-shadow` also blocks `box-shadow-color`) |
| `requireCss` | `["box-shadow"]` | properties that must appear at least once |
| `forbidClass` | regex list | class names that must not appear (Tailwind or BEM) |
| `max` | `{"box-shadow": {"value": "0", "unit": "px"}}` | upper bound on **every** geometric length of that property; for shadows this caps offset, blur and spread together |
| `note` | string | one line of human context |

Choose the narrowest guardrail that still catches the realistic mistake:

- no accent → `forbidCss: ["background-image", "box-shadow-color"]` is too broad; use the
  `forbidClass` colour-regex above, or list the exact gradient/image properties you forbid;
- rings instead of shadows → `max.box-shadow = 0px` (Linear) or `1px` (hairline rings allowed);
- no second font → `forbidClass: ["font-(serif|display|mono-[a-z]+)$"]` only if the site truly
  forbids it;
- if you cannot express it mechanically, the principle is `craft`/`system`, not `restraint`.

Guardrails are checked against generated UI with `lint_output.py --check-code <dir>`. A guardrail
that never fires is untested: include at least one deliberately wrong snippet mentally, or test
with a throwaway file before shipping.

## Banned vocabulary

`clean, modern, sleek, visually appealing, user-friendly, intuitive, seamless, elegant,
minimalist, polished, refined, sophisticated, delightful, stunning, beautiful, premium` — allowed
only as an explicit foil ("could have gone 'clean and modern', but…"). `lint_output.py` greps
for them; passing it is mandatory, and `grep` is the check, not memory.

## Output marker

Begin with `### Step 3 Output — Taste Principles (candidates → final)`.
