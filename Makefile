.PHONY: help demo demo-load test lint fmt hygiene clean venv

PY ?= python3
SIG ?= sig.jsonl
N ?= 276

help:
	@echo "Prime Tower Clocks — Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  make demo        -> compute signature for N=$(N), dump JSONL to $(SIG), reconstruct"
	@echo "  make demo-load   -> reconstruct from existing $(SIG)"
	@echo "  make test        -> run pytest"
	@echo "  make lint        -> ruff check ."
	@echo "  make fmt         -> ruff format ."
	@echo "  make hygiene     -> lint + test"
	@echo "  make clean       -> remove local artifacts + caches"
	@echo ""
	@echo "Vars:"
	@echo "  N=...            -> choose input integer (default: 276)"
	@echo "  SIG=...          -> choose JSONL output (default: sig.jsonl)"
	@echo "  PY=python3.x     -> choose python interpreter"

demo:
	$(PY) prime_tower_clocks.py $(N) --dump-jsonl $(SIG) --reconstruct

demo-load:
	$(PY) prime_tower_clocks.py --load-jsonl $(SIG) --reconstruct

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check .

fmt:
	$(PY) -m ruff format .

hygiene: lint test

clean:
	rm -f $(SIG)
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	rm -rf .ruff_cache .coverage htmlcov
