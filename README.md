# lewitt

[Live page](https://koroo.top/lewitt) · [How it works](https://koroo.top/lewitt/about) · [Download SKILL.md](https://koroo.top/lewitt/SKILL.md)

**Turn a website's visual rules into measured tokens, a shadcn / Tailwind v4 theme, agent rules, and guardrails a linter can enforce.**

Named after [Sol LeWitt](https://en.wikipedia.org/wiki/Sol_LeWitt), who wrote wall-drawing instructions precise enough for other people to execute. `lewitt` does that for UI: measurements come from a real browser, they land in one file (`dna.json`), and every artifact is compiled from it.

![lewitt preview of stripe.com — live swatches, evidence ids, token layers](docs/preview.png)

---

## Who it is for

- **Builders shipping with a coding agent.** You admire a site and want its discipline in your project. You get `shadcn-theme.css` to paste into `globals.css` and an `agent-rules.md` whose `MUST NOT` section lists what your agent keeps getting wrong: extra gradients, invented shadows, off-scale type.
- **Engineers treating the design system as code.** Every value carries a status (`observed` / `inferred` / `proposed` / `unknown`), interaction deltas come from real CDP input, and `lint_output.py` fails a run when a render drifts from `dna.json` or when generated UI breaks a guardrail.

## Three pieces

| Piece | Command | What it does | Writes |
| :--- | :--- | :--- | :--- |
| **Extract** | `lewitt <url>` (`--full` for a reference site) | reads 1–4 pages, records computed styles, screenshots and interaction deltas, names the trade-offs | `dna.json`, `taste.md`, `agent-rules.md`, `tokens.css`, `tokens.resolved.json`, `shadcn-theme.css`, `preview.html`, `VERIFY.md` |
| **Clip** | `scripts/clip.py` | lifts one block or micro-interaction from any page, strips its skin, records the reduce branch | `brick.md`, `brick.json`, `shots/` |
| **Certify** | `scripts/cert.py` | audits a running build against the extraction | `cert.md`, `cert.html`, `cert.json` |

Each piece works alone. `clip` needs no extraction; `cert` needs one (`dna.json` is the spec it checks against).

---

## Quick start

```sh
git clone https://github.com/CClishan/lewitt-skill.git ~/Projects/skills/lewitt
cd ~/Projects/skills/lewitt
bash scripts/setup.sh          # installs the Playwright driver and caches a Chromium build

ln -s ~/Projects/skills/lewitt ~/.codex/skills/lewitt     # Codex
ln -s ~/Projects/skills/lewitt ~/.claude/skills/lewitt    # Claude Code
ln -s ~/Projects/skills/lewitt ~/.dsh/skills/lewitt       # DeepSeek Harness
```

Then, in the agent:

> Use lewitt to analyze https://stripe.com

Add `--full` to also build `system/index.html`, a reference site (fixed rail, one scrolling canvas, live component matrices, stress toggles for long copy / missing media / reduced motion / a 390px viewport).

### Print the theme for `globals.css`

```sh
python3 scripts/build_artifacts.py --dest runs/stripe.com --print-theme
```

The theme uses Tailwind v4's `--color-*` namespace inside `@theme inline`, so `bg-background` and
`text-muted-foreground` resolve. Slots the source cannot support stay `initial` and are named in the
file header — a site with no error state produces no invented `--destructive` value.

### Clip one interaction

```sh
python3 scripts/clip.py --url https://www.onepixelai.com/ --find "Index" --dest ./bricks --action hover
```

`./bricks/clips/onepixelai.com-index/brick.md` contains:

- **skin stripped by role** — source colours map to `--card`, `--secondary`, `--primary`, `--radius` by
  contrast and role, never by nearest hex; the file opens by stating that copying the source's hex or
  rgb is a violation;
- **four sampled targets** — trigger, local module, the element under the mouse, and the panel an
  activation opens, compared as `before → during → settled → idle`;
- **a measured reduce branch** — the same timeline replayed under `prefers-reduced-motion: reduce`,
  classified `degraded` / `degraded-to-none` / `not-degraded` with both durations.

Hand `brick.md` to your agent and ask it to build the block with your project's own variables.

### Certify a build

```sh
python3 scripts/cert.py --url http://localhost:3000 --dest runs/stripe.com
```

Values are read in three tiers, and `cert.md` records which one answered:

1. `--lw-*` variables from `tokens.css`;
2. shadcn / Tailwind v4 slots (`--background`, `--primary`, `--muted-foreground`, `--border`, `--radius`);
3. computed styles of the page itself (`body`, `h1`, the first button, the first card).

A change you made on purpose goes in `{run_dir}/cert.config.json`, with a reason:

```json
{
  "intentional": [
    { "token": "color/text/body", "reason": "dashboards use the heading ink for body copy here" }
  ]
}
```

Verdict is `certified`, `warned`, `rejected` or `inconclusive`, and the exit code is non-zero for
anything but an outright pass.

### Run the gates

```sh
# a full extraction, including generated code checked against the restraint guardrails
python3 scripts/lint_output.py --dest runs/stripe.com --check-code ./src/components

# standalone bricks (a directory that only holds clips/)
python3 scripts/lint_output.py --dest ./bricks
```

---

## Three rules

1. **Evidence over guesswork** — every measurement, pattern, token and interaction carries
   `observed` / `inferred` / `proposed` / `unknown`. An unmeasured value is reported as unmeasured.
2. **Mechanical anti-slop** — authored prose is checked against a banned-word gate, and every
   restraint principle carries a machine-readable guardrail. Each guardrail pattern must catch a known
   violation before a run can pass.
3. **Single source of truth** — `dna.json` (validated by `dna.schema.json`) is the only authored file.
   `taste.md`, `tokens.css`, `shadcn-theme.css`, `agent-rules.md` and `preview.html` are deterministic
   renders; editing them by hand fails the drift gate.

## Included runs

Read the outputs before running your own:

| Run | Mode | Look |
| :--- | :--- | :--- |
| [runs/linear.app](runs/linear.app) | DNA | dark UI, one white action accent, rings instead of shadows |
| [runs/stripe.com](runs/stripe.com) | full | light UI, blue-tinted ink, one hero gradient, 300-weight display type |
| [runs/binance.com](runs/binance.com) | full | high-density dark trading surface, gold reserved for action and figures |

Each run holds `VERIFY.md` (what passed, what stayed `unverified`), and stripe also holds a clip set
(`clips/`) and a certificate.

## Requirements

Python 3.10+, Node 18+, and no API keys. The only dependency is Playwright, installed by
`scripts/setup.sh` into this repo's `node_modules`; browsers run headless in a throwaway profile.

## License

MIT
