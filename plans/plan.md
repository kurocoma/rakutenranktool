# 実装計画 — 楽天検索順位取得ツール

| 項目 | 内容 |
|---|---|
| ドキュメントバージョン | 1.0 |
| 作成日 | 2026-02-26 |
| 対応スペック | docs/spec.md v1.0 |

---

## 全体スケジュール

```
Step 1: プロジェクト初期化 ─────────────────────┐
Step 2: DB スキーマ                              │ 基盤
Step 3: Python Collector                        │
Step 4: タスクスケジューラ連携                     ├─→ ここで E2E 動作確認
Step 5: Next.js ダッシュボード（一覧・CRUD）       │ フロント
Step 6: ダッシュボード（詳細・グラフ・CSV）         │
Step 7: 結合テスト・調整                          ┘
```

---

## Step 1: プロジェクト初期化

### 目的
モノレポの骨格を作り、開発環境を整える。

### タスク
- [ ] 1-1. Git リポジトリ初期化 (`git init`)
- [ ] 1-2. `.gitignore` 作成（Python / Node.js / `.env` / Supabase ローカル）
- [ ] 1-3. `collector/` ディレクトリ + `pyproject.toml`（uv 用）
  - 依存: `requests`, `beautifulsoup4`, `pandas`, `supabase`, `python-dotenv`
  - dev依存: `pytest`, `pytest-mock`
- [ ] 1-4. `dashboard/` ディレクトリ — `npx create-next-app@latest` で初期化
  - TypeScript, App Router, Tailwind CSS
  - 依存追加: `@supabase/supabase-js`, グラフライブラリ（`recharts`）
- [ ] 1-5. `supabase/migrations/` ディレクトリ作成
- [ ] 1-6. `scripts/` ディレクトリ作成
- [ ] 1-7. ルートに `.env.example` 配置（Supabase URL / Key のテンプレート）
- [ ] 1-8. GitHub リポジトリ作成 & 初回 push

### 受入条件
- `uv sync` が成功する
- `npm install && npm run dev` が成功する
- `.env` が `.gitignore` に含まれている

---

## Step 2: DB スキーマ作成

### 目的
Supabase にテーブルを作成し、マイグレーションファイルで管理する。

### タスク
- [ ] 2-1. Supabase プロジェクト作成（Web コンソール）
- [ ] 2-2. マイグレーションファイル作成: `supabase/migrations/001_initial_schema.sql`
  - `products` テーブル（UNIQUE: shop_url + product_id）
  - `keywords` テーブル（UNIQUE: keyword）
  - `product_keywords` 中間テーブル（UNIQUE: product_id + keyword_id）
  - `rankings` テーブル（インデックス: product_id + keyword_id + searched_at）
  - `shop_hit_counts` テーブル
  - 全テーブルに `created_at DEFAULT now()` 設定
  - RLS ポリシー: Phase 1 では全操作を許可（`anon` キーで読み書き可能）
- [ ] 2-3. Supabase ダッシュボードから SQL を実行してテーブル作成
- [ ] 2-4. `.env` に `SUPABASE_URL` と `SUPABASE_KEY` を設定

### 受入条件
- 5 テーブルが Supabase 上に作成されている
- マイグレーション SQL が `supabase/migrations/` にコミットされている

---

## Step 3: Python Collector 実装

### 目的
楽天検索結果をスクレイピングし、Supabase に順位データを書き込む。

### ディレクトリ構成
```
collector/
├── src/
│   ├── __init__.py
│   ├── main.py            ← エントリーポイント
│   ├── config.py           ← 環境変数読込み・定数定義
│   ├── scraper.py          ← 楽天検索HTMLの取得とパース
│   ├── db.py               ← Supabase クライアント・CRUD
│   └── models.py           ← データクラス（dataclass）
├── tests/
│   ├── __init__.py
│   ├── test_scraper.py
│   ├── test_db.py
│   └── fixtures/           ← テスト用 HTML スナップショット
│       ├── search_pc.html
│       └── search_sp.html
└── pyproject.toml
```

### タスク

#### 3-1. config.py
- [ ] 環境変数読込み（`SUPABASE_URL`, `SUPABASE_KEY`）
- [ ] 定数定義
  - `SEARCH_URL_TEMPLATE = "https://search.rakuten.co.jp/search/mall/{keyword}/"`
  - `PC_USER_AGENT` / `SP_USER_AGENT`
  - `REQUEST_INTERVAL_MIN = 1` / `REQUEST_INTERVAL_MAX = 3`
  - `DEVICES = ["pc", "sp"]`

