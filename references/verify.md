# Verify — what the gates prove, and what they do not

Run after every render:

```sh
python3 "$SKILL/scripts/lint_output.py" --dest "$DEST/$DOMAIN"
```

Exit code 0 means every executable gate passed. It does **not** mean the extraction is faithful.

## Gates

| Gate | Pass means | It cannot tell you |
| --- | --- | --- |
| `dna.json contract` | all six blocks present, ids unique, references exist, one restraint with a guardrail, units and statuses legal | whether the values match the site |
| `token resolution` | every alias resolves, no cycles, same-type targets, every declared mode defined | whether the layering is the right call |
| `single source (R3)` | re-rendering `dna.json` reproduces every artifact byte-for-byte | whether the authored content is good |
| `evidence coverage` | at least one evidence entry exists and is cited | whether you captured enough pages |
| `anti-slop` | zero banned words in authored prose (foils allowed) | whether a sentence is still vague |
| `restraint guardrails` | every restraint carries a machine-readable guardrail | whether the guardrail is well chosen |
| `guardrail (generated code)` | `--check-code` found no forbidden property, class pattern, or over-cap length | whether the code looks like the source |
| `preview.html (self-contained)` | the preview links the same-folder `tokens.css` and loads no remote asset | rendering quality, copy tone |
| `system/ colour scope` | full mode: the page takes its canvas from `color/canvas` and sits on the right tone | whether individual specimens look right |
| `visual fidelity` | `unverified` without `fidelity.json`; `PARTIAL` while deviations are recorded; `PASS` only when `status: match` | that the reconstruction is correct — it records agreements and deviations for a reader |
| `full system/ site` | full mode: `system/index.html` exists (`FAIL` if absent) | whether the site is good |
| `full system/ site` | `n/a` in DNA mode | only meaningful with `--full` |

## `--check-code` details

- Scans `.css .scss .sass .less .html .htm .jsx .tsx .vue .svelte .astro` under the directory,
  skipping `node_modules`, `dist`, `build`, `.next`, `.git`.
- CSS: every `prop: value` inside rule blocks and at-rules, comments stripped.
- Markup: `style="…"` / `style={{ … }}` literals and `class`/`className` lists.
- `forbidCss` matches the property or a prefix (`box-shadow` also blocks `box-shadow-color`).
- `max.<property>` compares every geometric length in the value; for `box-shadow` that means
  offset, blur and spread together. Colour channels and hex colours are excluded.
- `requireCss` fails when the property never appears anywhere in the scanned code.

## What still needs your judgement

- **Fidelity** — put a specimen next to the source at 1440 and 390 and look. Record the result
  and what deviated.
- **Contrast of real pairs** — tokens are not a contrast check. Compute the pairs you actually
  use.
- **Guessing** — every `inferred` naming and `proposed` value is an opinion; the report must say
  which decisions came from evidence and which are yours.
- **Coverage** — list the pages you did not visit.

## Reporting

`VERIFY.md` is generated; copy its numbers into the final answer rather than re-describing the
run. If any gate failed, say so plainly and list the fix. Do not lower the bar: an `unverified`
row stays `unverified` even when everything else is green.
