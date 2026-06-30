-- Adds the full-text search capability that docs/TRD.md's pipeline diagram
-- promised ("Hybrid: Semantic + Keyword: BM25 ... reciprocal rank fusion")
-- but v1's actual schema (TRD §3.5) only ever created a vector index.
--
-- Run after the base schema (carried over unchanged from v1 TRD §3.5/§3.6):
--   alembic upgrade head   (base tables: users, shg_groups, ledger_entries,
--                            scheme_documents, scheme_chunks, scheme_interactions)
-- then:
--   psql $DATABASE_URL -f migrations/0002_hybrid_search.sql

ALTER TABLE scheme_chunks
  ADD COLUMN IF NOT EXISTS chunk_bengali_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', coalesce(chunk_bengali, ''))) STORED;

CREATE INDEX IF NOT EXISTS idx_scheme_chunks_fts
  ON scheme_chunks USING GIN (chunk_bengali_tsv);

-- LangGraph's Postgres checkpointer creates its own tables on first
-- `checkpointer.setup()` call (see services/orchestrator/graph.py) — no
-- manual migration needed for conversation state, only for the RAG corpus.
