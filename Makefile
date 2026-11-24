# lewitt — every run in runs/ rebuilt from its dna.json and gated.
# `make check` is the fresh-clone acceptance: renders must match the SSOT, guardrails and clip
# gates must be green. No network: it reads runs/*/dna.json and runs/*/clips/ only.
PYTHON ?= python3
RUNS    := $(sort $(dir $(wildcard runs/*/dna.json)))
DOMAINS := $(notdir $(patsubst %/,%,$(RUNS)))

.PHONY: check lint render help
help:
	@echo "make check   — render every run, then lint it (DNA + --check-code system/ + clips)"
	@echo "make render  — render every run from its dna.json"
	@echo "make lint    — lint every run (no render)"

render:
	@for d in $(DOMAINS); do echo "== render $$d"; $(PYTHON) scripts/build_artifacts.py runs/$$d >/dev/null || exit 1; done

lint:
	@fail=0; for d in $(DOMAINS); do echo "== lint $$d"; \
	  extra=""; [ -d runs/$$d/system ] && extra="--check-code runs/$$d/system"; \
	  $(PYTHON) scripts/lint_output.py --dest runs/$$d $$extra || fail=1; \
	  [ -d runs/$$d/clips ] && { $(PYTHON) scripts/lint_output.py --dest runs/$$d/clips || fail=1; }; \
	done; exit $$fail

check: render lint
