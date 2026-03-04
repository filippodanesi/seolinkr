# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Batch processing orchestrator — shared sitemap fetch, per-file pipeline."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from seo_linker.config import Config
from seo_linker.models import (
    BatchAuditResult,
    BatchResult,
    FileAuditResult,
    FileResult,
    TargetPage,
)


def run_batch_pipeline(
    input_paths: list[Path],
    sitemap_urls: list[str],
    *,
    output_dir: Path | None = None,
    max_links: int = 10,
    top_n: int = 25,
    model: str | None = None,
    config: Config | None = None,
    gsc_site: str | None = None,
    brand_guidelines: str | None = None,
    enable_rewrite: bool = False,
    content_type: str = "existing_article",
    generate_html: bool = False,
    brand_name: str = "Triumph\u00ae",
    log_fn: Callable[[str], None] | None = None,
    file_start_fn: Callable[[int, str, int], None] | None = None,
    file_log_fn: Callable[[int, str, str], None] | None = None,
    file_done_fn: Callable[[int, str, object], None] | None = None,
    file_error_fn: Callable[[int, str, str], None] | None = None,
) -> BatchResult:
    """Process multiple files with shared sitemap fetch.

    Phase 1: Fetch and enrich sitemaps once.
    Phase 2: Run pipeline per file using prefetched_pages.
    """
    import click

    from seo_linker.pipeline import run_pipeline
    from seo_linker.sitemap.enricher import enrich_pages
    from seo_linker.sitemap.fetcher import fetch_sitemap

    log_fn = log_fn or click.echo
    config = config or Config.load()

    # Phase 1: Shared sitemap fetch + enrichment
    log_fn(f"Batch: fetching sitemaps for {len(input_paths)} files...")
    pages: list[TargetPage] = []
    for sitemap_url in sitemap_urls:
        log_fn(f"  Fetching {sitemap_url}...")
        sitemap_pages = fetch_sitemap(sitemap_url)
        log_fn(f"    Found {len(sitemap_pages)} URLs")
        pages.extend(sitemap_pages)

    # Deduplicate
    seen: set[str] = set()
    unique: list[TargetPage] = []
    for p in pages:
        if p.url not in seen:
            seen.add(p.url)
            unique.append(p)
    pages = unique
    log_fn(f"  Total unique URLs: {len(pages)}")

    # Filter product pages (.html)
    before = len(pages)
    pages = [p for p in pages if not p.url.rstrip("/").endswith(".html")]
    if before != len(pages):
        log_fn(f"  Filtered {before - len(pages)} product pages, {len(pages)} remaining")

    # Enrich
    log_fn("  Enriching pages with metadata...")
    pages = enrich_pages(pages, config.cache_ttl_hours)
    enriched = sum(1 for p in pages if p.title)
    log_fn(f"  Enriched {enriched}/{len(pages)} pages")

    # GSC enrichment
    if gsc_site:
        from seo_linker.gsc.client import GSCClient

        gsc_client = GSCClient(
            service_account_path=config.gsc_service_account or None,
            oauth_client_secrets_path=config.gsc_oauth_secrets or None,
            cache_ttl_hours=config.gsc_cache_ttl,
        )
        pages = gsc_client.enrich_candidates(pages, gsc_site)
        log_fn(f"  GSC: {sum(1 for p in pages if p.impressions > 0)}/{len(pages)} with metrics")

    log_fn(f"Shared setup complete. Processing {len(input_paths)} files...\n")

    # Phase 2: Per-file processing
    file_results: list[FileResult] = []
    succeeded = 0
    failed = 0
    total_links = 0

    for i, input_path in enumerate(input_paths):
        filename = input_path.name

        if file_start_fn:
            file_start_fn(i, filename, len(input_paths))

        # Per-file log_fn that routes to both shared log and file-specific log
        def make_file_log(idx: int, fname: str) -> Callable[[str], None]:
            def _log(msg: str) -> None:
                if file_log_fn:
                    file_log_fn(idx, fname, msg)
            return _log

        per_file_log = make_file_log(i, filename)

        try:
            # Determine output path
            if output_dir:
                out = output_dir / f"{input_path.stem}_linked{input_path.suffix}"
            else:
                out = input_path.with_name(f"{input_path.stem}_linked{input_path.suffix}")

            result = run_pipeline(
                input_path=input_path,
                sitemap_urls=sitemap_urls,
                output_path=out,
                max_links=max_links,
                top_n=top_n,
                model=model,
                config=config,
                gsc_site=gsc_site,
                log_fn=per_file_log,
                brand_guidelines=brand_guidelines,
                enable_rewrite=enable_rewrite,
                content_type=content_type,
                prefetched_pages=pages,
                generate_html=generate_html,
                brand_name=brand_name,
            )
            file_results.append(FileResult(
                filename=filename,
                status="success",
                result=result,
            ))
            total_links += len(result.insertions)
            succeeded += 1
            log_fn(f"  [{i + 1}/{len(input_paths)}] {filename}: {len(result.insertions)} links inserted")

            if file_done_fn:
                file_done_fn(i, filename, result)

        except Exception as e:
            file_results.append(FileResult(
                filename=filename,
                status="error",
                error=str(e),
            ))
            failed += 1
            log_fn(f"  [{i + 1}/{len(input_paths)}] {filename}: ERROR - {e}")

            if file_error_fn:
                file_error_fn(i, filename, str(e))

    log_fn(f"\nBatch complete: {succeeded} succeeded, {failed} failed, {total_links} total links")

    return BatchResult(
        total_files=len(input_paths),
        succeeded=succeeded,
        failed=failed,
        file_results=file_results,
        total_links_inserted=total_links,
        total_sitemap_pages=len(pages),
    )


def run_batch_audit(
    input_paths: list[Path],
    site_domain: str | None = None,
    log_fn: Callable[[str], None] | None = None,
) -> BatchAuditResult:
    """Audit multiple files, aggregating results."""
    import click

    from seo_linker.audit.checker import audit_file

    log_fn = log_fn or click.echo

    file_results: list[FileAuditResult] = []
    succeeded = 0
    failed = 0
    total_issues = 0
    files_passing = 0

    for i, input_path in enumerate(input_paths):
        filename = input_path.name
        try:
            result = audit_file(input_path, site_domain)
            has_errors = any(iss.severity == "error" for iss in result.issues)
            file_results.append(FileAuditResult(
                filename=filename,
                status="success",
                result=result,
            ))
            succeeded += 1
            total_issues += len(result.issues)
            if not has_errors:
                files_passing += 1
            log_fn(f"  [{i + 1}/{len(input_paths)}] {filename}: {len(result.issues)} issues")
        except Exception as e:
            file_results.append(FileAuditResult(
                filename=filename,
                status="error",
                error=str(e),
            ))
            failed += 1
            log_fn(f"  [{i + 1}/{len(input_paths)}] {filename}: ERROR - {e}")

    files_with_errors = sum(
        1
        for fr in file_results
        if fr.status == "success"
        and fr.result is not None
        and any(iss.severity == "error" for iss in fr.result.issues)  # type: ignore[union-attr]
    )

    log_fn(f"\nBatch audit: {succeeded} audited, {failed} failed, {total_issues} total issues")

    return BatchAuditResult(
        total_files=len(input_paths),
        succeeded=succeeded,
        failed=failed,
        file_results=file_results,
        total_issues=total_issues,
        files_with_errors=files_with_errors,
        files_passing=files_passing,
    )
