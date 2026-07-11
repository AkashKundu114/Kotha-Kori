.PHONY: help setup dev check-env test lint logs down

help:
	@echo "Kotha-Khata — Development Commands"
	@echo "===================================="
	@echo "make setup      — first-time setup: copy .env, validate it, bring up DB"
	@echo "make dev        — start the full stack (docker compose up --build)"
	@echo "make check-env  — verify required .env values are actually filled in"
	@echo "make test       — run unit tests (no network/API keys required)"
	@echo "make lint       — ruff + mypy"
	@echo "make logs       — tail gateway + worker logs"
	@echo "make down       — stop everything"

setup:
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env — now fill in the REQUIRED section before continuing."; else echo ".env already exists, leaving it alone."; fi
	python3 scripts/check_env.py || true

check-env:
	python3 scripts/check_env.py

dev: check-env
	docker compose up --build

test:
	pip install -q -r requirements.txt --break-system-packages 2>/dev/null || pip install -q -r requirements.txt
	pytest tests/ -v

lint:
	ruff check . && mypy shared/ services/

logs:
	docker compose logs -f gateway orchestrator-worker

down:
	docker compose down
