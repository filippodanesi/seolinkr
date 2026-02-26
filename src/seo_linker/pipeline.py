# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Main pipeline orchestrator."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import click

from seo_linker.config import Config
from seo_linker.linking.claude_linker import link_content
from seo_linker.matching.prefilter import prefilter_pages
from seo_linker.models import LinkingResult, TargetPage
from seo_linker.parsers.detector import detect_parser
from seo_linker.sitemap.enricher import enrich_pages
from seo_linker.sitemap.fetcher import fetch_sitemap
from seo_linker.writers.docx_writer import DocxWriter
from seo_linker.writers.markdown_writer import MarkdownWriter
from seo_linker.writers.xlsx_writer import XlsxWriter


class PipelineError(Exception):
    """Raised when the pipeline encounters a non-recoverable error."""

WRITER_MAP = {
    ".md": MarkdownWriter(),
    ".markdown": MarkdownWriter(),
    ".docx": DocxWriter(),
    ".xlsx": XlsxWriter(),
}


def run_pipeline(
    input_path: Path,
    sitemap_urls: list[str],
    output_path: Path | None = None,
    max_links: int = 10,
    top_n: int = 25,
    model: str | None = None,
    current_url: str | None = None,
    config: Config | None = None,
    gsc_site: str | None = None,
    log_fn: Callable[[str], None] | None = None,
    brand_guidelines: str | None = None,
    gsc_client: object | None = None,
    enable_rewrite: bool = False,
    content_type: str = "existing_article",
    rewrite_instructions: str | None = None,
    prefetched_pages: list[TargetPage] | None = None,
    generate_html: bool = False,
    brand_name: str = "Triumph®",
) -> LinkingResult:
    """Execute the full internal linking pipeline."""
    log_fn = log_fn or click.echo
    config = config or Config.load()
    model = model or config.default_model

    if not config.api_key:
        raise PipelineError(
            "Anthropic API key not set. Run: seo-linker config --api-key YOUR_KEY\n"
            "Or set ANTHROPIC_API_KEY environment variable."
        )

    # Determine output path
    if output_path is None:
        suffix = input_path.suffix
        output_path = input_path.with_name(f"{input_path.stem}_linked{suffix}")

    ext = input_path.suffix.lower()

    # Step 1: Parse input content
    log_fn(f"Parsing {input_path.name}...")
    parser = detect_parser(input_path)
    sections = parser.parse(input_path)
    total_words = sum(len(s.text.split()) for s in sections)
    log_fn(f"  Found {len(sections)} section(s), ~{total_words} words")

    # Step 1b: Rewrite/optimize content (optional — before sitemap fetch)
    rewritten_text = ""
    if enable_rewrite:
        log_fn(f"Rewriting content ({content_type})...")
        from seo_linker.rewriting.claude_rewriter import rewrite_content

        sections = rewrite_content(
            sections,
            api_key=config.api_key,
            model=model,
            brand_guidelines=brand_guidelines,
            content_type=content_type,
            custom_instructions=rewrite_instructions,
            log_fn=log_fn,
        )
        rewritten_text = "\n\n".join(s.text for s in sections)
        rewritten_words = len(rewritten_text.split())
        log_fn(f"  Rewrite complete: ~{rewritten_words} words")

    if prefetched_pages is not None:
        # Bulk mode: pages already fetched, filtered, and enriched
        pages = prefetched_pages
        log_fn(f"Using {len(pages)} pre-fetched pages (bulk mode)")
    else:
        # Step 2: Fetch sitemaps (merge all)
        pages: list[TargetPage] = []
        for sitemap_url in sitemap_urls:
            log_fn(f"Fetching sitemap from {sitemap_url}...")
            sitemap_pages = fetch_sitemap(sitemap_url)
            log_fn(f"  Found {len(sitemap_pages)} URLs")
            pages.extend(sitemap_pages)

        # Deduplicate by URL
        seen: set[str] = set()
        unique_pages: list[TargetPage] = []
        for p in pages:
            if p.url not in seen:
                seen.add(p.url)
                unique_pages.append(p)
        pages = unique_pages

        if len(sitemap_urls) > 1:
            log_fn(f"  Total unique URLs across {len(sitemap_urls)} sitemaps: {len(pages)}")

        if not pages:
            raise PipelineError("No URLs found in sitemaps.")

        # Step 2b: Filter out product pages (.html) — keep categories, magazine, landing pages
        before_filter = len(pages)
        pages = [p for p in pages if not p.url.rstrip("/").endswith(".html")]
        if before_filter != len(pages):
            log_fn(f"  Filtered out {before_filter - len(pages)} product pages (.html), {len(pages)} remaining")

        # Step 3: Enrich pages with metadata
        log_fn("Enriching pages with title & meta description...")
        pages = enrich_pages(pages, config.cache_ttl_hours)
        enriched = sum(1 for p in pages if p.title)
        log_fn(f"  Enriched {enriched}/{len(pages)} pages")

    # GSC: enrich ALL pages before prefilter (multi-signal scoring uses GSC data)
    if gsc_site:
        if gsc_client is None:
            from seo_linker.gsc.client import GSCClient
            gsc_client = GSCClient(
                service_account_path=config.gsc_service_account or None,
                oauth_client_secrets_path=config.gsc_oauth_secrets or None,
                cache_ttl_hours=config.gsc_cache_ttl,
            )
        pages = gsc_client.enrich_candidates(pages, gsc_site)
        enriched_gsc = sum(1 for p in pages if p.impressions > 0)
        log_fn(f"  GSC data: {enriched_gsc}/{len(pages)} pages with metrics")

    # Pre-filter with multi-signal scoring (embedding + URL taxonomy + GSC + headings)
    log_fn(f"Pre-filtering to top {top_n} candidates via multi-signal scoring...")
    candidates = prefilter_pages(sections, pages, top_n, config.embedding_model)
    log_fn(f"  Selected {len(candidates)} candidate pages")

    # Step 5: Claude linking
    log_fn(f"Sending to Claude ({model}) for semantic link insertion...")
    result = link_content(
        sections, candidates, config.api_key, model, max_links, current_url,
        brand_guidelines=brand_guidelines,
    )
    result.total_sitemap_pages = len(pages)
    result.candidate_pages_count = len(candidates)
    result.rewritten_text = rewritten_text
    log_fn(f"  Inserted {len(result.insertions)} links")

    # Step 6: Write output
    writer = WRITER_MAP.get(ext)
    if writer is None:
        raise PipelineError(f"No writer for format '{ext}'")

    writer.write(result, input_path, output_path)
    log_fn(f"Output written to {output_path}")

    # Step 7: Generate SEO title & meta description (optional)
    if generate_html:
        from seo_linker.html.generator import generate_seo_metadata

        meta = generate_seo_metadata(
            linked_text=result.linked_text,
            api_key=config.api_key,
            model=model,
            brand_name=brand_name,
            log_fn=log_fn,
        )
        result.seo_title = meta["title"]
        result.seo_meta_description = meta["meta_description"]

        # Re-write output with metadata embedded (writer reads seo_title/seo_meta_description)
        writer.write(result, input_path, output_path)
        log_fn(f"SEO metadata embedded in {output_path.name}")

    # Print report
    if result.insertions:
        log_fn("\nLink report:")
        for ins in result.insertions:
            log_fn(f"  [{ins.anchor_text}] -> {ins.target_url}")
            if ins.reasoning:
                log_fn(f"    Reason: {ins.reasoning}")

    return result
