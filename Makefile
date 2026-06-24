.PHONY: help setup dev prod pull-models finetune-whisper finetune-llm \
        seed-schemes eval-stt audit-rag migrate test lint

help:
	@echo "Kotha-Kori Development Commands"
	@echo "================================="
	@echo "make setup          — First-time dev setup"
	@echo "make dev            — Start all services locally"
	@echo "make pull-models    — Download all Ollama base models"
	@echo "make finetune-llm   — Run QLoRA fine-tuning pipeline"
	@echo "make finetune-whisper — Fine-tune Whisper on Bengali audio"
	@echo "make seed-schemes   — Ingest government scheme documents into RAG"
	@echo "make eval-stt       — Run STT accuracy evaluation"
	@echo "make audit-rag      — Generate RAG hallucination audit report"
	@echo "make migrate        — Run Alembic DB migrations"
	@echo "make test           — Run full test suite"

setup:
	cp .env.example .env
	pip install -r requirements-dev.txt
	docker compose up -d postgres redis
	sleep 3
	make migrate

dev:
	docker compose up --build

pull-models:
	ollama pull qwen2.5:7b-instruct-q4_K_M
	ollama pull qwen2-vl:7b-instruct-q4_K_M
	ollama pull nomic-embed-text

finetune-llm:
	cd ml/llm-finetune && python finetune_qlora.py

finetune-whisper:
	cd ml/whisper-finetune && python finetune.py

seed-schemes:
	python scripts/seed_schemes.py

eval-stt:
	python scripts/eval_stt.py

audit-rag:
	python scripts/audit_rag.py

migrate:
	alembic upgrade head

test:
	pytest tests/ -v --cov=shared --cov=services

lint:
	ruff check . && mypy shared/ services/
