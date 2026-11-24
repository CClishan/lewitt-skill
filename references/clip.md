# `lewitt clip` — lift one block, keep its behaviour

A **brick** is one small module (a gallery tile, a pricing card, a drawer) with its interaction
recorded and its skin removed. It answers the question behind most vibe-coding sessions: *"this
section from that site — can I have it, in my project's colours?"*

```sh
# standalone: no extraction needed, output goes to {dest}/clips/{domain}-{slug}/
python3 scripts/clip.py --url https://example.com --find "See how it works" --dest ./bricks

# inside an extraction, mapped onto that run's variables
python3 scripts/clip.py --url https://example.com --selector "#gallery > article" --dest runs/example.com --slots lw

# anywhere, under a name you choose
python3 scripts/clip.py --url https://example.com --find "Start free" --out ./src/bricks/pricing-cta
```

`--dest` no longer needs a `dna.json`. Output: `{dest}/clips/{slug}/` (or `{dest}/clips/{domain}-{slug}/`
in standalone, or `--out <dir>` verbatim), holding `brick.json`, `brick.md`, `shots/`.

## Slot systems

| `--slots` | Output | When |
| --- | --- | --- |
| `shadcn` (default) | `var(--card)`, `var(--muted)`, `var(--primary)`, `var(--border)`, `var(--radius)`… | you paste into a shadcn / Tailwind v4 project |
| `lw` | `var(--lw-…)` from the run's `dna.json` | you want the extraction's own semantic tokens (requires `dna.json`) |

shadcn mapping is **by role, not by nearest colour**: a hovered block's surface becomes `--card`, the
hover tint `--muted`, the control that changes state `--primary`, its label
`--primary-foreground`, text `--card-foreground` / `--muted-foreground`, and every radius
`--radius` (shadcn derives the rest). Brick.md opens with a banner naming the slot system and states
that copying the source's hex/rgb into the project is a hard violation — `cert` rejects it.

## What a brick is, and is not

| It is | It is not |
| --- | --- |
| geometry, timing, state machine, content skeleton | a pixel copy, or the source's CSS |
| a mapping from source colours to **your** slots | a second design system |
| a description you can implement in the project's stack | a drag-and-drop export |

If you cannot describe the module without the source's class names, the brick is not finished.

## How the recording works

1. **Find** — `--find "<visible text>"` (exact match first, then substring) or `--selector`.
   The **module** is the nearest ancestor that looks like a block (`article`, `[class*="card"]`, a
   grid child ≥ 280px wide); the **stateful** element is the descendant that actually moves on
   activation (`panel`, `drawer`, `menu`, `collapse`…).
2. **Drive** — hover uses a real CDP `mouseMoved`; click uses `mousePressed` + `mouseReleased` at the
   trigger's centre. Nothing is submitted, nothing logs in.
3. **Record** — for each state: box, opacity, transform, colours, radius, shadow, the computed
   `transition`, and every running animation (`getAnimations`, with its keyframes summary).
4. **Strip** — the source background/label colours are mapped to the closest semantic token in this
   run and written as `var(--lw-…)`; the content skeleton lists the text nodes by tag and role.
5. **Round trip** — `idle → hover → settled → idle` for hover; `idle → open → idle` for
   click/toggle. Each arrow says whether it was actually observed.

## Reading `brick.md`

- **States** — one row per snapshot; `transitions running` is the count of live animations.
- **Deltas** — only properties that changed, as `before → after`.
- **Skin mapping** — `source value → slot (var, Δ)`. A slot marked *no slot matched* means you must
  pick one; the brick must not invent a colour.
- **State machine** — the arrows with `observed: true/false`. An arrow that was never observed is a
  TODO for your implementation, not a fact.
- **Implementation notes** — which properties to animate, which timing to reuse, which box to keep.

## Reduced motion (measured, twice)

Every clip runs the same timeline **twice in the same browser**: once normally, once with
`Emulation.setEmulatedMedia` set to `prefers-reduced-motion: reduce` (verified through
`matchMedia`). `brick.json > reducedMotion` records duration, travel and end state for both passes:

| status | meaning |
| --- | --- |
| `degraded-to-none` | the source removes the transition entirely under reduce — mirror that (instant end state) |
| `degraded` | shorter or less travel, same end state — mirror the measured ratio |
| `not-degraded` | ⚠️ the source keeps moving under reduce — implement the branch yourself, do not copy it |
| `unrecorded` | the pass produced no snapshot (media emulation or the state itself failed) |

## Limits (MVP)

- One module, one interaction per run. Sequences (open → animate → close) need separate clips.
- Only pointer activation is recorded; keyboard behaviour is assumed to mirror it and must be tested
  in the implementation.
- Assets are never downloaded; media beyond the first two are dropped.
- Only `prefers-reduced-motion` is emulated; forced-colors, dark mode and coarse pointers are not.
- A source that ignores reduce produces a warning, not a fix: the brick tells you the source failed
  and asks you to implement the branch.
