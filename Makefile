.PHONY: help setup dev pull-models seed-schemes test lint langfuse-init

help:
	@echo "Kotha-Khata v2 — Development Commands"
	@echo "======================================"
	@echo "make setup        — First-time dev setup (.env, base infra, migrations)"
	@echo "make dev          — Start all services locally"
	@echo "make pull-models  — Download Ollama models (tier-3 LLM + embeddings)"
	@echo "make seed-schemes — Ingest government scheme PDFs into RAG"
	@echo "make test         — Run unit tests (start here: tests/unit/test_grounding_verifier.py)"
	@echo "make lint         — ruff + mypy"

setup:
	cp -n .env.example .env || true
	pip install -r requirements.txt
	docker compose up -d postgres redis
	sleep 3
	alembic upgrade head
	psql $$DATABASE_URL -f migrations/0002_hybrid_search.sql

dev:
	docker compose up --build

pull-models:
	ollama pull qwen2.5:7b-instruct-q4_K_M
	ollama pull nomic-embed-text

seed-schemes:
	python scripts/seed_schemes.py

test:
	pytest tests/ -v

lint:
	ruff check . && mypy shared/ services/
