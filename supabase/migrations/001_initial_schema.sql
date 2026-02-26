-- ============================================================
-- 楽天検索順位取得ツール — 初期スキーマ
-- スキーマ: rank_tracker（他プロジェクトと分離）
-- ============================================================

-- 1. スキーマ作成
CREATE SCHEMA IF NOT EXISTS rank_tracker;

-- 2. products（商品マスタ）
CREATE TABLE rank_tracker.products (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    shop_url    text NOT NULL,
    product_id  text NOT NULL,
    display_name text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (shop_url, product_id)
);

COMMENT ON TABLE rank_tracker.products IS '商品マスタ。shop_url + product_id で一意に特定';

-- 3. keywords（キーワードマスタ）
CREATE TABLE rank_tracker.keywords (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword     text NOT NULL UNIQUE,
    created_at  timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE rank_tracker.keywords IS '検索キーワードマスタ';

-- 4. product_keywords（商品×キーワード 中間テーブル）
CREATE TABLE rank_tracker.product_keywords (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id  uuid NOT NULL REFERENCES rank_tracker.products(id) ON DELETE CASCADE,
    keyword_id  uuid NOT NULL REFERENCES rank_tracker.keywords(id) ON DELETE CASCADE,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (product_id, keyword_id)
);

COMMENT ON TABLE rank_tracker.product_keywords IS '商品とキーワードの多対多リレーション';

-- 5. rankings（順位記録）
CREATE TABLE rank_tracker.rankings (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id  uuid NOT NULL REFERENCES rank_tracker.products(id) ON DELETE CASCADE,
    keyword_id  uuid NOT NULL REFERENCES rank_tracker.keywords(id) ON DELETE CASCADE,
    device      text NOT NULL CHECK (device IN ('pc', 'sp')),
    rank        integer,  -- null = 圏外
    page        integer NOT NULL DEFAULT 1,
    searched_at timestamptz NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE rank_tracker.rankings IS '検索順位の記録。rank が null の場合は圏外';

-- パフォーマンス用インデックス
CREATE INDEX idx_rankings_product_keyword_searched
    ON rank_tracker.rankings (product_id, keyword_id, searched_at DESC);

CREATE INDEX idx_rankings_searched_at
    ON rank_tracker.rankings (searched_at DESC);

-- 6. shop_hit_counts（店舗ヒット数）
CREATE TABLE rank_tracker.shop_hit_counts (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword_id  uuid NOT NULL REFERENCES rank_tracker.keywords(id) ON DELETE CASCADE,
    shop_url    text NOT NULL,
    device      text NOT NULL CHECK (device IN ('pc', 'sp')),
    hit_count   integer NOT NULL DEFAULT 0,
    searched_at timestamptz NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE rank_tracker.shop_hit_counts IS 'キーワード検索結果における店舗別ヒット数';

CREATE INDEX idx_shop_hit_counts_keyword_searched
    ON rank_tracker.shop_hit_counts (keyword_id, searched_at DESC);

-- ============================================================
-- RLS（Row Level Security）
-- Phase 1: 全操作を許可（ローカル運用・認証なし）
-- Phase 2 で Supabase Auth 導入時にポリシーを変更
-- ============================================================

ALTER TABLE rank_tracker.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE rank_tracker.keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE rank_tracker.product_keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE rank_tracker.rankings ENABLE ROW LEVEL SECURITY;
ALTER TABLE rank_tracker.shop_hit_counts ENABLE ROW LEVEL SECURITY;

-- Phase 1: anon / authenticated ロールに全操作を許可
CREATE POLICY "Allow all for products"
    ON rank_tracker.products FOR ALL
    USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for keywords"
    ON rank_tracker.keywords FOR ALL
    USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for product_keywords"
    ON rank_tracker.product_keywords FOR ALL
    USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for rankings"
    ON rank_tracker.rankings FOR ALL
    USING (true) WITH CHECK (true);

CREATE POLICY "Allow all for shop_hit_counts"
    ON rank_tracker.shop_hit_counts FOR ALL
    USING (true) WITH CHECK (true);

-- ============================================================
-- スキーマへのアクセス権限付与
-- Supabase の anon / authenticated ロールがアクセスできるようにする
-- ============================================================

GRANT USAGE ON SCHEMA rank_tracker TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA rank_tracker TO anon, authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA rank_tracker TO anon, authenticated;

-- 今後作成されるテーブルにも自動で権限付与
ALTER DEFAULT PRIVILEGES IN SCHEMA rank_tracker
    GRANT ALL ON TABLES TO anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA rank_tracker
    GRANT ALL ON SEQUENCES TO anon, authenticated;

-- updated_at 自動更新トリガー
CREATE OR REPLACE FUNCTION rank_tracker.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_products_updated_at
    BEFORE UPDATE ON rank_tracker.products
    FOR EACH ROW EXECUTE FUNCTION rank_tracker.update_updated_at();
