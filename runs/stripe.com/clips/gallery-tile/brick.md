# brick — #gallery-tile

- url: http://127.0.0.1:8768/
- found by: text-exact · trigger `<a>` “See how it works”
- action: **hover** · camera: 1440×900
- instructions: `stripe.com` (dna.json 1.1)
- captured: 2026-11-24T04:14:50+00:00

## States

| State | geometry | opacity | transform | transitions running |
| --- | --- | --- | --- | --- |
| before | [433, 60, 353, 288] | 1 | none | 0 |
| during | [433, 55, 353, 288] | 1 | matrix(1, 0, 0, 1, 0, -5.16169) | 2 |
| settled | [433, 54, 353, 288] | 1 | matrix(1, 0, 0, 1, 0, -5.9902) | 2 |
| after | [433, 60, 353, 288] | 1 | none | 0 |

## Deltas

- **module.hover** · `rect`: `[433, 60, 353, 288]` → `[433, 55, 353, 288]`
- **module.hover** · `transform`: `none` → `matrix(1, 0, 0, 1, 0, -5.16169)`
- **module.hover** · `box-shadow`: `none` → `rgba(50, 50, 93, 0.082) 0px 10.657px 21.314px 0px`
- **module.settled** · `rect`: `[433, 60, 353, 288]` → `[433, 54, 353, 288]`
- **module.settled** · `transform`: `none` → `matrix(1, 0, 0, 1, 0, -5.9902)`
- **module.settled** · `box-shadow`: `none` → `rgba(50, 50, 93, 0.118) 0px 15.7356px 31.4711px 0px`
- **stateful.open**: no computed change
- **stateful.closed**: no computed change

## Skin mapping (stripped)

- `background`: source `rgb(248, 250, 253)` → slot `color/surface-subtle` (`var(--lw-surface-subtle)` = `#F8FAFD`, Δ0.0)
- `color`: source `rgb(80, 97, 122)` → slot `color/text/body` (`var(--lw-text-body)` = `#50617A`, Δ0.0)

## State machine

- **idle → hover**: pointer enters the module (CSS :hover or pointer handlers) (observed: True)
- **hover → settled**: transition finishes; nothing else moves (observed: True)
- **settled → idle**: pointer leaves the module; every computed value returns to baseline (observed: True)

## Implementation notes

- Drive the state with a class the project owns (e.g. `is-open`), never with source-site classes.
- Animate only the properties that changed: box-shadow, rect, transform.
- Use the source's transition string for timing; replace colours and faces with the mapped slots above.
- Keep the geometry contract: the module's box is [433, 60, 353, 288]. Layout inside it may change, the box may not.
- If a property did not change in the recording, do not invent a transition for it.

## Content skeleton (no skin)

| tag | role | text |
| --- | --- | --- |
| `h3` | h3 | Gallery tile |
| `a` | a | See how it works |

## Cleanup

- Remove any injected helper styles before leaving the page.
- Close any window an activation opened; the recording never submits forms or logs in.
- Keep shots/ next to brick.md so the geometry can be re-checked after implementation.

_A brick is instructions, not a clone: the geometry, timing and state machine come from the source; colour and type come from your project's slots._
