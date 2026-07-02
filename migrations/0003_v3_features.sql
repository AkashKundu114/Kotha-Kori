CREATE TABLE IF NOT EXISTS catalog_creations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) NOT NULL,
  raw_image_s3_key VARCHAR(500) NOT NULL,
  processed_image_s3_key VARCHAR(500),
  product_type VARCHAR(100),
  caption_bengali TEXT,
  price_suggestion_min NUMERIC(10,2),
  price_suggestion_max NUMERIC(10,2),
  vision_model_used VARCHAR(30),
  user_reported_shared BOOLEAN,
  user_reported_sale_resulted BOOLEAN,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_catalog_creations_user ON catalog_creations(user_id, created_at DESC);
CREATE TABLE IF NOT EXISTS market_prices (
  time TIMESTAMPTZ NOT NULL,
  block VARCHAR(100) NOT NULL,
  district VARCHAR(100),
  product_category VARCHAR(100) NOT NULL,
  avg_price_inr_per_unit NUMERIC(8,2),
  unit VARCHAR(20),
  data_source VARCHAR(20) NOT NULL,
  sample_count INTEGER,
  PRIMARY KEY (time, block, product_category, data_source)
);
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
    PERFORM create_hypertable('market_prices', 'time', if_not_exists => TRUE);
  END IF;
END $$;
CREATE INDEX IF NOT EXISTS idx_market_block_product
  ON market_prices(block, product_category, time DESC);
ALTER TABLE users ADD COLUMN IF NOT EXISTS business_categories TEXT[];
ALTER TABLE users ADD COLUMN IF NOT EXISTS self_reported_literacy VARCHAR(30);
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_modality VARCHAR(10) DEFAULT 'voice';
ALTER TABLE users ADD COLUMN IF NOT EXISTS dialect_hint VARCHAR(30);
ALTER TABLE users ADD COLUMN IF NOT EXISTS ledger_correction_rate NUMERIC(4,3) DEFAULT 0.0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS sessions_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS trust_stage VARCHAR(15) DEFAULT 'new';
ALTER TABLE ledger_entries ADD COLUMN IF NOT EXISTS extracted_by VARCHAR(20);
ALTER TABLE ledger_entries ADD COLUMN IF NOT EXISTS quantity NUMERIC(10,2);
ALTER TABLE ledger_entries ADD COLUMN IF NOT EXISTS unit VARCHAR(20);
