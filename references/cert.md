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

### Where a value is read from (three tiers)

Real projects do not all declare `--lw-*`: a shadcn/ui + Tailwind v4 app only has
`--background / --foreground / --primary / --muted-foreground / --border / --radius`. `cert` reads
each check through these tiers and records which one answered in the "Read from" column:

1. **`--lw-*` on the page** — the variables lewitt exports;
2. **shadcn / Tailwind v4 slots** — `--background`, `--foreground`, `--primary`,
   `--primary-foreground`, `--muted`, `--muted-foreground`, `--card`, `--border`, `--radius`
   (radius converted from `rem` to `px`);
3. **what the page actually paints** — `body` background/colour, `h1` colour and font size, the first
   button's fill/label/radius, the first card's surface/radius.

A token answered by tier 1 or 2 is a declaration check; tier 3 is a rendering check. A token no
tier can answer is reported as **not measured**, never as a pass.

| Group | How | Pass rule |
| --- | --- | --- |
| component type sizes (`type/*`) | each variable is applied to a probe element on **your page** and read back | within 1px |
| radii (`radius/*`) | same probe | within 1px |
| font families | same probe, first family must appear in the computed stack | name contains |
| semantic colours | the variable's value is read from **your page's own CSS custom properties** | max channel delta ≤ 4, alpha composited over white |
| guardrails | every element's class list, inline `style`, and computed `box-shadow` on your page | any `forbidClass` match or bound violation |

A variable your page never defines is reported as **not measured**, not as a pass. The report
always ends with a "not certified" list (component geometry, spacing, motion, resemblance).

## Intentional deviations

Some differences are decisions. Declare them next to `dna.json`:

```json
// {run_dir}/cert.config.json
{"intentional": [
  {"token": "color/text/body", "reason": "this build uses the heading ink on purpose"},
  {"token": "type/h2", "reason": "h2 scale not implemented yet"}
]}
```

Matching deviations are listed under *Intentional deviations* with their reason and no longer count
towards `rejected`. A reason is mandatory; an entry without one is ignored.

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
