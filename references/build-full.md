# Full mode — the runnable reference site

Only enter this mode when the user asked for it (`--full`, "建设计系统站点", "build a
browsable design system"). It reuses the same `dna.json`; it never re-derives values.
`preview.html` renders this same dual view as one file; `system/` adds the folder-based Specs
panels (capture, clips, downloads).

## Output

`{dest}/{domain}/system/` — a self-contained static site: a minimal sticky top bar over **two views**.

```text
┌ topbar: [lewitt mark] site · 3px brand band   Live Preview | Specs & Evidence   Copy theme  Stress ┐
│ view 1  Live Preview — one numbered scrolling long scroll, painted in the run's --lw-* tokens          │
│   hero (brand first screen)                                                                           │
│   01 Colour Palette      semantic / component / primitive, scene line, WCAG chip per swatch, + Observed│
│   02 Typography Scale    one row of monospace params, then the run's own copy at real size            │
│   03 Components & Cards  real states (forced samples labelled), form, pricing / feature cards, rows,   │
│                          one measured interaction delta                                                │
│   04 Motion & Guardrails drawn cubic-bezier + Replay slider, MUST NOT capsules with the regex folded,  │
│                          taste cards (chose over)                                                     │
│   05 Clipped Bricks      a live rebuild from the brick's slot mapping, the real keyframe shots,       │
│                          deltas, and the measured reduced-motion verdict                              │
│ view 2  Specs & Evidence — overview, tokens, measurements, evidence ledger, limitations, code &       │
│         downloads, fidelity                                                                            │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **top bar**: lewitt mark, source name, the run's 3px brand fingerprint, the view switch
  (`Live Preview` default | `Specs & Evidence`, also `#live` / `#specs`), copy-shadcn-theme button,
  and three stress booleans: `Long copy` · `Reduced motion` · `Narrow 390`.
- **stress booleans feed both views**: Long copy re-cuts the preview columns and the specs grids;
  Reduced motion removes every transition/animation in the site frame and turns motion replays
  into their end state; Narrow 390 rebuilds the site at 390 inside a calm dark field.
- **Observed tags**: colour, typography, motion and material each carry one tag; it opens a card
  with the actual ledger entry (id, locator, measured values, method) — proof, not a badge.
- **Museums and phones**: the preview shows the source's own nav/footer bar and section rhythm
  (`specimens.backdrop`: canvas / surface / action per section, so a dark section stays dark).

Files:

```
system/
  index.html      both views (tokens.css is read from ../tokens.css)
  doc.css         neutral base + the shell CSS
  site.css        specimen-specific styles
  system.js       view switch, stress, evidence cards, motion replay, copy
  system.css      hand-authored component skin (optional, kept as-is)
  evidence.json   the ledger payload the Observed cards read
```

## Where the content comes from (R3)

Everything is a render of `dna.json`:

- `specimens.hero` / `stats` / `cards` / `table` / `form` — site-voice copy (hero line, stats strip,
  pricing tiers with one `featured` inverted tier, sample rows, form labels). Written by the
  extraction phase in the target site's voice; never another site's placeholder sentence.
- `specimens.backdrop` — the section rhythm (`canvas` | `surface` | `action`, one per section incl. `nav`).
- `specimens.brandSvg` — the source's own inline mark (self-contained; no `href`, `url()`, script).
- `specimens.typeSpecimens` — per-step copy for the type scale, keyed by type token id.
- `tokens` drive every colour, type step, radius and curve; `taste[].guardrail` drives the MUST NOT
  capsules; `interactions` drive the measured-delta block; `evidence` drives the Observed cards.

## Verify

```sh
python3 "$SKILL/scripts/build_artifacts.py" "$DEST/$DOMAIN"
python3 "$SKILL/scripts/lint_output.py" --dest "$DEST/$DOMAIN" --check-code "$DEST/$DOMAIN/system"
```

`shell_checks()` fails the run when the top bar, the two-view switch, sections 01-04, the Observed
tag, a WCAG chip, a drawn bezier, a replay control, a MUST NOT capsule, or the Specs panels are
missing (a run rendered before v1.2 may still use the old rail shell). `script_checks()` fails when a
generated page binds the same `var` twice in one closure.

Then check 1440 / 390 / 320, keyboard, reduced motion, every stress boolean, and that the download
links resolve. Record anything you could not test as `unverified`.