#### 3-2. scraper.py
- [ ] `fetch_search_page(keyword: str, device: str) -> str`
  - User-Agent 切替
  - `requests.get()` でHTML取得
  - `random.uniform(1, 3)` 秒のインターバル
  - タイムアウト設定（10秒）
  - HTTPエラー時は例外をログ出力して `None` を返す
- [ ] `parse_search_results(html: str) -> list[SearchResult]`
  - BeautifulSoup で検索結果の商品リンクを抽出
  - 各商品リンクから `shop_url` と `product_id` を抽出
  - 順位（1〜45）を付与して返す
- [ ] `find_product_rank(results: list, shop_url: str, product_id: str) -> int | None`
  - 結果リスト内を照合、見つかれば順位、なければ `None`（圏外）
- [ ] `count_shop_hits(results: list, shop_url: str) -> int`
  - 指定 shop_url の商品が検索結果に何件あるかカウント

#### 3-3. db.py
- [ ] Supabase クライアント初期化
- [ ] `get_active_product_keywords() -> list[dict]`
  - product_keywords + products + keywords を JOIN して全組み合わせ取得
- [ ] `insert_ranking(product_id, keyword_id, device, rank, page, searched_at)`
- [ ] `insert_shop_hit_count(keyword_id, shop_url, device, hit_count, searched_at)`

#### 3-4. main.py
- [ ] メイン処理フロー:
  1. DB から全商品×キーワード組み合わせを取得
  2. キーワード単位でユニークにまとめる（同一キーワードは1回の検索で済ませる）
  3. 各キーワード × 各デバイスで検索実行
  4. 検索結果から全登録商品の順位を照合・記録
  5. 店舗ヒット数をカウント・記録
- [ ] ログ設定（`logging` モジュール、ファイル + コンソール出力）
- [ ] 実行サマリ出力（処理件数、エラー件数、所要時間）

#### 3-5. テスト
- [ ] `tests/fixtures/` に楽天検索結果のHTMLスナップショットを保存
- [ ] `test_scraper.py`: パース処理のユニットテスト
  - 商品リンクの抽出が正しいか
  - shop_url / product_id の分割が正しいか
  - 順位番号が正しいか
- [ ] `test_db.py`: DB操作のモックテスト

### 受入条件
- `uv run python -m src.main` で手動実行が成功する
- Supabase の `rankings` テーブルにデータが入る
- `uv run pytest` が全テスト pass する

---

## Step 4: Windows タスクスケジューラ連携

### 目的
2 時間おきに collector を自動実行する bat ファイルを作成する。

### タスク
- [ ] 4-1. `scripts/run_collector.bat` 作成
  - UTF-8 BOM 付きで保存
  - `chcp 65001` で文字コード設定
  - プロジェクトディレクトリへ `cd`
  - `uv run python -m src.main` を実行
  - 実行ログをファイルに追記（`>> logs/collector.log 2>&1`）
- [ ] 4-2. `collector/logs/` ディレクトリ作成、`.gitkeep` 配置
- [ ] 4-3. タスクスケジューラ登録手順書を `docs/scheduler-setup.md` に記載
  - 2 時間間隔の設定方法
  - PC スリープ時の挙動について注意書き

### 受入条件
- bat ファイルをダブルクリックで collector が実行される
- 日本語パスを含む環境で文字化けしない
- ログファイルに実行結果が記録される

---

## Step 5: Next.js ダッシュボード（一覧・CRUD）

### 目的
商品の一覧表示と、商品・キーワードの登録・編集・削除を実装する。

### ディレクトリ構成（App Router）
```
dashboard/
├── app/
│   ├── layout.tsx
│   ├── page.tsx              ← 商品一覧（トップ）
│   └── products/
│       └── [id]/
│           └── page.tsx      ← 商品詳細ダッシュボード
├── components/
│   ├── ProductList.tsx        ← 商品リストコンポーネント
│   ├── ProductCard.tsx        ← 商品カード（順位サマリ表示）
│   ├── SearchFilter.tsx       ← 検索・絞り込みフォーム
│   ├── RankBadge.tsx          ← 順位バッジ（上昇↑下降↓停滞→）
│   ├── RegisterModal.tsx      ← 新規登録モーダル
│   └── ConfirmDialog.tsx      ← 削除確認ダイアログ
├── lib/
│   ├── supabase.ts            ← Supabase クライアント
│   └── types.ts               ← 型定義
└── ...
```

### タスク

#### 5-1. Supabase クライアント設定
- [ ] `lib/supabase.ts` — 環境変数から初期化
- [ ] `lib/types.ts` — Product, Keyword, ProductKeyword, Ranking 等の型定義

