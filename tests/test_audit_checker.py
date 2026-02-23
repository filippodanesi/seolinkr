"""Tests for audit checker module."""

from __future__ import annotations

from pathlib import Path

import pytest

from seo_linker.audit.checker import audit_file, AuditResult


@pytest.fixture
def sample_article(tmp_path):
    """Create a sample markdown article with internal links."""
    content = """\
# Best Running Shoes Guide

Looking for the perfect running shoe? Our guide covers everything from
[trail running shoes](https://www.example.com/shoes/trail) to supportive
[road running shoes](https://www.example.com/shoes/road) and comfortable
[walking shoes](https://www.example.com/shoes/walking).

## Why Internal Links Matter

Internal links help readers discover more content on our site.
Check out our [Marathon Training Guide](https://www.example.com/blog/marathon-training)
for more inspiration.

## Top Picks

Our favorite pick is the [UltraBoost Pro](https://www.example.com/ultraboost-pro.html)
which offers great support for active lifestyles.
"""
    file_path = tmp_path / "test_article.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def article_with_issues(tmp_path):
    """Create an article with various audit issues."""
    content = """\
# [Bad Heading Link](https://www.example.com/shoes)

Click [here](https://www.example.com/shoes) to see our collection.
Also check [here](https://www.example.com/shoes/trail) for more.

Visit [more](https://www.example.com/shoes/road) to learn about road shoes.
And [link](https://www.example.com/shoes/walking) for walking shoes.

Same URL twice: [Shoes](https://www.example.com/shoes) and [Collection](https://www.example.com/shoes).
"""
    file_path = tmp_path / "bad_article.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


class TestAuditFile:
    def test_counts_link_types(self, sample_article):
        result = audit_file(sample_article, "www.example.com")
        assert result.total_links == 5
        assert result.category_links == 4  # trail, road, walking, blog/marathon-training
        assert result.magazine_links == 0
        assert result.product_links == 1  # .html product

    def test_detects_generic_anchors(self, article_with_issues):
        result = audit_file(article_with_issues, "www.example.com")
        generic_issues = [i for i in result.issues if i.type == "generic_anchor"]
        # "here", "more", "link" are generic
        anchors_flagged = {i.anchor for i in generic_issues}
        assert "here" in anchors_flagged
        assert "more" in anchors_flagged
        assert "link" in anchors_flagged

    def test_detects_heading_links(self, article_with_issues):
        result = audit_file(article_with_issues, "www.example.com")
        heading_issues = [i for i in result.issues if i.type == "heading_link"]
        assert len(heading_issues) == 1
        assert heading_issues[0].severity == "error"

    def test_detects_duplicate_urls(self, article_with_issues):
        result = audit_file(article_with_issues, "www.example.com")
        dup_issues = [i for i in result.issues if i.type == "duplicate_url"]
        assert len(dup_issues) >= 1
        assert any("https://www.example.com/shoes" in i.url for i in dup_issues)

    def test_warns_too_few_category_links(self, tmp_path):
        content = "No links here at all."
        file_path = tmp_path / "empty.md"
        file_path.write_text(content, encoding="utf-8")
        result = audit_file(file_path, "www.example.com")
        category_issues = [i for i in result.issues if i.type == "too_few_category_links"]
        assert len(category_issues) == 1

    def test_warns_missing_cross_links(self, tmp_path):
        content = "Some [shoes](https://www.example.com/shoes) content."
        file_path = tmp_path / "no_magazine.md"
        file_path.write_text(content, encoding="utf-8")
        result = audit_file(file_path, "www.example.com")
        cross_issues = [i for i in result.issues if i.type == "missing_cross_link"]
        assert len(cross_issues) == 1

    def test_auto_detects_domain(self, sample_article):
        # Don't pass domain — should auto-detect from links
        result = audit_file(sample_article)
        assert result.total_links == 5
        assert result.category_links >= 3

    def test_clean_article_minimal_issues(self, sample_article):
        result = audit_file(sample_article, "www.example.com")
        # This article meets minimum requirements
        error_issues = [i for i in result.issues if i.severity == "error"]
        assert len(error_issues) == 0

    def test_external_links_classified(self, tmp_path):
        content = "Check [Google](https://www.google.com) for more."
        file_path = tmp_path / "external.md"
        file_path.write_text(content, encoding="utf-8")
        result = audit_file(file_path, "www.example.com")
        assert result.external_links == 1
