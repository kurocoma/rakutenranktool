"""db モジュールのモックテスト."""

from unittest.mock import MagicMock, patch


class TestInsertRankings:
    """insert_rankings のテスト."""

    @patch("src.db._table")
    def test_insert_records(self, mock_table):
        from src.db import insert_rankings

        mock_chain = MagicMock()
        mock_table.return_value = mock_chain
        mock_chain.insert.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[])

        records = [
            {
                "product_id": "uuid-1",
                "keyword_id": "uuid-2",
                "device": "pc",
                "rank": 3,
                "page": 1,
                "searched_at": "2026-02-27T00:00:00+00:00",
            }
        ]
        insert_rankings(records)

        mock_table.assert_called_once_with("rankings")
        mock_chain.insert.assert_called_once_with(records)

    @patch("src.db._table")
    def test_skip_empty(self, mock_table):
        from src.db import insert_rankings

        insert_rankings([])
        mock_table.assert_not_called()


class TestInsertShopHitCounts:
    """insert_shop_hit_counts のテスト."""

    @patch("src.db._table")
    def test_insert_records(self, mock_table):
        from src.db import insert_shop_hit_counts

        mock_chain = MagicMock()
        mock_table.return_value = mock_chain
        mock_chain.insert.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[])

        records = [
            {
                "keyword_id": "uuid-2",
                "shop_url": "ichiban-okinawa",
                "device": "pc",
                "hit_count": 3,
                "searched_at": "2026-02-27T00:00:00+00:00",
            }
        ]
        insert_shop_hit_counts(records)

        mock_table.assert_called_once_with("shop_hit_counts")
        mock_chain.insert.assert_called_once_with(records)
