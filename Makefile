VENV := .venv
PY := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

.PHONY: setup keys-check variants mock pilot pilot-mock run analyze parser-test estimate

# Creates a virtual environment, installs Python + node deps, and creates your .env from the template.
setup:
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install -q -r requirements.txt
	cd parser_test/node && npm install --silent
	test -f .env || cp .env.example .env
	@echo ""
	@echo "Wrote .env from .env.example (skipped if it already existed) — now open .env and paste your keys."

# Loads .env, confirms both API keys are present, and makes one tiny real call
# per provider (cheapest/configured models) so you know your keys work before
# `make pilot` spends anything for real. Costs a fraction of a cent.
keys-check:
	$(PY) scripts/run_screen.py --preflight

variants:
	$(PY) scripts/make_variants.py

# Mock end-to-end run — no API keys needed, no network.
mock: variants
	$(PY) scripts/run_screen.py --mock --reps 5 --ablation institution_swap --run-id mock-institution-swap
	$(PY) scripts/run_screen.py --mock --reps 5 --ablation evidence_links --run-id mock-evidence-links
	$(PY) analysis/analyze.py mock-institution-swap
	$(PY) analysis/analyze.py mock-evidence-links

# REAL pilot — one real JD, one condition (A), 10 reps per model, actual API
# calls. Needs .env populated (`make keys-check` first). Sizes the rep count
# for `make run` and projects that run's cost. ~$0.04 at current config prices
# (see START_HERE.md) — safe to run on a personal card.
pilot: variants
	$(PY) analysis/pilot.py --jd anthropic-pm-beneficial-deployments-001 --reps 10

# The old mock-only pilot behaviour — no keys, no network, deterministic fake
# scores. Use this to sanity-check the pipeline itself, not to size real reps.
pilot-mock:
	$(PY) analysis/pilot.py --mock --jd synth-001 --reps 8

# Real run — needs .env populated and real JDs collected into jds/text/.
# Set REPS from the pilot's recommendation first.
REPS ?= 5
ABLATION ?= institution_swap
run:
	$(PY) scripts/run_screen.py --reps $(REPS) --ablation $(ABLATION)

analyze:
	$(PY) analysis/analyze.py $(RUN_ID)

parser-test:
	$(PY) parser_test/run_parsers.py

estimate:
	$(PY) scripts/estimate_cost.py --jds 20 --reps 3 --ablations 2
