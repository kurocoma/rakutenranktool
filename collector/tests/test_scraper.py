"""scraper モジュールのユニットテスト."""

from pathlib import Path

from src.scraper import (
    _extract_from_url,
    count_shop_hits,
    find_product_rank,
    parse_search_results,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


class TestParseSearchResults:
    """parse_search_results のテスト."""

    def test_initial_state_parse(self):
        """__INITIAL_STATE__ JSON から正しくパースできること."""
        html = _load_fixture("search_initial_state.html")
        results = parse_search_results(html)

        assert len(results) == 5
        assert results[0].position == 1
        assert results[0].shop_url == "aikanhonpo"
        assert results[0].product_id == "1355740"
        assert results[0].name == "ノニジュース 900ml オーガニック"

    def test_initial_state_positions(self):
        """順位が 1 始まりで連番になっていること."""
        html = _load_fixture("search_initial_state.html")
        results = parse_search_results(html)

        positions = [r.position for r in results]
        assert positions == [1, 2, 3, 4, 5]

    def test_initial_state_all_shops(self):
        """全商品の shop_url が正しく抽出されること."""
        html = _load_fixture("search_initial_state.html")
        results = parse_search_results(html)

        shops = [r.shop_url for r in results]
        assert shops == [
            "aikanhonpo", "hyperlink", "ichiban-okinawa",
            "hands-web", "supplement-shop",
        ]

    def test_json_ld_fallback(self):
        """JSON-LD フォールバックで正しくパースできること."""
        html = _load_fixture("search_json_ld.html")
        results = parse_search_results(html)

        assert len(results) == 3
        assert results[0].position == 1
        assert results[0].shop_url == "aikanhonpo"
        assert results[1].shop_url == "ichiban-okinawa"
        assert results[2].shop_url == "hyperlink"

    def test_empty_html(self):
        """空の HTML では空リストを返すこと."""
        results = parse_search_results("<html><body></body></html>")
        assert results == []


class TestExtractFromUrl:
    """_extract_from_url のテスト."""

    def test_standard_url(self):
        shop, pid = _extract_from_url(
            "https://item.rakuten.co.jp/ichiban-okinawa/noni-jyuce3/"
        )
        assert shop == "ichiban-okinawa"
        assert pid == "noni-jyuce3"

    def test_url_with_query(self):
        shop, pid = _extract_from_url(
            "https://item.rakuten.co.jp/shop1/item123/?variantId=abc"
        )
        assert shop == "shop1"
        assert pid == "item123"

    def test_url_without_trailing_slash(self):
        shop, pid = _extract_from_url(
            "https://item.rakuten.co.jp/shop1/item123"
        )
        assert shop == "shop1"
        assert pid == "item123"

    def test_invalid_url(self):
        shop, pid = _extract_from_url("https://www.rakuten.co.jp/shop1/")
        assert shop == ""
        assert pid == ""


class TestFindProductRank:
    """find_product_rank のテスト."""

    def test_found(self):
        html = _load_fixture("search_initial_state.html")
        results = parse_search_results(html)

        rank = find_product_rank(results, "ichiban-okinawa", "noni-jyuce3")
        assert rank == 3

    def test_not_found(self):
        html = _load_fixture("search_initial_state.html")
        results = parse_search_results(html)

        rank = find_product_rank(results, "nonexistent-shop", "no-product")
        assert rank is None

    def test_first_position(self):
        html = _load_fixture("search_initial_state.html")
        results = parse_search_results(html)

        rank = find_product_rank(results, "aikanhonpo", "1355740")
        assert rank == 1


class TestCountShopHits:
    """count_shop_hits のテスト."""

    def test_single_hit(self):
        html = _load_fixture("search_initial_state.html")
        results = parse_search_results(html)

        count = count_shop_hits(results, "ichiban-okinawa")
        assert count == 1

    def test_no_hits(self):
        html = _load_fixture("search_initial_state.html")
        results = parse_search_results(html)

        count = count_shop_hits(results, "nonexistent-shop")
        assert count == 0
