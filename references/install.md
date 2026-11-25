# Install / repair

The skill needs Python 3.10+, Node 18+, and playwright (installed into the skill's own `node_modules`).
No API key, no browser account.

## 1. Find the skill directory

The skill directory is the one holding this file's parent `references/` and a `scripts/` sibling.
Usually it is the folder the platform unpacked, e.g. `~/.workbuddy/skills/lewitt`. If `scripts/` is
not there, the package was only partially unpacked — re-install it in the client before continuing.

## 2. Install the browser driver (once per machine)

```sh
bash "$SKILL/scripts/setup.sh"          # playwright + chromium into $SKILL/node_modules
bash "$SKILL/scripts/setup.sh" --check  # report only, install nothing
```

Exit code 0 means ready. Common failures:

| Message | Fix |
| --- | --- |
| `'node' is required` / `'npm' is required` | Install Node 18+ and reopen the terminal. |
| `npm install` network error | Set `$HTTP_PROXY` / `$HTTPS_PROXY` and rerun; the browser download also honours `PLAYWRIGHT_BROWSERS_PATH`. |
| `browser: MISSING` after install | `cd "$SKILL" && npx playwright install chromium` |

## 3. Offline self-check (no network)

```sh
python3 "$SKILL/scripts/lint_output.py" --dest "$SKILL/runs/stripe.com"
```

Exit 0 means the scripts and the data contract are intact. If `runs/` was left out of the install to
save space, skip this step — it is a smoke test, not a requirement.

## 4. Output location

Write runs to `./runs/{domain}/` under the user's current project. Never write into the skill
directory itself: it is read-only by convention and shared across projects.
