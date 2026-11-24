# brick — Start a Demo · hero CTA (`.hero_cta a`)

> **Slot system: `shadcn`** — every colour and radius below is written as a shadcn / Tailwind v4 variable (`var(--card)`, `var(--muted)`…). Copying the source's hardcoded hex or rgb values into your project is a **hard violation**: re-run `lewitt cert` and it will reject the build.

- url: https://www.steno.ai/
- found by: class-component:hero_cta > a · trigger `<a>` “Start a Demo”
- action: **hover** · camera: 1440×900
- instructions: none — standalone clip, skin mapping by role
- slot source: shadcn / Tailwind v4 slots, mapped by role
- captured: 2026-11-24T10:59:20+00:00
- conclusion: **observed** (4 computed change(s) recorded)

## States

| State | geometry | opacity | transform | transitions running | duration |
| --- | --- | --- | --- | --- | --- |
| before · trigger `a` | [40, 653, 148, 56] | 0.9967 | matrix(1, 0, 0, 1, 0, 0.1041 | 0 | 0ms |
| before · module `div` | [40, 191, 432, 518] | 1 | none | 0 | 0ms |
| before · hovered element `div` | [75, 387, 43, 77] | 1 | none | 0 | 0ms |
| before · stateful `div` | [40, 653, 148, 56] | 1 | none | 0 | 0ms |
| during · trigger `a` | [40, 652, 148, 56] | 1 | matrix(1, 0, 0, 1, 0, 0) | 0 | 0ms |
| during · module `div` | [40, 191, 432, 518] | 1 | none | 0 | 0ms |
| during · hovered element `div` | [75, 387, 43, 77] | 1 | none | 0 | 0ms |
| during · stateful `div` | [40, 652, 148, 56] | 1 | none | 0 | 0ms |
| settled · trigger `a` | [40, 652, 148, 56] | 1 | matrix(1, 0, 0, 1, 0, 0) | 0 | 0ms |
| settled · module `div` | [40, 191, 432, 518] | 1 | none | 0 | 0ms |
| settled · hovered element `div` | [75, 387, 43, 77] | 1 | none | 0 | 0ms |
| settled · stateful `div` | [40, 652, 148, 56] | 1 | none | 0 | 0ms |
| after · trigger `a` | [40, 652, 148, 56] | 1 | matrix(1, 0, 0, 1, 0, 0) | 0 | 0ms |
| after · module `div` | [40, 191, 432, 518] | 1 | none | 0 | 0ms |
| after · hovered element `div` | [75, 387, 43, 77] | 1 | none | 0 | 0ms |
| after · stateful `div` | [40, 652, 148, 56] | 1 | none | 0 | 0ms |

## Deltas

- **module.hover** · trigger · `rect`: `[40, 653, 148, 56]` → `[40, 652, 148, 56]`
- **module.hover** · trigger · `opacity`: `0.9967` → `1`
- **module.hover** · trigger · `transform`: `matrix(1, 0, 0, 1, 0, 0.1041)` → `matrix(1, 0, 0, 1, 0, 0)`
- **module.hover** · stateful · `rect`: `[40, 653, 148, 56]` → `[40, 652, 148, 56]`
- **module.settled** · trigger · `rect`: `[40, 653, 148, 56]` → `[40, 652, 148, 56]`
- **module.settled** · trigger · `opacity`: `0.9967` → `1`
- **module.settled** · trigger · `transform`: `matrix(1, 0, 0, 1, 0, 0.1041)` → `matrix(1, 0, 0, 1, 0, 0)`
- **module.settled** · stateful · `rect`: `[40, 653, 148, 56]` → `[40, 652, 148, 56]`
- **stateful.open**: no computed change
- **stateful.closed**: no computed change

## Skin mapping (stripped)

- `surface`: source `rgba(0, 0, 0, 0)` → `var(--card)` — the module is a passive block: card surface
- `text`: source `rgb(40, 39, 36)` → `var(--card-foreground)` — body text inside a card
- `radius`: source `0px` → `var(--radius)` — shadcn derives every control radius from --radius

## State machine

- **idle → hover**: pointer enters the module (CSS :hover or pointer handlers) (observed: True)
- **hover → settled**: transition finishes; nothing else moves (observed: True)
- **settled → idle**: pointer leaves the module; every computed value returns to baseline (observed: False)

## Reduced motion

- emulated with CDP `Emulation.setEmulatedMedia` `prefers-reduced-motion: reduce` (matchMedia in page: True)
- status: **not-degraded** — ⚠️ **not degraded — the source keeps moving**
- detail: same motion under reduce: 0ms → 0ms, travel 0px → 32px

| Recording | duration | travel (translateY) | transform |
| --- | --- | --- | --- |
| normal | 0ms | 0px | `matrix(1, 0, 0, 1, 0, 0)` |
| reduced | 0ms | 32px | `matrix(1, 0, 0, 1, 0, 32)` |

> The source does not honour `prefers-reduced-motion` here. Your implementation must — either drop the transition or keep the end state and remove the travel. This is a place to improve on the source, not to copy it.

## Implementation notes

- Drive the state with a class the project owns (e.g. `is-open`), never with source-site classes.
- Animate only the properties that changed: opacity, rect, transform.
- Use the source's transition string for timing; take colours from the mapped slots, never from the source.
- Keep the geometry contract: the module's box is None. Layout inside it may change, the box may not.
- If a property did not change in the recording, do not invent a transition for it.
- The source ignores prefers-reduced-motion: implement the reduce branch yourself.

## Content skeleton (no skin)

| tag | role | text |
| --- | --- | --- |
| `div` | div | — Tony Robbins |
| `h1` | h1 | Influence everywhere. All at once. |
| `p` | p | We create AI Twins that turn personal brands into personal r |
| `div` | div | Watch Tony |
| `span` | span | Start a Demo |

## Cleanup

- Remove any injected helper styles before leaving the page.
- Close any window an activation opened; the recording never submits forms or logs in.
- Keep shots/ next to brick.md so the geometry can be re-checked after implementation.

_A brick is instructions, not a clone: the geometry, timing and state machine come from the source; colour and type come from your project's slots._
