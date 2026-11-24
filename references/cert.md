# `lewitt cert` — audit a running site against an extraction

`cert` is the certificate step: a Sol LeWitt wall drawing was executed by assistants and he signed
what was actually on the wall. Here the wall is your localhost page and the instructions are the
tokens and guardrails already extracted into `dna.json`.

```sh
python3 scripts/cert.py --url http://localhost:3000 --dest runs/stripe.com
python3 scripts/cert.py --url http://localhost:3000 --dest runs/stripe.com --pages 3
```

Writes `cert.md` (human), `cert.html` (printable) and `cert.json` (machine) **inside the run
directory**. It never edits `dna.json` or any render.

## What is measured

| Group | How | Pass rule |
| --- | --- | --- |
| component type sizes (`type/*`) | each variable is applied to a probe element on **your page** and read back | within 1px |
| radii (`radius/*`) | same probe | within 1px |
| font families | same probe, first family must appear in the computed stack | name contains |
| semantic colours | the variable's value is read from **your page's own CSS custom properties** | max channel delta ≤ 4, alpha composited over white |
| guardrails | every element's class list, inline `style`, and computed `box-shadow` on your page | any `forbidClass` match or bound violation |

A variable your page never defines is reported as **not measured**, not as a pass. The report
always ends with a "not certified" list (component geometry, spacing, motion, resemblance).

## Verdict

| Verdict | When | Exit |
| --- | --- | --- |
| `certified` | every measured probe agrees, no guardrail hits | 0 |
| `warned` | deviations under 15% of the weighted score and no colour deviation | 1 (0 with `--allow-warn`) |
| `rejected` | any colour deviation, heavier deviation, or a guardrail hit | 1 |
| `inconclusive` | nothing could be measured (no variables, no capture) | 1 |

Capture failures exit 2 and write nothing — an empty certificate would be worse than none.

## CI

```sh
python3 scripts/cert.py --url http://localhost:3000 --dest runs/stripe.com || exit 1
```

Do not wire this into a pipeline for a *third-party* site: guardrails describe UI you generated from
this run, and the local page is the only thing they should be applied to.
