# lewitt certificate

**Verdict: CERTIFIED** · 16/16 token probes measured · 0 deviation(s) · 0 guardrail hit(s)

- target: `http://127.0.0.1:8765/`
- instructions: `stripe.com` (dna.json, schema 1.1)
- issued: 2026-11-24T07:57:13+00:00 · pages inspected: 1

> sign this only for the tokens above; unmeasured rows are listed, not assumed

## Deviations first

No deviation on the measured tokens.

## What was measured

| Token | Value in tokens.css | Rendered value | Read from | Result |
| --- | --- | --- | --- | --- |
| `type/hero` | `48px` | `48px` | rendered element | match |
| `type/h2` | `32px` | `32px` | page --lw-* var | match |
| `type/h3` | `26px` | `26px` | page --lw-* var | match |
| `type/body` | `16px` | `16px` | page --lw-* var | match |
| `type/ui` | `15px` | `15px` | page --lw-* var | match |
| `type/caption` | `10px` | `10px` | page --lw-* var | match |
| `color/canvas` | `#FFFFFF` | `rgb(255, 255, 255)` | page --lw-* var | match |
| `color/canvas-tint` | `#F6F9FC` | `rgb(246, 249, 252)` | page --lw-* var | match |
| `color/surface-subtle` | `#F8FAFD` | `rgb(248, 250, 253)` | page --lw-* var | match |
| `color/text/heading` | `#061B31` | `rgb(6, 27, 49)` | page --lw-* var | match |
| `color/text/body` | `#50617A` | `rgb(80, 97, 122)` | page --lw-* var | match |
| `color/text/muted` | `#64748D` | `rgb(100, 116, 141)` | page --lw-* var | match |
| `color/action/bg` | `#533AFD` | `rgb(83, 58, 253)` | page --lw-* var | match |
| `color/action/bg-alt` | `#635BFF` | `rgb(99, 91, 255)` | page --lw-* var | match |
| `color/action/fg` | `#FFFFFF` | `rgb(255, 255, 255)` | page --lw-* var | match |
| `color/link` | `#533AFD` | `rgb(83, 58, 253)` | page --lw-* var | match |

## Not certified

- component geometry (padding, gaps, radii of specific elements) is not probed — only token values are
- spacing scale, motion timing and hover/focus deltas on the live page are not asserted
- visual resemblance to the source site is out of scope: this certificate is about instructions, not screenshots

_A certificate does not replace a design review: it proves the tokens whose values are checkable were applied. Anything this run could not probe is listed above, not assumed._
