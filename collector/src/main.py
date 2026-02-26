"""楽天検索順位取得 — メインエントリーポイント.

処理フロー:
  1. DB から全商品×キーワード組み合わせを取得
  2. キーワード単位でユニークにまとめる
  3. 各キーワード × 各デバイスで検索実行
  4. 検索結果から全登録商品の順位を照合・記録
  5. 店舗ヒット数をカウント・記録
"""

from __future__ import annotations

import logging
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

from src.config import DEVICES, LOG_DIR
from src.db import get_active_product_keywords, insert_rankings, insert_shop_hit_counts
from src.scraper import (
    count_shop_hits,
    fetch_search_page,
    find_product_rank,
    parse_search_results,
    wait_interval,
)


def setup_logging() -> None:
    """ロギングの初期設定."""
    log_file = LOG_DIR / f"collector_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def run() -> None:
    """メイン処理."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("=== 検索順位取得 開始 ===")
    start_time = time.time()

    # 1. DB から全組み合わせを取得
    product_keywords = get_active_product_keywords()
    if not product_keywords:
        logger.warning("登録済みの商品・キーワードがありません。終了します。")
        return

    logger.info("取得した商品×キーワード組み合わせ: %d 件", len(product_keywords))

    # 2. キーワード単位でグルーピング
    # keyword_id -> {"keyword": str, "products": [{"product_id", "keyword_id", "shop_url", "product_code"}]}
    keyword_groups: dict[str, dict] = defaultdict(lambda: {"keyword": "", "products": []})
    for pk in product_keywords:
        group = keyword_groups[pk["keyword_id"]]
        group["keyword"] = pk["keyword"]
        group["products"].append(pk)

    logger.info("ユニークキーワード数: %d", len(keyword_groups))

    # 3. 各キーワード × 各デバイスで検索実行
    searched_at = datetime.now(timezone.utc).isoformat()
    ranking_records: list[dict] = []
    hit_count_records: list[dict] = []
    error_count = 0
    search_count = 0

    for keyword_id, group in keyword_groups.items():
        keyword = group["keyword"]
        products = group["products"]

        for device in DEVICES:
            logger.info("検索中: keyword=%s, device=%s", keyword, device)

            html = fetch_search_page(keyword, device)
            search_count += 1

            if html is None:
                error_count += 1
                logger.warning("スキップ: keyword=%s, device=%s", keyword, device)
                # 圏外として記録
                for p in products:
                    ranking_records.append({
                        "product_id": p["product_id"],
                        "keyword_id": keyword_id,
                        "device": device,
                        "rank": None,
                        "page": 1,
                        "searched_at": searched_at,
                    })
                wait_interval()
                continue

            # 4. 検索結果パース
            results = parse_search_results(html)
            logger.info("検索結果: %d 件の商品を取得", len(results))

            # 5. 各登録商品の順位を照合
            for p in products:
                rank = find_product_rank(results, p["shop_url"], p["product_code"])
                ranking_records.append({
                    "product_id": p["product_id"],
                    "keyword_id": keyword_id,
                    "device": device,
                    "rank": rank,
                    "page": 1,
                    "searched_at": searched_at,
                })
                status = f"{rank}位" if rank else "圏外"
                logger.info(
                    "  %s/%s → %s",
                    p["shop_url"], p["product_code"], status,
                )

            # 6. 店舗ヒット数をカウント（登録商品の shop_url をユニークにして集計）
            shop_urls_seen: set[str] = set()
            for p in products:
                if p["shop_url"] not in shop_urls_seen:
                    shop_urls_seen.add(p["shop_url"])
                    hit_count = count_shop_hits(results, p["shop_url"])
                    hit_count_records.append({
                        "keyword_id": keyword_id,
                        "shop_url": p["shop_url"],
                        "device": device,
                        "hit_count": hit_count,
                        "searched_at": searched_at,
                    })

            wait_interval()

    # 7. DB に一括書き込み
    logger.info("DB 書き込み: rankings=%d 件, shop_hit_counts=%d 件",
                len(ranking_records), len(hit_count_records))
    insert_rankings(ranking_records)
    insert_shop_hit_counts(hit_count_records)

    # サマリ
    elapsed = time.time() - start_time
    logger.info("=== 検索順位取得 完了 ===")
    logger.info("検索実行: %d 回, エラー: %d 回, 所要時間: %.1f 秒",
                search_count, error_count, elapsed)


if __name__ == "__main__":
    run()
