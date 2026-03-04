# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Tests for batch processing and auditing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from seo_linker.batch import run_batch_audit, run_batch_pipeline
from seo_linker.models import BatchAuditResult, BatchResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


ARTICLE_MD = """\
# Test Article

This is a test article about running shoes.

Check out our [running shoes collection](https://www.example.com/shoes/running) for more.

We also have [trail shoes](https://www.example.com/shoes/trail) and
[hiking boots](https://www.example.com/shoes/hiking) available.

Read our [guide to choosing shoes](https://www.example.com/magazine/shoe-guide) for tips.
"""


@pytest.fixture
def batch_dir(tmp_path: Path) -> Path:
    """Create a temp directory with multiple markdown files."""
    for i in range(3):
        (tmp_path / f"article_{i}.md").write_text(ARTICLE_MD, encoding="utf-8")
    return tmp_path


@pytest.fixture
def linked_dir(tmp_path: Path) -> Path:
    """Create a temp directory with _linked files for auditing."""
    for i in range(3):
        (tmp_path / f"article_{i}_linked.md").write_text(ARTICLE_MD, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Batch audit tests
# ---------------------------------------------------------------------------


class TestRunBatchAudit:
    def test_audits_all_files(self, linked_dir: Path):
        result = run_batch_audit(
            input_paths=sorted(linked_dir.glob("*_linked.md")),
            site_domain="www.example.com",
            log_fn=lambda _: None,
        )
        assert isinstance(result, BatchAuditResult)
        assert result.total_files == 3
        assert result.succeeded == 3
        assert result.failed == 0

    def test_aggregates_issues(self, linked_dir: Path):
        result = run_batch_audit(
            input_paths=sorted(linked_dir.glob("*_linked.md")),
            site_domain="www.example.com",
            log_fn=lambda _: None,
        )
        # Each file has the same content with issues; total = per_file * 3
        assert len(result.file_results) == 3
        per_file_issues = result.file_results[0].result.issues  # type: ignore[union-attr]
        assert result.total_issues == len(per_file_issues) * 3
        for fr in result.file_results:
            assert fr.status == "success"
            assert fr.result is not None

    def test_handles_missing_file(self, tmp_path: Path):
        missing = tmp_path / "nonexistent.md"
        result = run_batch_audit(
            input_paths=[missing],
            log_fn=lambda _: None,
        )
        assert result.failed == 1
        assert result.succeeded == 0
        assert result.file_results[0].status == "error"

    def test_files_passing_count(self, linked_dir: Path):
        result = run_batch_audit(
            input_paths=sorted(linked_dir.glob("*_linked.md")),
            site_domain="www.example.com",
            log_fn=lambda _: None,
        )
        # No heading links → no error-severity issues → all files pass
        assert result.files_passing == 3
        assert result.files_with_errors == 0

    def test_empty_input_list(self):
        result = run_batch_audit(
            input_paths=[],
            log_fn=lambda _: None,
        )
        assert result.total_files == 0
        assert result.succeeded == 0


# ---------------------------------------------------------------------------
# Batch pipeline tests
# ---------------------------------------------------------------------------


class TestRunBatchPipeline:
    @patch("seo_linker.pipeline.run_pipeline")
    @patch("seo_linker.sitemap.enricher.enrich_pages")
    @patch("seo_linker.sitemap.fetcher.fetch_sitemap")
    def test_calls_pipeline_per_file(
        self, mock_fetch, mock_enrich, mock_pipeline, batch_dir: Path
    ):
        from seo_linker.models import LinkingResult

        mock_fetch.return_value = []
        mock_enrich.return_value = []
        mock_pipeline.return_value = LinkingResult(
            original_text="", linked_text="", insertions=[]
        )

        input_paths = sorted(batch_dir.glob("*.md"))
        result = run_batch_pipeline(
            input_paths=input_paths,
            sitemap_urls=["https://example.com/sitemap.xml"],
            log_fn=lambda _: None,
        )

        assert isinstance(result, BatchResult)
        assert result.total_files == 3
        assert result.succeeded == 3
        assert mock_pipeline.call_count == 3

    @patch("seo_linker.pipeline.run_pipeline")
    @patch("seo_linker.sitemap.enricher.enrich_pages")
    @patch("seo_linker.sitemap.fetcher.fetch_sitemap")
    def test_fetches_sitemap_once(
        self, mock_fetch, mock_enrich, mock_pipeline, batch_dir: Path
    ):
        from seo_linker.models import LinkingResult

        mock_fetch.return_value = []
        mock_enrich.return_value = []
        mock_pipeline.return_value = LinkingResult(
            original_text="", linked_text="", insertions=[]
        )

        run_batch_pipeline(
            input_paths=sorted(batch_dir.glob("*.md")),
            sitemap_urls=["https://example.com/sitemap.xml"],
            log_fn=lambda _: None,
        )

        # Sitemap fetched once, not per-file
        assert mock_fetch.call_count == 1

    @patch("seo_linker.pipeline.run_pipeline")
    @patch("seo_linker.sitemap.enricher.enrich_pages")
    @patch("seo_linker.sitemap.fetcher.fetch_sitemap")
    def test_passes_prefetched_pages(
        self, mock_fetch, mock_enrich, mock_pipeline, batch_dir: Path
    ):
        from seo_linker.models import LinkingResult, TargetPage

        pages = [TargetPage(url="https://example.com/page1")]
        mock_fetch.return_value = pages
        mock_enrich.return_value = pages
        mock_pipeline.return_value = LinkingResult(
            original_text="", linked_text="", insertions=[]
        )

        run_batch_pipeline(
            input_paths=sorted(batch_dir.glob("*.md")),
            sitemap_urls=["https://example.com/sitemap.xml"],
            log_fn=lambda _: None,
        )

        # Every pipeline call gets prefetched_pages
        for call in mock_pipeline.call_args_list:
            assert call.kwargs["prefetched_pages"] == pages

    @patch("seo_linker.pipeline.run_pipeline")
    @patch("seo_linker.sitemap.enricher.enrich_pages")
    @patch("seo_linker.sitemap.fetcher.fetch_sitemap")
    def test_continues_on_file_error(
        self, mock_fetch, mock_enrich, mock_pipeline, batch_dir: Path
    ):
        from seo_linker.models import LinkingResult

        mock_fetch.return_value = []
        mock_enrich.return_value = []
        # First file errors, second and third succeed
        mock_pipeline.side_effect = [
            Exception("test error"),
            LinkingResult(original_text="", linked_text="", insertions=[]),
            LinkingResult(original_text="", linked_text="", insertions=[]),
        ]

        result = run_batch_pipeline(
            input_paths=sorted(batch_dir.glob("*.md")),
            sitemap_urls=["https://example.com/sitemap.xml"],
            log_fn=lambda _: None,
        )

        assert result.succeeded == 2
        assert result.failed == 1
        assert result.file_results[0].status == "error"
        assert result.file_results[0].error == "test error"

    @patch("seo_linker.pipeline.run_pipeline")
    @patch("seo_linker.sitemap.enricher.enrich_pages")
    @patch("seo_linker.sitemap.fetcher.fetch_sitemap")
    def test_callbacks_invoked(
        self, mock_fetch, mock_enrich, mock_pipeline, batch_dir: Path
    ):
        from seo_linker.models import LinkingResult

        mock_fetch.return_value = []
        mock_enrich.return_value = []
        mock_pipeline.return_value = LinkingResult(
            original_text="", linked_text="", insertions=[]
        )

        start_calls: list[tuple] = []
        done_calls: list[tuple] = []

        result = run_batch_pipeline(
            input_paths=sorted(batch_dir.glob("*.md")),
            sitemap_urls=["https://example.com/sitemap.xml"],
            log_fn=lambda _: None,
            file_start_fn=lambda i, f, t: start_calls.append((i, f, t)),
            file_done_fn=lambda i, f, r: done_calls.append((i, f)),
        )

        assert len(start_calls) == 3
        assert len(done_calls) == 3
