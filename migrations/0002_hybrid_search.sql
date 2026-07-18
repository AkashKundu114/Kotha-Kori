CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS scheme_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme_name VARCHAR(255) NOT NULL,
  scheme_code VARCHAR(50),
  document_type VARCHAR(50),
  content_bengali TEXT,
  content_english TEXT,
  source_url VARCHAR(500),
  source_file VARCHAR(500),
  last_verified_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scheme_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES scheme_documents(id) ON DELETE CASCADE,
  chunk_text TEXT NOT NULL,
  chunk_bengali TEXT,
  embedding vector(768),
  chunk_index INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheme_chunks_document ON scheme_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_scheme_chunks_embedding ON scheme_chunks
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

ALTER TABLE scheme_chunks
  ADD COLUMN IF NOT EXISTS chunk_bengali_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', coalesce(chunk_bengali, ''))) STORED;
CREATE INDEX IF NOT EXISTS idx_scheme_chunks_fts
  ON scheme_chunks USING GIN (chunk_bengali_tsv);
