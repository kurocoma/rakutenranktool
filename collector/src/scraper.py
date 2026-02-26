"""楽天検索結果のスクレイピングモジュール.

取得戦略:
  1. window.__INITIAL_STATE__ の JSON パース（主戦略）
  2. JSON-LD (schema.org/ItemList) パース（フォールバック）
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from src.config import (
    REQUEST_INTERVAL_MAX,
    REQUEST_INTERVAL_MIN,
    REQUEST_TIMEOUT,
    SEARCH_URL_TEMPLATE,
    USER_AGENTS,
)
from src.models import SearchResult

logger = logging.getLogger(__name__)

# item.rakuten.co.jp/{shop_url}/{product_id}/ から抽出する正規表現
_ITEM_URL_PATTERN = re.compile(
    r"https?://item\.rakuten\.co\.jp/([^/]+)/([^/?]+)/?"
)


def fetch_search_page(keyword: str, device: str) -> str | None:
    """楽天検索ページの HTML を取得する.

    Args:
        keyword: 検索キーワード
        device: "pc" or "sp"

    Returns:
        HTML 文字列。失敗時は None。
    """
    url = SEARCH_URL_TEMPLATE.format(keyword=quote(keyword, safe=""))
    headers = {
        "User-Agent": USER_AGENTS[device],
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        logger.error("検索ページ取得失敗: keyword=%s, device=%s, error=%s", keyword, device, e)
        return None


def wait_interval() -> None:
    """リクエスト間隔を 1〜3 秒ランダムで待機する."""
    interval = random.uniform(REQUEST_INTERVAL_MIN, REQUEST_INTERVAL_MAX)
    time.sleep(interval)


def parse_search_results(html: str) -> list[SearchResult]:
    """検索結果 HTML から商品リストを抽出する.

    主戦略: window.__INITIAL_STATE__ の JSON
    フォールバック: JSON-LD (schema.org/ItemList)
    """
    results = _parse_from_initial_state(html)
    if results:
        return results

    logger.warning("__INITIAL_STATE__ パース失敗。JSON-LD にフォールバック")
    results = _parse_from_json_ld(html)
    if results:
        return results

    logger.error("検索結果のパースに失敗しました")
    return []


def _parse_from_initial_state(html: str) -> list[SearchResult]:
    """window.__INITIAL_STATE__ JSON から商品リストを抽出する."""
    match = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.+?});\s*<\/script>", html, re.DOTALL)
    if not match:
        return []

    try:
        state = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        logger.warning("__INITIAL_STATE__ JSON パースエラー: %s", e)
        return []

    # items の取得パス: ichibaSearch.items
    items = _deep_get(state, "ichibaSearch", "items")
    if not items:
        return []

    results: list[SearchResult] = []
    for i, item in enumerate(items, start=1):
        shop_url_code = _deep_get(item, "shop", "urlCode")
        item_url = item.get("url") or item.get("originalItemUrl") or ""
        name = item.get("name", "")

        # shop.urlCode が取れない場合は URL から抽出
        if not shop_url_code:
            shop_url_code, product_id = _extract_from_url(item_url)
        else:
            _, product_id = _extract_from_url(item_url)

        if shop_url_code and product_id:
            results.append(SearchResult(
                position=i,
                shop_url=shop_url_code,
                product_id=product_id,
                name=name,
            ))

    return results


def _parse_from_json_ld(html: str) -> list[SearchResult]:
    """JSON-LD (schema.org/ItemList) から商品リストを抽出する."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchResult] = []

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue

        if data.get("@type") != "ItemList":
            continue

        for entry in data.get("itemListElement", []):
            product = entry.get("item", {})
            position = entry.get("position", 0)
            url = product.get("url", "")
            name = product.get("name", "")

            shop_url, product_id = _extract_from_url(url)
            if shop_url and product_id:
                results.append(SearchResult(
                    position=position,
                    shop_url=shop_url,
                    product_id=product_id,
                    name=name,
                ))

    return results


def _extract_from_url(url: str) -> tuple[str, str]:
    """item.rakuten.co.jp URL から shop_url と product_id を抽出する.

    Returns:
        (shop_url, product_id) のタプル。抽出失敗時は ("", "")。
    """
    m = _ITEM_URL_PATTERN.search(url)
    if m:
        return m.group(1), m.group(2)
    return "", ""


def _deep_get(d: dict, *keys: str):
    """ネストされた dict から安全に値を取得する."""
    for key in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(key)
    return d


def find_product_rank(
    results: list[SearchResult], shop_url: str, product_id: str
) -> int | None:
    """検索結果リストから指定商品の順位を見つける.

    Returns:
        順位（1始まり）。見つからなければ None（圏外）。
    """
    for r in results:
        if r.shop_url == shop_url and r.product_id == product_id:
            return r.position
    return None


def count_shop_hits(results: list[SearchResult], shop_url: str) -> int:
    """検索結果リストで指定 shop_url の商品が何件あるかカウントする."""
    return sum(1 for r in results if r.shop_url == shop_url)
