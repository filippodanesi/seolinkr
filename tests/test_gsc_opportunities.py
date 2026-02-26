# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Tests for GSC opportunity scoring."""

from __future__ import annotations

import pytest

from seo_linker.gsc.client import PageMetrics
from seo_linker.gsc.opportunities import score_opportunity, Opportunity


class TestScoreOpportunity:
    def test_high_priority_page(self):
        """High impressions + position 4-15 should be high priority."""
        m = PageMetrics(url="https://example.com/bhs", impressions=10000, clicks=300, ctr=0.03, position=8.0)
        score, priority, reason = score_opportunity(m)
        assert priority == "high"
        assert score > 0.5
        assert "High impressions" in reason

    def test_quick_win_page(self):
        """High impressions + position < 4 should be quick_win."""
        m = PageMetrics(url="https://example.com/bhs", impressions=10000, clicks=1000, ctr=0.1, position=2.5)
        score, priority, reason = score_opportunity(m)
        assert priority == "quick_win"
        assert "Already near top" in reason

    def test_medium_priority_page(self):
        """Moderate impressions + position 5-20 should be medium."""
        m = PageMetrics(url="https://example.com/bhs", impressions=2000, clicks=50, ctr=0.025, position=12.0)
        score, priority, reason = score_opportunity(m)
        assert priority == "medium"
        assert "Moderate volume" in reason

    def test_low_priority_page(self):
        """Low impressions should be low priority."""
        m = PageMetrics(url="https://example.com/bhs", impressions=50, clicks=2, ctr=0.04, position=25.0)
        score, priority, reason = score_opportunity(m)
        assert priority == "low"

    def test_score_is_bounded(self):
        """Score should be between 0 and 1."""
        test_cases = [
            PageMetrics(url="a", impressions=100000, clicks=5000, position=8.0),
            PageMetrics(url="b", impressions=1, clicks=0, position=100.0),
            PageMetrics(url="c", impressions=5000, clicks=100, position=1.0),
        ]
        for m in test_cases:
            score, _, _ = score_opportunity(m)
            assert 0 <= score <= 1, f"Score {score} out of bounds for {m}"

    def test_position_8_is_optimal(self):
        """Position 8 should produce highest position factor for same impressions."""
        base_imp = 10000
        scores = {}
        for pos in [4, 8, 12, 15, 20]:
            m = PageMetrics(url="a", impressions=base_imp, position=pos)
            score, _, _ = score_opportunity(m)
            scores[pos] = score
        # Position 8 should have highest score
        assert scores[8] >= max(scores[4], scores[12], scores[15], scores[20])

    def test_higher_impressions_higher_score(self):
        """More impressions should produce higher scores at same position."""
        low = PageMetrics(url="a", impressions=1000, position=8.0)
        high = PageMetrics(url="b", impressions=50000, position=8.0)
        score_low, _, _ = score_opportunity(low)
        score_high, _, _ = score_opportunity(high)
        assert score_high > score_low
