---
name: lewitt
description: >-
  Reverse-engineer a website's design into an evidence-backed, agent-usable design DNA:
  tokens (primitive/semantic/component) plus opinionated WHY trade-offs, rendered from one
  file into taste.md, tokens.css, agent-rules.md and enforced guardrails. Use when someone
  gives a URL and asks what makes it look the way it does, wants its tokens or "design DNA",
  wants to build something in the style of a site, or needs rules an AI coder must follow.
  Two modes: DNA mode (default, ~1-2 min, no site build) and --full (adds a runnable
  design-system reference site with component states and compositions). Do NOT use to scrape
  content, summarize a page, or clone a screenshot pixel-for-pixel.
cn: "给一个网址，抽出可追溯的设计 DNA（tokens + 为什么这么做），生成 taste.md / tokens.css / agent-rules.md 并强制校验；--full 才建可浏览的设计系统站点。"
category: "设计/前端"
---

# Design DNA

Turn a URL into one authored file — `dna.json` — and everything else is rendered from it.

| Artifact | What it is | Written by |
| --- | --- | --- |
| `dna.json` | **The only thing you author**: meta, evidence, measurements, patterns, taste, tokens | you |
| `taste.md` | Design Map + Taste DNA, human-readable | `build_artifacts.py` |
| `tokens.css` | `[data-ds]` scoped variables, primitive → semantic → component | `build_artifacts.py` |
| `tokens.resolved.json` | flat values per mode | `build_artifacts.py` |
| `preview.html` | single-file live specimens, motion replay, taste cards, source thumbnails, copy/download bar | `build_artifacts.py` |
| `shadcn-theme.css` | shadcn/ui + Tailwind v4 `@theme inline` slots mapped from semantic tokens; unmapped slots say `initial`, never invented | `build_artifacts.py` |
| `dna.schema.json` | the v1.1 data contract other tools can validate against (repo root; `build_artifacts.validate` is the authority) | authored |
| `agent-rules.md` | hard constraints first, then principles, patterns, token list, verify command | `build_artifacts.py` |
| `VERIFY.md` / `verify.json` | gate results, including explicit `unverified` rows | `lint_output.py` |
| `system/` | runnable reference site — states, compositions, stress controls, fidelity (**`--full` only**) | you, then `lint_output.py --check-code` |
| `fidelity.json` | side-by-side comparison record (`--full`): what agrees, what deviates | you |

Output lives at `{dest}/{domain}/` so two sites never overwrite each other.

## Three rules that override everything below

**R1 — Evidence never changes class.** Every claim is `observed | inferred | proposed | unknown`,
and `observed`/`inferred` cite an evidence id. A screenshot estimate is never written as a CSS
value. A missing value is `unknown`, never a plausible number.

**R2 — Anti-slop is mechanical.** Banned vocabulary is checked by `lint_output.py`, not by memory.
Every taste principle carries a real rejected alternative (`chose` vs `over`), and at least one
is a **restraint** with a machine-readable `guardrail`. If a principle could be written without
ever seeing this site, delete it.

**R3 — Single source.** `dna.json` (schema **1.1**) is authored; artifacts are renders. Never hand-edit
`taste.md`, `tokens.css`, `agent-rules.md`, or `tokens.resolved.json`; `lint_output.py` fails when
they drift. The same registry feeds the documentation, the CSS, the exports, and `system/`.

## Modes

| Mode | Input | Produces | Budget |
| --- | --- | --- | --- |
| **DNA** (default) | one URL | `capture/` + `dna.json` + 4 renders + `VERIFY.md` | 1 page + up to 3 representative subpages |
| **Full** (`--full`, or "建设计系统站点 / build a design-system site") | one URL | everything above + `system/` + guardrail check on it | same crawl, more build time |

Do not silently upgrade to Full. Do not build `system/` in DNA mode.

## Pipeline

Set `SKILL=<this skill dir>`, `DEST=<output root>`, `DOMAIN=<host without www>`.

### Phase 0 — Brief (do this first, every time)

Resolve four fields; infer any that the request already answers, and state them in one line
instead of asking:

- **source** — the URL;
- **mode** — DNA unless `--full` or an explicit site-build request;
- **scope** — DNA mode = entry page + up to 3 representative same-origin families found in nav.
  Ask only if the user wants exhaustive coverage or an authenticated area;
- **dest** — `{dest}/{domain}/`.

**Incremental update (hard rule).** If `{dest}/{domain}/dna.json` already exists, you are
updating, not rebuilding:

1. Read the existing file and **declare a scope** — the blocks this run may change, e.g.
   `taste` for wording, `tokens,measurements` for a changed primary colour, `evidence,measurements,tokens`
   after capturing a new subpage that exposed new components.
2. Edit only the blocks in scope; leave every other block byte-identical (including evidence ids
   you are not re-observing). Everything outside the scope is frozen automatically.
3. Render with `--incremental <scope>`; the tool records `meta.incremental {targets, frozen}`.
4. `tokens` may change, but only together with `evidence` in the same scope (or with `--force`
   plus a `meta.limitations` line). Numbers never move without the proof that moved them.
5. Never delete evidence that still supports a frozen block. Never rewrite the file wholesale
   "to be safe".

If the target page cannot be reached, stop and report; do not fabricate a system from an error
page.

### Phase 1 — Sense

Read [references/sense.md](references/sense.md), then:

```sh
python3 "$SKILL/scripts/capture.py" <url> --dest "$DEST" --pages 4
```

