"""Tests for GSC cross-linker module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from seo_linker.gsc.client import PageMetrics, QueryData
from seo_linker.gsc.cross_linker import find_cross_link_gaps, _short_path


class TestShortPath:
    def test_extracts_last_segment(self):
        assert _short_path("https://www.example.com/blog/running-guide") == "running-guide"

    def test_handles_trailing_slash(self):
        assert _short_path("https://www.example.com/blog/running-guide/") == "running-guide"

    def test_handles_no_path(self):
        result = _short_path("https://example.com")
        assert result  # Should return something, not empty


class TestFindCrossLinkGaps:
    def _make_mock_client(self, page_queries, page_metrics):
        """Create a mock GSCClient with given data."""
        client = MagicMock()
        client.get_magazine_queries.return_value = page_queries
        client.get_page_metrics.return_value = page_metrics
        return client

    def test_no_pages_returns_empty(self):
        client = self._make_mock_client({}, {})
        result = find_cross_link_gaps(client, "sc-domain:test.com")
        assert result == []

    def test_single_page_returns_empty(self):
        client = self._make_mock_client(
            {"https://test.com/a": [QueryData(query="running guide", impressions=100)]},
            {},
        )
        result = find_cross_link_gaps(client, "sc-domain:test.com")
        assert result == []

    def test_shared_queries_produce_bidirectional_opportunities(self):
        page_queries = {
            "https://test.com/article-a": [
                QueryData(query="running shoes", impressions=500),
                QueryData(query="trail running", impressions=300),
                QueryData(query="best running gear", impressions=200),
            ],
            "https://test.com/article-b": [
                QueryData(query="trail running", impressions=400),
                QueryData(query="best running gear", impressions=250),
                QueryData(query="hiking boots", impressions=100),
            ],
        }
        page_metrics = {
            "https://test.com/article-a": PageMetrics(url="https://test.com/article-a", impressions=5000, position=8.0),
            "https://test.com/article-b": PageMetrics(url="https://test.com/article-b", impressions=3000, position=12.0),
        }

        client = self._make_mock_client(page_queries, page_metrics)
        result = find_cross_link_gaps(client, "sc-domain:test.com")

        # Should have 2 bidirectional opportunities (A->B and B->A)
        assert len(result) == 2
        source_target_pairs = {(o.source_url, o.target_url) for o in result}
        assert ("https://test.com/article-a", "https://test.com/article-b") in source_target_pairs
        assert ("https://test.com/article-b", "https://test.com/article-a") in source_target_pairs

        # Check shared queries
        for opp in result:
            assert opp.shared_query_count == 2
            assert "trail running" in opp.shared_queries
            assert "best running gear" in opp.shared_queries

    def test_min_shared_queries_filter(self):
        page_queries = {
            "https://test.com/a": [QueryData(query="shoes", impressions=100)],
            "https://test.com/b": [QueryData(query="shoes", impressions=100)],
        }
        page_metrics = {}

        client = self._make_mock_client(page_queries, page_metrics)
        # Only 1 shared query, min is 2
        result = find_cross_link_gaps(client, "sc-domain:test.com", min_shared_queries=2)
        assert result == []

        # Lower min to 1
        result = find_cross_link_gaps(client, "sc-domain:test.com", min_shared_queries=1)
        assert len(result) == 2  # Bidirectional

    def test_opportunities_sorted_by_relevance_score(self):
        page_queries = {
            "https://test.com/a": [
                QueryData(query="q1", impressions=100),
                QueryData(query="q2", impressions=100),
                QueryData(query="q3", impressions=100),
            ],
            "https://test.com/b": [
                QueryData(query="q1", impressions=100),
                QueryData(query="q2", impressions=100),
                QueryData(query="q3", impressions=100),
            ],
            "https://test.com/c": [
                QueryData(query="q1", impressions=100),
                QueryData(query="q2", impressions=100),
            ],
        }
        page_metrics = {
            "https://test.com/a": PageMetrics(url="https://test.com/a", impressions=10000, position=5.0),
            "https://test.com/b": PageMetrics(url="https://test.com/b", impressions=1000, position=10.0),
            "https://test.com/c": PageMetrics(url="https://test.com/c", impressions=500, position=20.0),
        }

        client = self._make_mock_client(page_queries, page_metrics)
        result = find_cross_link_gaps(client, "sc-domain:test.com")

        # Should be sorted by score descending
        scores = [o.relevance_score for o in result]
        assert scores == sorted(scores, reverse=True)
