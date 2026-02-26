# Supabase CLI セットアップ & マイグレーション手順

## 前提条件
- Node.js がインストール済み（npx が使える状態）
- Supabase アカウントを持っている

## 1. Supabase CLI インストール

Windows では npx 経由で利用する（グローバルインストール不要）。

```powershell
npx supabase --version
```

## 2. Supabase にログイン

```powershell
npx supabase login
```

- ブラウザが開くので Supabase にログイン
- トークンが自動で設定される
- **非TTY環境の場合**: Supabase ダッシュボード → Settings → Access Tokens でトークンを生成し:
  ```powershell
  npx supabase login --token <your-token>
  ```

## 3. プロジェクト初期化（初回のみ）

```powershell
cd "C:\Users\hppym\開発案件\検索順位取得ツール"
npx supabase init --workdir .
```

`supabase/config.toml` が生成される。以下を設定:

```toml
project_id = "rakuten-rank-tracker"

[api]
schemas = ["public", "graphql_public", "rank_tracker"]
```

## 4. リモートプロジェクトにリンク（初回のみ）

```powershell
npx supabase link --project-ref <project-ref-id>
```

project-ref-id は Supabase ダッシュボードの URL から取得:
`https://supabase.com/dashboard/project/<project-ref-id>`

例:
```powershell
npx supabase link --project-ref iqbsrmzntakldkpxvqeu
```

## 5. マイグレーション作成

`supabase/migrations/` に SQL ファイルを追加:

```
supabase/migrations/
├── 001_initial_schema.sql
├── 002_add_new_table.sql
└── ...
```

命名規則: `<連番>_<説明>.sql`

## 6. マイグレーション適用

```powershell
npx supabase db push
```

- 未適用のマイグレーションのみ実行される
- 確認プロンプトが出るので `Y` で適用

## 7. その他の便利コマンド

```powershell
# リモートDBの現在のスキーマをダンプ
npx supabase db dump --schema rank_tracker -f dump.sql

# マイグレーション状態を確認
npx supabase migration list

# リモートDBとの差分を確認
npx supabase db diff --schema rank_tracker
```

## トラブルシューティング

### `Missing required field in config: project_id`
→ `supabase/config.toml` の `project_id` が空。値を設定する。

### `Cannot use automatic login flow inside non-TTY environments`
→ PowerShell で直接 `npx supabase login` を実行するか、`--token` フラグを使う。

### カスタムスキーマが API から見えない
→ `config.toml` の `schemas` に追加 + Supabase ダッシュボードの API Settings → Exposed schemas にも追加が必要。
