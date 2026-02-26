"""設定モジュール — 環境変数・定数定義."""

import os
from pathlib import Path

from dotenv import load_dotenv

# .env はプロジェクトルートに配置
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# --- Supabase ---
SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_SECRET_KEY: str = os.environ["SUPABASE_SECRET_KEY"]

# --- 楽天検索 ---
SEARCH_URL_TEMPLATE = "https://search.rakuten.co.jp/search/mall/{keyword}/"

# --- User-Agent ---
PC_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
SP_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Mobile Safari/537.36"
)

USER_AGENTS = {
    "pc": PC_USER_AGENT,
    "sp": SP_USER_AGENT,
}

# --- リクエスト設定 ---
REQUEST_INTERVAL_MIN = 1.0
REQUEST_INTERVAL_MAX = 3.0
REQUEST_TIMEOUT = 15  # 秒

# --- デバイス ---
DEVICES = ["pc", "sp"]

# --- ログ ---
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
