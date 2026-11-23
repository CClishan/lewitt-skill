# design-dna

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
`agent-rules.md` and `VERIFY.md` are deterministic renders of it. If a rendered file drifts,
`lint_output.py` fails — so an analysis can never be half-updated.

```
meta · evidence · measurements · patterns · taste · tokens
```

Restraint principles carry a machine-readable `guardrail`, so "no accent colour" or "rings
instead of shadows" can be enforced against generated UI, not just written down.

## Usage

```sh
SKILL=~/Projects/skills/design-dna/scripts
DEST=./out

python3 $SKILL/capture.py linear.app --dest $DEST --pages 4      # isolated, CDP-eval capture
#   ... author $DEST/linear.app/dna.json (see references/) ...
python3 $SKILL/build_artifacts.py $DEST/linear.app              # renders + schema gate
python3 $SKILL/lint_output.py --dest $DEST/linear.app           # all gates
python3 $SKILL/lint_output.py --dest $DEST/linear.app --check-code ./src   # guardrails vs code
```

Incremental update of one site:

```sh
python3 $SKILL/build_artifacts.py $DEST/linear.app --incremental measurements,taste
```

It refuses when a frozen block changed since the last render.

## Requirements

- Python 3.10+
- `playwright` for capture (one-time): `mkdir -p ~/.dd && cd ~/.dd && npm i playwright && npx playwright install chromium`
  `capture.py` exits non-zero rather than capture from a non-isolated browser.

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

## Worked example (linear.app, DNA mode)

| Gate | Result |
| --- | --- |
| dna.json contract / token resolution / single source / incremental freeze | PASS |
| evidence coverage (28 entries) / restraint guardrails (2/2) / anti-slop (0 hits) | PASS |
| guardrail vs generated code, visual fidelity | unverified (not claimed) |

Sharpest principle: *Brand lives in white, not in colour* — white on `#08090A` is the only
high-contrast action; a branded hue would compete with the product screenshot.

## Status

Not committed to a remote yet. Create the repo and push when you want a shareable version.
