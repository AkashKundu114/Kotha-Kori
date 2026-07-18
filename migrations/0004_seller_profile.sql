CREATE TABLE IF NOT EXISTS seller_profiles (
  user_id UUID PRIMARY KEY REFERENCES users(id),
  product_type VARCHAR(100),
  production_cost NUMERIC(10,2),
  preferred_margin NUMERIC(4,3) DEFAULT 0.30,
  minimum_price NUMERIC(10,2),
  monthly_sales INTEGER DEFAULT 0,
  inventory INTEGER DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE market_prices ADD COLUMN IF NOT EXISTS demand_score NUMERIC(3,2);
