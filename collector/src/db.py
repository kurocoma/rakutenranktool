"""Supabase データベース操作モジュール.

全テーブルは rank_tracker スキーマに配置。
Supabase client のスキーマ指定は .schema() で行う。
"""

from __future__ import annotations

import logging

from supabase import create_client

from src.config import SUPABASE_SECRET_KEY, SUPABASE_URL

logger = logging.getLogger(__name__)

# rank_tracker スキーマを使うクライアント
_client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


def _table(name: str):
    """rank_tracker スキーマのテーブルを参照する."""
    return _client.schema("rank_tracker").table(name)


def get_active_product_keywords() -> list[dict]:
    """全商品×キーワードの組み合わせを取得する.

    Returns:
        [
            {
                "product_keyword_id": uuid,
                "product_id": uuid,
                "keyword_id": uuid,
                "shop_url": str,
                "product_code": str,  # product_id カラム（商品管理番号）
                "keyword": str,
                "display_name": str | None,
            },
            ...
        ]
    """
    resp = (
        _table("product_keywords")
        .select(
            "id, product_id, keyword_id, "
            "products:product_id(shop_url, product_id, display_name), "
            "keywords:keyword_id(keyword)"
        )
        .execute()
    )

    results = []
    for row in resp.data:
        product = row.get("products", {}) or {}
        keyword = row.get("keywords", {}) or {}
        results.append({
            "product_keyword_id": row["id"],
            "product_id": row["product_id"],
            "keyword_id": row["keyword_id"],
            "shop_url": product.get("shop_url", ""),
            "product_code": product.get("product_id", ""),
            "keyword": keyword.get("keyword", ""),
            "display_name": product.get("display_name"),
        })

    return results


def insert_rankings(records: list[dict]) -> None:
    """順位レコードを一括挿入する.

    Args:
        records: [{"product_id", "keyword_id", "device", "rank", "page", "searched_at"}, ...]
    """
    if not records:
        return
    _table("rankings").insert(records).execute()
    logger.info("rankings に %d 件挿入", len(records))


def insert_shop_hit_counts(records: list[dict]) -> None:
    """店舗ヒット数レコードを一括挿入する.

    Args:
        records: [{"keyword_id", "shop_url", "device", "hit_count", "searched_at"}, ...]
    """
    if not records:
        return
    _table("shop_hit_counts").insert(records).execute()
    logger.info("shop_hit_counts に %d 件挿入", len(records))
