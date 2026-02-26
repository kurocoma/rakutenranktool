# 検索順位取得ツール — CLAUDE.md

## プロジェクト概要
楽天市場の検索結果から指定商品の掲載順位を定期取得し、Supabase に蓄積、Next.js ダッシュボードで可視化するツール。

## リポジトリ構成（モノレポ）
```
search-rank-tracker/
├── CLAUDE.md          ← 本ファイル（AI 向けルール）
├── docs/
│   └── spec.md        ← 要件定義書
├── plans/
│   └── plan.md        ← 実装計画
├── collector/          ← Python 3.11+（スクレイピング＋DB書込み）
│   ├── src/
│   ├── tests/
│   └── pyproject.toml
├── dashboard/          ← Next.js（Supabase 読取り＋可視化）
│   └── ...
├── supabase/           ← マイグレーション・シード
│   └── migrations/
└── scripts/            ← bat / ps1 ヘルパー
```

## 技術スタック
| レイヤー | 技術 | 備考 |
|---|---|---|
| スクレイピング | Python 3.11+ / requests / BeautifulSoup | JS描画不可時は Playwright へ切替 |
| データ加工 | pandas | CSV 出力にも利用 |
| DB | Supabase (PostgreSQL) | スキーマ `rank_tracker` で分離。ローカル運用。将来 Auth 追加予定 |
| フロント | Next.js | Supabase client で直接読取り |
| スケジューラ | Windows タスクスケジューラ | 2 時間おき（1日12回） |
| パッケージ管理 | uv (Python) / npm or pnpm (Next.js) | |

## 対象サイト
- 検索URL: `https://search.rakuten.co.jp/search/mall/{keyword}/`
- 商品URL: `https://item.rakuten.co.jp/{shop_url}/{product_id}/`
- 1ページ目（最大45件）のみ取得。見つからなければ「圏外」
- PC / SP は User-Agent 切替で取得

## 商品特定ロジック
- 検索結果の各商品リンクから `shop_url` と `product_id` を抽出
- 登録済みの `shop_url` + `product_id` と照合して順位を記録
- 自社・他社の区別フラグは持たない（同一テーブルでフラットに管理）

## データ規模（初期）
- 商品: 10、キーワード: 20、巡回: 12回/日、デバイス: 2
- → 最大 4,800 レコード/日

## 絶対ルール
1. **ファイル作成は本プロジェクトディレクトリ内のみ**
   `C:\Users\hppym\開発案件\検索順位取得ツール\` 配下以外にファイル・フォルダを作成してはならない。
2. **bat / ps1 ファイルのエンコーディング**
   日本語 Windows 環境で動作させるため、以下を厳守:
   - `.bat` ファイルは **Shift_JIS (cp932)** で保存、先頭に `chcp 65001` を入れる場合は **UTF-8 BOM 付き** で保存
   - `.ps1` ファイルは **UTF-8 BOM 付き** で保存
   - ファイル内のパスに日本語が含まれる場合は特に注意
3. **スクレイピングの配慮**
   - リクエスト間隔は `random.uniform(1, 3)` 秒のランダムインターバル
   - User-Agent を適切に設定（bot と分かる文字列は避ける）
4. **DB スキーマ変更は必ずマイグレーションファイルで管理**
   `supabase/migrations/` に SQL ファイルを追加する形で行う。
   - **スキーマ分離**: 全テーブルは `rank_tracker` スキーマに配置（`public` スキーマは使わない）
   - Supabase の同一プロジェクトを複数ツールで共有するため、スキーマで名前空間を分離する
   - テーブル参照は必ず `rank_tracker.products` のように完全修飾名を使う
5. **テスト**
   - collector: pytest でユニットテスト必須
   - dashboard: 最低限 lint (ESLint) を通す
6. **認証は Phase 2 以降**
   現時点ではログイン不要。将来 Supabase Auth を導入予定のため、API キーのハードコードは禁止（環境変数 `.env` で管理）。
7. **機密情報**
   `.env` ファイルは `.gitignore` に含める。Supabase URL / Key は絶対にコミットしない。

## 開発フロー
1. `docs/spec.md` を確認 → 要件を理解
2. `plans/plan.md` を確認 → 実装タスクを把握
3. 実装は各ディレクトリ内で行い、PR 単位でレビュー
4. テスト → ローカル動作確認 → マージ

## コマンドリファレンス（想定）
```bash
# collector
cd collector && uv run python -m src.main          # 手動実行
cd collector && uv run pytest                        # テスト

# dashboard
cd dashboard && npm run dev                          # 開発サーバー
cd dashboard && npm run build                        # ビルド
cd dashboard && npm run lint                         # lint
```
