# Full mode — the runnable reference site

Only enter this mode when the user asked for it (`--full`, "建设计系统站点", "build a
browsable design system"). It reuses the same `dna.json`; it never re-derives values.

## Output

`{dest}/{domain}/system/` — a self-contained static site (plain HTML/CSS/JS is enough):

```
system/
  index.html          section nav, anchors, skip link
  tokens.css          copy or import of ../tokens.css (scoped to [data-ds])
  evidence.json       copy of the evidence ledger shown in the UI
  sections/           foundations · components · compositions · motion · stress · handoff
```

No backend, no build step required. Scope every token and specimen style under `[data-ds]` so
the documentation chrome never inherits the extracted component geometry.

## Required sections

1. **Foundations** — colour swatches with real fg/bg pairs and usage counts, type specimens at
   their real sizes, radii, depth (rings vs floats side by side), spacing shown as geometry.
2. **Components** — anatomy, variants, states (default/hover/focus/pressed/disabled), token
   mapping, usage and avoidance. Simulated states are labelled as samples; they supplement, not
   replace, real pointer/keyboard behaviour.
3. **Compositions** — at least three: a source-like section, an interaction flow, and a fuller
   responsive layout. They must reuse the gallery components, not bespoke markup.
4. **Motion** — replay with actual duration/easing, plus a reduced-motion comparison. The OS
   preference is respected and a manual toggle supplements it.
5. **Stress** — long labels, missing media, empty/error/loading, 320px width, large text.
   Distinguish sample-level scaling from real zoom tests.
6. **Handoff** — download links for `tokens.css`, `tokens.resolved.json`, `taste.md`,
   `agent-rules.md`; evidence ids; `limitations`; what is proposed vs observed.

## Rules

- Every displayed value comes from `tokens.resolved.json`; never retype a number in HTML.
- Interactions are real local state (a "Save" button changes state). Never submit to the source
  site.
- Real semantic controls, visible focus, accessible names, status announcements.
- No decorative motion in the documentation chrome; do not autoplay every specimen.
- New behaviour invented for an example is labelled `proposed`.

## Verify

```sh
python3 "$SKILL/scripts/lint_output.py" --dest "$DEST/$DOMAIN" --check-code "$DEST/$DOMAIN/system"
```

Then, and only then, check the site at 1440 / 390 / 320, keyboard, reduced motion, and confirm
the download links resolve. Record anything you could not test as `unverified` — a build that
passes local checks is not proof the site is accessible or faithful.
