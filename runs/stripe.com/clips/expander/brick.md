# brick — #exp

- url: http://127.0.0.1:8768/
- found by: selector · trigger `<button>` “Show details”
- action: **toggle** · camera: 1440×900
- instructions: `stripe.com` (dna.json 1.1)
- captured: 2026-11-24T04:11:36+00:00

## States

| State | geometry | opacity | transform | transitions running |
| --- | --- | --- | --- | --- |
| before | [60, 388, 1320, 113] | 1 | none | 0 |
| before_target | [76, 485, 1288, 0] | 1 | none | 0 |
| during | [76, 485, 1288, 50] | 1 | none | 1 |
| after | [76, 485, 1288, 50] | 1 | none | 0 |
| restored | [76, 485, 1288, 0] | 1 | none | 0 |

## Deltas

- **module.hover**: no computed change
- **module.settled**: no computed change
- **stateful.open** · `rect`: `[76, 485, 1288, 0]` → `[76, 485, 1288, 50]`
- **stateful.closed**: no computed change

## Skin mapping (stripped)

- `background`: source `rgb(248, 250, 253)` → slot `color/action/fg` (`var(--lw-action-fg)` = `#FFFFFF`, Δ7.0)
- `color`: source `rgb(80, 97, 122)` → slot `color/action/bg` (`var(--lw-action-bg)` = `#533AFD`, Δ131.0)
- `background_during`: source `rgba(0, 0, 0, 0)` → slot `color/canvas` (`var(--lw-canvas)` = `#FFFFFF`, Δ0.0)

## State machine

- **idle → open**: click (or keyboard equivalent) on the trigger (observed: True)
- **open → idle**: second click, Escape, or click outside (observed: True)

## Implementation notes

- Drive the state with a class the project owns (e.g. `is-open`), never with source-site classes.
- Animate only the properties that changed: background, border-radius, rect.
- Use the source's transition string for timing; replace colours and faces with the mapped slots above.
- Keep the geometry contract: the module's box is [60, 388, 1320, 113]. Layout inside it may change, the box may not.
- If a property did not change in the recording, do not invent a transition for it.

## Content skeleton (no skin)

| tag | role | text |
| --- | --- | --- |
| `button` | button | Show details |
| `p` | p | Panel content here. |

## Cleanup

- Remove any injected helper styles before leaving the page.
- Close any window an activation opened; the recording never submits forms or logs in.
- Keep shots/ next to brick.md so the geometry can be re-checked after implementation.

_A brick is instructions, not a clone: the geometry, timing and state machine come from the source; colour and type come from your project's slots._
