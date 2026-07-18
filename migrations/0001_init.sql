CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS shg_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  district VARCHAR(100),
  block VARCHAR(100),
  grade_level INTEGER,
  total_members INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  whatsapp_number VARCHAR(20) UNIQUE NOT NULL,
  name VARCHAR(255),
  shg_id UUID REFERENCES shg_groups(id),
  district VARCHAR(100),
  block VARCHAR(100),
  consent_given BOOLEAN DEFAULT FALSE,
  consent_given_at TIMESTAMPTZ,
  onboarded_at TIMESTAMPTZ DEFAULT NOW(),
  last_active_at TIMESTAMPTZ,
  business_categories TEXT[],
  self_reported_literacy VARCHAR(30),
  preferred_modality VARCHAR(10) DEFAULT 'voice',
  dialect_hint VARCHAR(30),
  ledger_correction_rate NUMERIC(4,3) DEFAULT 0.0,
  sessions_count INTEGER DEFAULT 0,
  trust_stage VARCHAR(15) DEFAULT 'new'
);
CREATE INDEX IF NOT EXISTS idx_users_whatsapp_number ON users(whatsapp_number);

CREATE TABLE IF NOT EXISTS ledger_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) NOT NULL,
  entry_date TIMESTAMPTZ DEFAULT NOW(),
  entry_type VARCHAR(10),
  amount_inr NUMERIC(10,2) NOT NULL,
  category VARCHAR(100),
  description_bengali TEXT,
  quantity NUMERIC(10,2),
  unit VARCHAR(20),
  raw_transcript TEXT,
  is_corrected BOOLEAN DEFAULT FALSE,
  correction_of UUID REFERENCES ledger_entries(id),
  extracted_by VARCHAR(20),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ledger_user_date ON ledger_entries(user_id, entry_date);
CREATE INDEX IF NOT EXISTS idx_ledger_category ON ledger_entries(category);

CREATE TABLE IF NOT EXISTS catalog_creations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) NOT NULL,
  raw_image_s3_key VARCHAR(500) NOT NULL,
  processed_image_s3_key VARCHAR(500),
  product_type VARCHAR(100),
  caption_bengali TEXT,
  ad_caption_bengali TEXT,
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
CREATE INDEX IF NOT EXISTS idx_market_block_product ON market_prices(block, product_category, time DESC);
