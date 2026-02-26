"""データモデル定義."""

from dataclasses import dataclass


@dataclass
class SearchResult:
    """検索結果の1商品を表す."""

    position: int  # 検索結果内の順位（1始まり）
    shop_url: str  # 店舗URL識別子 (例: ichiban-okinawa)
    product_id: str  # 商品管理番号 (例: noni-jyuce3)
    name: str  # 商品名


@dataclass
class RankRecord:
    """DB に書き込む順位レコード."""

    product_id: str  # uuid
    keyword_id: str  # uuid
    device: str  # "pc" or "sp"
    rank: int | None  # None = 圏外
    page: int
    searched_at: str  # ISO 8601


@dataclass
class ShopHitRecord:
    """DB に書き込む店舗ヒット数レコード."""

    keyword_id: str  # uuid
    shop_url: str
    device: str
    hit_count: int
    searched_at: str  # ISO 8601
