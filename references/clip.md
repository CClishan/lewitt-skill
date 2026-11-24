# `lewitt clip` — lift one block, keep its behaviour

A **brick** is one small module (a gallery tile, a pricing card, a drawer) with its interaction
recorded and its skin removed. It answers the question behind most vibe-coding sessions: *"this
section from that site — can I have it, in my project's colours?"*

```sh
python3 scripts/clip.py --url https://example.com --find "See how it works" --dest runs/example.com
python3 scripts/clip.py --url https://example.com --selector "#gallery > article" --dest runs/example.com --action click
```

`--dest` is an existing lewitt run: its `dna.json` supplies the semantic slots the source skin is
mapped onto. Output: `{dest}/clips/{slug}/{brick.json, brick.md, shots/}`.

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

## Limits (MVP)

- One module, one interaction per run. Sequences (open → animate → close) need separate clips.
- Only pointer activation is recorded; keyboard behaviour is assumed to mirror it and must be tested
  in the implementation.
- Assets are never downloaded; media beyond the first two are dropped.
- `prefers-reduced-motion` behaviour of the source is **not** captured — the brick tells you to
  implement it, it cannot show you how the source did it.