`capture.py` finds playwright via `LEWITT_PW_DIR` → the skill's own `node_modules` → global/npx,
so a fresh clone only needs `bash scripts/setup.sh`. It refuses to run without an isolated driver — a logged-in or wrong surface is a
failed capture, not a weaker one. It writes `capture/dom.json` (with `interactions`: forced hover / focus-visible deltas), `capture/viewport.png`,
`capture/fullpage.png` (only when ≤ 6 viewports tall), `capture/dom-N.json` for extra pages, and
`capture/meta.json`. Read the screenshots: composition is judged visually, values come from the
DOM, and disagreements are recorded as `conflict`, not silently resolved.

### Phase 2 — Infer (three passes, in order)

Read each reference when you reach it; do not preload all three.

1. **Measure** — [references/infer-measure.md](references/infer-measure.md): ~17 categories of
   exact values, each tied to evidence ids.
2. **Pattern** — [references/infer-pattern.md](references/infer-pattern.md): 5–8 system rules
   with `rule`, `goal`, `evidence`. This layer is mandatory; taste may not jump straight from
   measurements.
3. **Taste** — [references/infer-taste.md](references/infer-taste.md): 3–4 principles with
   `trigger / decision / chose / over / reason / evidence / patterns`. At least one `kind:
   restraint`, and each restraint carries a `guardrail`.

**Interaction deltas.** `capture.py` also forces hover (real CDP mouse) and `:focus-visible` on up to
5 representatives (2 buttons, a link, a card, an input) and records before→after values for
`background-color, color, border-color, box-shadow, outline, transform`. Copy those into
`dna.json > interactions[]` verbatim (status `observed`, citing evidence ids). Do not report a
delta you did not measure; "none (measured, no computed change)" is a valid, useful result.

Cross-page agreement is the strongest evidence: a value on 2+ pages is a system signal; one
page only is local — keep it, but weight it lower and say so.

### Phase 3 — Model and author

Read [references/model.md](references/model.md). Write `{dest}/{domain}/dna.json` with the six
blocks. Tokens are layered: `primitive` (raw value) → `semantic` (role, aliases) →
`component` (reusable part). `unknown` never enters `tokens[]`; it stays in prose or
`measurements` with `status: unknown`.

### Phase 4 — Render

```sh
python3 "$SKILL/scripts/build_artifacts.py" "$DEST/$DOMAIN"
```

It validates, then writes the five renders (including `preview.html`, which links the same-folder
`tokens.css` and has no external dependency — `lint_output.py` gates that). A schema failure stops rendering — fix the source,
never the output.

Theme export (always written; or on demand):

```sh
python3 "$SKILL/scripts/build_artifacts.py" "$DEST/$DOMAIN" --export=shadcn   # only shadcn-theme.css
python3 "$SKILL/scripts/build_artifacts.py" "$DEST/$DOMAIN" --print-theme     # paste into globals.css
```

Incremental form:

```sh
python3 "$SKILL/scripts/build_artifacts.py" "$DEST/$DOMAIN" --incremental taste
python3 "$SKILL/scripts/build_artifacts.py" "$DEST/$DOMAIN" --incremental evidence,measurements,tokens   # e.g. the brand colour changed
```

Frozen blocks that moved since the last render make it fail; so does a `tokens` change whose
`evidence` was not in scope.

### Phase 5 — Verify

```sh
python3 "$SKILL/scripts/lint_output.py" --dest "$DEST/$DOMAIN"
python3 "$SKILL/scripts/lint_output.py" --dest "$DEST/$DOMAIN" --check-code "$DEST/$DOMAIN/system"   # --full only
```

Gates: `dna.json` contract, token resolution (no cycles/dangling/type mismatch), anti-slop,
single-source drift, restraint guardrails, and — with `--check-code` — whether generated code
violates any guardrail. Rows that cannot be tested are listed as `unverified`, never as pass.
Read [references/verify.md](references/verify.md) for what each gate does and does not prove.

### Phase 6 — Report

One short block: mode, pages inspected, artifact paths, the sharpest principle in one line, and
every `FAIL`/`unverified` row. Do not claim a site is ready when a gate failed.

**Full mode only** — read [references/build-full.md](references/build-full.md) and build
`system/` from the same tokens, then run `--check-code`. The reference site is an app shell
(fixed rail + one scrolling canvas), not a long document.

Subcommands stay small on purpose: `cert` and `remix` live in their own references
([cert.md](references/cert.md)) so this file stays the contract, not a manual.

**Certiry a build** — once an app (or the generated `system/`) runs locally, audit it against the
same `dna.json`:

```sh
python3 "$SKILL/scripts/cert.py" --url http://localhost:3000 --dest "$DEST/$DOMAIN"
```

It writes `cert.md` / `cert.html` / `cert.json` with a verdict (`certified`, `warned`, `rejected`,
`inconclusive`), measured token deltas and guardrail hits on the live page. Read
[references/cert.md](references/cert.md) for what is and is not certified.

## Banned vocabulary

`clean, modern, sleek, visually appealing, user-friendly, intuitive, seamless, elegant,
minimalist, polished, refined, sophisticated, delightful, stunning, beautiful, premium`.

They are allowed only as an explicit foil ("could have gone 'clean and modern', but…").

## Failure handling

| Situation | Do |
| --- | --- |
| No isolated browser driver | Stop. Run `bash scripts/setup.sh` (installs playwright next to the skill), or set `LEWITT_PW_DIR`, or pass `--driver`. Do not fall back to a shared session silently; if you must, set `meta.captureIsolated=false` + `meta.isolationNote`. |
| Bot wall / login form | Report it; ask for an accessible URL or exported screenshots. A labeled scaffold is not an extraction. |
| SPA still hydrating | `capture.py` waits; add a `limitations` entry and mark affected measurements `inferred`. |
| Fewer than 3 taste principles survive | Ship 2 with evidence. Never pad with generic ones. |
| Guardrail blocks legitimate code | Change the guardrail in `dna.json` (with evidence), not the check. |
