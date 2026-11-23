# lewitt

Reverse-engineer a website into a **design DNA** an AI coder can actually follow: measured
tokens plus the trade-offs behind them, rendered from one authored file and checked by
executable gates.

Merged from two skills and their strongest parts:

- `taste-skill` (senlindesign) — the Measure → Pattern → Taste reasoning chain, forced
  restatement of a rejected alternative, mandatory restraint, mechanical anti-slop.
- `website-design-system` (DiqingWWW) — evidence ledger with status labels, three-layer tokens,
  single-source artifacts, explicit verification.

## The one idea

`dna.json` is the only file you author. `taste.md`, `tokens.css`, `tokens.resolved.json`,
`agent-rules.md`, `preview.html` and `VERIFY.md` are deterministic renders of it. The preview is a
single file with live swatches, type and motion specimens, taste cards and a copy/download bar —
it renders in ~30 ms and needs no browser tooling. If a rendered file drifts,
`lint_output.py` fails — so an analysis can never be half-updated.

```
meta · evidence · measurements · patterns · taste · tokens
```

Restraint principles carry a machine-readable `guardrail`, so "no accent colour" or "rings
instead of shadows" can be enforced against generated UI, not just written down.

## Usage

```sh
SKILL=~/Projects/skills/lewitt/scripts
DEST=./out

python3 $SKILL/capture.py linear.app --dest $DEST --pages 4      # isolated, CDP-eval capture
#   ... author $DEST/linear.app/dna.json (see references/) ...
python3 $SKILL/build_artifacts.py $DEST/linear.app              # renders + schema gate
python3 $SKILL/lint_output.py --dest $DEST/linear.app           # all gates
python3 $SKILL/lint_output.py --dest $DEST/linear.app --check-code ./src   # guardrails vs code
```

Incremental update of one site — declare the scope, everything else is frozen:

```sh
python3 $SKILL/build_artifacts.py $DEST/linear.app --incremental taste                      # wording only
python3 $SKILL/build_artifacts.py $DEST/linear.app --incremental evidence,measurements,tokens  # brand colour changed
```

It fails when a frozen block moved since the last render, or when `tokens` changed without
`evidence` in the same scope.

## Requirements

- Python 3.10+
- `playwright` for capture (one-time): `bash scripts/setup.sh` installs it into the skill's own
  `node_modules` (override with `LEWITT_PW_DIR`). Verification order: `LEWITT_PW_DIR` → skill
  `node_modules` → `npm root -g` → npx cache. `capture.py` exits non-zero rather than capture
  from a non-isolated browser.

## Layout

```
SKILL.md                  entry point, pipeline, three rules
references/
  sense.md                capture, isolation, evidence ledger, screenshot-vs-DOM rules
  infer-measure.md        17 measurement categories
  infer-pattern.md        system-rule layer (5-8 patterns)
  infer-taste.md          trade-offs, restraint, guardrail grammar, banned words
  model.md                dna.json contract, token layers, modes
  build-full.md           --full: runnable design-system site
  verify.md               what each gate proves and does not
scripts/
  capture.py              isolated browser capture (node playwright via CDP)
  capture_node.js, eval_cdp.js
  extract.js              in-page DOM extractor (measure only)
  build_artifacts.py      SSOT renderer + schema validator
  lint_output.py          slop · drift · freeze · guardrails (--check-code)
evals/evals.json          regression cases (linear restraint, stripe craft, incremental, guardrail)
runs/linear.app/          the worked example: 3 pages, 28 evidence, 46 tokens, 0 slop hits
```

## Worked examples (DNA mode)

| Run | Pages | Evidence | Tokens | Anti-slop hits | Restraint guardrails | Gate summary |
| --- | --- | --- | --- | --- | --- | --- |
| `runs/linear.app` | 3 | 28 | 46 | 0 | 2/2 | all PASS |
| `runs/stripe.com` | 4 | 32 | 49 | 0 | 2/2 | all PASS |

- Linear — *Brand lives in white, not in colour*: white on `#08090A` is the only high-contrast
  action; a branded hue would compete with the product screenshot.
- Stripe — *Colour is a once-per-page event*: one gradient band in the hero, indigo
  (`#533AFD`) on actions and links only (~0.2% of surface), everything below flat white.

The Stripe run is the anti-slop stress test: a craft-heavy, gradient-heavy, motion-heavy site
passes the word list without being described as "polished" or "premium" — the craft shows up as
measurements (blue-tinted ink, 300 weights, three motion tiers), not adjectives.

`visual fidelity` stays `unverified` in both runs: the gates prove internal consistency, not
resemblance.

## Credits

The reasoning chain and banned-word discipline come from `taste-skill` (MIT, Senlin); the
evidence ledger, token layering and verification table come from `website-design-system`
(DiqingWWW). `lewitt` is the merge, named after Sol LeWitt's instruction-set idea: the brief is
a set of instructions that a competent executor can rebuild from.
