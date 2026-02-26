# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Tests for model changes — opportunity_score property."""

from __future__ import annotations

import pytest

from seo_linker.models import TargetPage


class TestOpportunityScore:
    def test_zero_impressions_returns_zero(self):
        page = TargetPage(url="https://example.com/page")
        assert page.opportunity_score == 0.0

    def test_high_impressions_good_position(self):
        page = TargetPage(url="https://example.com/page", impressions=10000, avg_position=8.0)
        score = page.opportunity_score
        assert score > 0.5
        assert score <= 1.0

    def test_position_1_lower_than_position_8(self):
        """Position 1 (already strong) should score lower than position 8."""
        page_pos1 = TargetPage(url="a", impressions=10000, avg_position=1.0)
        page_pos8 = TargetPage(url="b", impressions=10000, avg_position=8.0)
        assert page_pos8.opportunity_score > page_pos1.opportunity_score

    def test_very_high_position_low_score(self):
        """Position 50+ should have very low score."""
        page = TargetPage(url="a", impressions=10000, avg_position=50.0)
        assert page.opportunity_score < 0.1

    def test_score_is_rounded(self):
        page = TargetPage(url="a", impressions=5000, avg_position=8.0)
        score = page.opportunity_score
        # Should be rounded to 3 decimal places
        assert score == round(score, 3)

    def test_display_text_includes_gsc_data(self):
        page = TargetPage(
            url="https://example.com/page",
            title="Test Page",
            impressions=5000,
            avg_position=7.5,
        )
        text = page.display_text
        assert "GSC" in text
        assert "5000" in text
        assert "7.5" in text

    def test_display_text_no_gsc_when_zero_impressions(self):
        page = TargetPage(url="https://example.com/page", title="Test Page")
        text = page.display_text
        assert "GSC" not in text

    def test_default_gsc_fields(self):
        page = TargetPage(url="https://example.com/page")
        assert page.impressions == 0
        assert page.clicks == 0
        assert page.avg_position == 0.0
        assert page.top_queries == []
