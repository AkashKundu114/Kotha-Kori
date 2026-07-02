ALTER TABLE scheme_chunks
  ADD COLUMN IF NOT EXISTS chunk_bengali_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', coalesce(chunk_bengali, ''))) STORED;
CREATE INDEX IF NOT EXISTS idx_scheme_chunks_fts
  ON scheme_chunks USING GIN (chunk_bengali_tsv);