#### 5-2. 商品一覧画面（トップ）
- [ ] `SearchFilter.tsx` — キーワード / 商品名での絞り込み入力
- [ ] `ProductCard.tsx` — 商品情報 + 最新順位サマリ + 前回比の変動表示
- [ ] `ProductList.tsx` — カードのリスト表示
- [ ] 変動フィルタ（上昇・下降・停滞・圏外）のタブ/ボタン
- [ ] `page.tsx` — 上記を組み合わせたトップページ

#### 5-3. 商品・キーワード CRUD
- [ ] `RegisterModal.tsx` — 新規登録フォーム
  - 店舗URL + 商品管理番号 + キーワード（複数追加可能）
  - Supabase へ INSERT（products → keywords → product_keywords）
- [ ] 編集機能 — 表示名の変更、キーワードの追加・削除
- [ ] 削除機能 — 確認ダイアログ付き。関連する product_keywords も CASCADE 削除

### 受入条件
- 商品の一覧が表示され、絞り込みができる
- 新規登録・編集・削除が動作する
- 順位の上昇/下降/停滞が視覚的にわかる

---

## Step 6: ダッシュボード（詳細・グラフ・CSV）

### 目的
商品詳細画面に順位推移グラフ・他社比較・CSV ダウンロードを実装する。

### タスク

#### 6-1. 商品詳細画面
- [ ] `products/[id]/page.tsx` — キーワード別の PC / SP 順位一覧テーブル
- [ ] 期間選択（直近24時間 / 7日 / 30日 / カスタム）

#### 6-2. 順位推移グラフ
- [ ] `recharts` による折れ線グラフ
  - X軸: 日時（searched_at）
  - Y軸: 順位（逆順: 1位が上）
  - 系列: PC / SP を色分け
  - 圏外は Y軸の最大値+αの位置にプロット（視覚的に区別）
- [ ] キーワード切替でグラフが更新される

#### 6-3. 他社比較
- [ ] 同一キーワードに紐付く全商品の順位を横並び表示
- [ ] テーブル形式: 商品 | PC順位 | SP順位 | 変動

#### 6-4. CSV ダウンロード
- [ ] 表示中のデータ（順位一覧 or 推移データ）を CSV として生成
- [ ] ブラウザ側で `Blob` + `URL.createObjectURL` でダウンロード
- [ ] カラム: キーワード, 商品(shop_url/product_id), デバイス, 順位, 取得日時

### 受入条件
- 商品詳細画面でキーワード別順位が見える
- グラフが正しく描画される（圏外も含む）
- CSV がダウンロードでき、Excel で開ける（BOM 付き UTF-8）

---

## Step 7: 結合テスト・調整

### 目的
全体を通して動作確認し、不具合を修正する。

### タスク
- [ ] 7-1. テストデータ投入（商品3〜5件、キーワード5〜10件）
- [ ] 7-2. collector を手動実行し、Supabase にデータが入ることを確認
- [ ] 7-3. ダッシュボードで一覧・詳細・グラフ・CSV 全画面を確認
- [ ] 7-4. bat ファイルでの自動実行を確認
- [ ] 7-5. エッジケース確認
  - 全商品が圏外のキーワード
  - キーワードに記号・スペースが含まれる場合の URL エンコーディング
  - Supabase 接続エラー時の挙動
- [ ] 7-6. `collector/tests/` の pytest 全 pass 確認
- [ ] 7-7. `dashboard/` の `npm run lint` + `npm run build` 成功確認

### 受入条件
- spec.md の受入条件（8項）を全て満たす
- テスト・lint・ビルドが pass する
- ログにエラーが出ない（想定内のスキップは OK）

---

## 技術的な注意事項

### スクレイピング
- 楽天検索結果の HTML 構造はサイト改修で変わる可能性がある。パーサーは `scraper.py` に集約し、変更時の影響範囲を限定する
- リクエスト間隔: `random.uniform(1, 3)` 秒（検知回避のためランダム化）
- User-Agent は一般的なブラウザの文字列を使用

### データベース
- `rankings` テーブルは肥大化しやすい（4,800件/日）。Phase 2 で古いデータのアーカイブ/削除ポリシーを検討
- インデックス: `rankings(product_id, keyword_id, searched_at)` は必須

### フロントエンド
- Supabase クライアントは `anon` キーで直接アクセス（Phase 1）。Phase 2 で RLS + Auth に切替
- グラフの Y 軸は逆順（1位が上）にすること。圏外は特殊表示

### bat ファイル
- 先頭に `chcp 65001` を入れて UTF-8 モードに切替
- ファイル自体は UTF-8 BOM 付きで保存
- パス内の日本語ディレクトリ名に注意
