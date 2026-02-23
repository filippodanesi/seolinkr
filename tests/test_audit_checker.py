"""Tests for audit checker module."""

from __future__ import annotations

from pathlib import Path

import pytest

from seo_linker.audit.checker import audit_file, AuditResult


@pytest.fixture
def sample_article(tmp_path):
    """Create a sample markdown article with internal links."""
    content = """\
# Best Bras Guide

Looking for the perfect bra? Our guide covers everything from
[bügellose BHs](https://de.triumph.com/bhs/ohne-buegel) to supportive
[Sport-BHs](https://de.triumph.com/sport-bhs) and comfortable
[Baumwoll-BHs](https://de.triumph.com/bhs/baumwoll-bhs).

## Why Internal Links Matter

Internal links help readers discover more content on our site.
Check out our [Spitzen-BH Guide](https://de.triumph.com/magazin/spitzen-bh-guide)
for more inspiration.

## Top Picks

Our favorite pick is the [Triaction Zen](https://de.triumph.com/triaction-zen.html)
which offers great support for active lifestyles.
"""
    file_path = tmp_path / "test_article.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def article_with_issues(tmp_path):
    """Create an article with various audit issues."""
    content = """\
# [Bad Heading Link](https://de.triumph.com/bhs)

Click [hier](https://de.triumph.com/bhs) to see our collection.
Also check [hier](https://de.triumph.com/bhs/ohne-buegel) for more.

Visit [more](https://de.triumph.com/sport-bhs) to learn about sports bras.
And [link](https://de.triumph.com/bhs/baumwoll-bhs) for cotton bras.

Same URL twice: [BHs](https://de.triumph.com/bhs) and [Kollektion](https://de.triumph.com/bhs).
"""
    file_path = tmp_path / "bad_article.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


class TestAuditFile:
    def test_counts_link_types(self, sample_article):
        result = audit_file(sample_article, "de.triumph.com")
        assert result.total_links == 5
        assert result.category_links == 3  # ohne-buegel, sport-bhs, baumwoll-bhs
        assert result.magazine_links == 1  # magazin/spitzen-bh-guide
        assert result.product_links == 1  # .html product

    def test_detects_generic_anchors(self, article_with_issues):
        result = audit_file(article_with_issues, "de.triumph.com")
        generic_issues = [i for i in result.issues if i.type == "generic_anchor"]
        # "hier", "more", "link" are generic
        anchors_flagged = {i.anchor for i in generic_issues}
        assert "hier" in anchors_flagged
        assert "more" in anchors_flagged
        assert "link" in anchors_flagged

    def test_detects_heading_links(self, article_with_issues):
        result = audit_file(article_with_issues, "de.triumph.com")
        heading_issues = [i for i in result.issues if i.type == "heading_link"]
        assert len(heading_issues) == 1
        assert heading_issues[0].severity == "error"

    def test_detects_duplicate_urls(self, article_with_issues):
        result = audit_file(article_with_issues, "de.triumph.com")
        dup_issues = [i for i in result.issues if i.type == "duplicate_url"]
        assert len(dup_issues) >= 1
        assert any("https://de.triumph.com/bhs" in i.url for i in dup_issues)

    def test_warns_too_few_category_links(self, tmp_path):
        content = "No links here at all."
        file_path = tmp_path / "empty.md"
        file_path.write_text(content, encoding="utf-8")
        result = audit_file(file_path, "de.triumph.com")
        category_issues = [i for i in result.issues if i.type == "too_few_category_links"]
        assert len(category_issues) == 1

    def test_warns_missing_cross_links(self, tmp_path):
        content = "Some [BHs](https://de.triumph.com/bhs) content."
        file_path = tmp_path / "no_magazine.md"
        file_path.write_text(content, encoding="utf-8")
        result = audit_file(file_path, "de.triumph.com")
        cross_issues = [i for i in result.issues if i.type == "missing_cross_link"]
        assert len(cross_issues) == 1

    def test_auto_detects_domain(self, sample_article):
        # Don't pass domain — should auto-detect from links
        result = audit_file(sample_article)
        assert result.total_links == 5
        assert result.category_links >= 3

    def test_clean_article_minimal_issues(self, sample_article):
        result = audit_file(sample_article, "de.triumph.com")
        # This article meets minimum requirements
        error_issues = [i for i in result.issues if i.severity == "error"]
        assert len(error_issues) == 0

    def test_external_links_classified(self, tmp_path):
        content = "Check [Google](https://www.google.com) for more."
        file_path = tmp_path / "external.md"
        file_path.write_text(content, encoding="utf-8")
        result = audit_file(file_path, "de.triumph.com")
        assert result.external_links == 1
