# lewitt certificate

**Verdict: CERTIFIED** · 14/14 token probes measured · 0 deviation(s) · 0 guardrail hit(s)

- target: `http://127.0.0.1:8765/runs/linear.app/preview.html`
- instructions: `linear.app` (dna.json, schema 1.1)
- re-render: `python3 scripts/cert.py --url http://127.0.0.1:8765/runs/linear.app/preview.html --dest runs/linear.app`
- issued: 2026-11-24T09:17:25+00:00 · pages inspected: 1

> sign this only for the tokens above; unmeasured rows are listed, not assumed

## Deviations first

No deviation on the measured tokens.

## What was measured

| Token | Value in tokens.css | Rendered value | Read from | Result |
| --- | --- | --- | --- | --- |
| `type/display-1` | `64px` | `64px` | probe element | match |
| `type/display-2` | `48px` | `48px` | probe element | match |
| `type/title` | `20px` | `20px` | probe element | match |
| `type/body` | `15px` | `15px` | probe element | match |
| `type/ui` | `13px` | `13px` | probe element | match |
| `type/caption` | `12px` | `12px` | probe element | match |
| `color/canvas` | `#08090A` | `rgb(8, 9, 10)` | probe element | match |
| `color/surface` | `#0F1011` | `rgb(15, 16, 17)` | probe element | match |
| `color/ring` | `#23252A` | `rgb(35, 37, 42)` | probe element | match |
| `color/text/primary` | `#F7F8F8` | `rgb(247, 248, 248)` | probe element | match |
| `color/text/body` | `#D0D6E0` | `rgb(208, 214, 224)` | probe element | match |
| `color/text/muted` | `#8A8F98` | `rgb(138, 143, 152)` | probe element | match |
| `color/action/bg` | `#FFFFFF` | `rgb(255, 255, 255)` | probe element | match |
| `color/action/fg` | `#08090A` | `rgb(8, 9, 10)` | probe element | match |

## Not certified

- this run has no system/ reference site (DNA mode): the wall audited is the page at http://127.0.0.1:8765/runs/linear.app/preview.html, whatever it was served from at issue time
- component geometry (padding, gaps, radii of specific elements) is not probed — only token values are
- spacing scale, motion timing and hover/focus deltas on the live page are not asserted
- visual resemblance to the source site is out of scope: this certificate is about instructions, not screenshots

_A certificate does not replace a design review: it proves the tokens whose values are checkable were applied. Anything this run could not probe is listed above, not assumed._
