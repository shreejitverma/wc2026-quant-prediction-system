SHELL := /bin/bash
UV := uv

.PHONY: help setup lock test lint fmt hooks selfcheck verify clean daily news-cycle api openapi bootstrap-data

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
	@echo "  api        run the terminal API (uvicorn, 127.0.0.1:8000)"
	@echo "  openapi    export OpenAPI schema to frontend/openapi.json"
	@echo "  bootstrap-data  create data/ ledger+runs artifacts (idempotent)"

setup:
	$(UV) sync --extra dev

lock:
	$(UV) lock

test:
	$(UV) run pytest

test-cov:
	$(UV) run pytest --cov=src --cov-fail-under=93

test-bench:
	$(UV) run pytest tests/benchmarks/ --benchmark-only --benchmark-autosave
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

api:
	$(UV) run uvicorn wc2026.api.server:app --host 127.0.0.1 --port 8000 --reload

openapi:
	$(UV) run python -m wc2026.api.export_openapi

bootstrap-data:
	$(UV) run python scripts/bootstrap_api_data.py

clean:
	rm -rf .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
