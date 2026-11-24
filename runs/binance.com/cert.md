# lewitt certificate

**Verdict: CERTIFIED** · 19/19 token probes measured · 0 deviation(s) · 0 guardrail hit(s)

- target: `http://127.0.0.1:8765/runs/binance.com/system/index.html`
- instructions: `binance.com` (dna.json, schema 1.1)
- re-render: `python3 scripts/cert.py --url http://127.0.0.1:8765/runs/binance.com/system/index.html --dest runs/binance.com`
- issued: 2026-11-24T09:17:10+00:00 · pages inspected: 1

> sign this only for the tokens above; unmeasured rows are listed, not assumed

## Deviations first

No deviation on the measured tokens.

## What was measured

| Token | Value in tokens.css | Rendered value | Read from | Result |
| --- | --- | --- | --- | --- |
| `type/figure` | `72px` | `72px` | probe element | match |
| `type/headline` | `40px` | `40px` | probe element | match |
| `type/title` | `18px` | `18px` | probe element | match |
| `type/ui` | `14px` | `14px` | probe element | match |
| `type/body` | `12px` | `12px` | probe element | match |
| `type/legal` | `8px` | `8px` | probe element | match |
| `color/canvas` | `#181A20` | `rgb(24, 26, 32)` | page --lw-* var | match |
| `color/surface` | `#29313D` | `rgb(41, 49, 61)` | page --lw-* var | match |
| `color/well` | `#1E2329` | `rgb(30, 35, 41)` | page --lw-* var | match |
| `color/border` | `#333B47` | `rgb(51, 59, 71)` | page --lw-* var | match |
| `color/border-strong` | `#3D4452` | `rgb(61, 68, 82)` | page --lw-* var | match |
| `color/text/primary` | `#EAECEF` | `rgb(234, 236, 239)` | page --lw-* var | match |
| `color/text/secondary` | `#929AA5` | `rgb(146, 154, 165)` | page --lw-* var | match |
| `color/text/tertiary` | `#707A8A` | `rgb(112, 122, 138)` | page --lw-* var | match |
| `color/brand` | `#F0B90B` | `rgb(240, 185, 11)` | page --lw-* var | match |
| `color/action/bg` | `#FCD535` | `rgb(252, 213, 53)` | page --lw-* var | match |
| `color/action/fg` | `#202630` | `rgb(32, 38, 48)` | page --lw-* var | match |
| `color/trend/up` | `#2EBD85` | `rgb(46, 189, 133)` | page --lw-* var | match |
| `color/trend/down` | `#F6465D` | `rgb(246, 70, 93)` | page --lw-* var | match |

## Not certified

- component geometry (padding, gaps, radii of specific elements) is not probed — only token values are
- spacing scale, motion timing and hover/focus deltas on the live page are not asserted
- visual resemblance to the source site is out of scope: this certificate is about instructions, not screenshots

_A certificate does not replace a design review: it proves the tokens whose values are checkable were applied. Anything this run could not probe is listed above, not assumed._
