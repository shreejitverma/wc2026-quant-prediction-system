SHELL := /bin/bash
UV := uv

.PHONY: help setup lock test lint fmt hooks selfcheck verify clean daily news-cycle

help:
	@echo "Targets:"
	@echo "  setup      uv sync (create venv + install deps from lockfile)"
	@echo "  test       run pytest"
	@echo "  lint       ruff check"
	@echo "  fmt        ruff format"
	@echo "  hooks      install pre-commit hooks (incl. leakage gate)"
	@echo "  selfcheck  run Phase 0+1+2 end-to-end smoke tests"
	@echo "  verify     lint + test + selfcheck (full gate)"
	@echo "  daily      [Phase 8] full pipeline (placeholder)"
	@echo "  news-cycle [Phase 8] event-driven fast path (placeholder)"

setup:
	$(UV) sync --extra dev

lock:
	$(UV) lock

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check src tests scripts

fmt:
	$(UV) run ruff format src tests scripts

hooks:
	$(UV) run pre-commit install

selfcheck:
	$(UV) run python scripts/phase0_selfcheck.py
	$(UV) run python scripts/phase2_selfcheck.py

verify: lint test selfcheck

daily:
	@echo "[Phase 8] daily pipeline not implemented yet (ingest->...->evaluation)."

news-cycle:
	@echo "[Phase 8] news fast-path not implemented yet (lineups/injuries)."

clean:
	rm -rf .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
