"""Main pipeline orchestrator."""

from __future__ import annotations

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
) -> LinkingResult:
    """Execute the full internal linking pipeline."""
    config = config or Config.load()
    model = model or config.default_model

    if not config.api_key:
        raise click.ClickException(
            "Anthropic API key not set. Run: seo-linker config --api-key YOUR_KEY\n"
            "Or set ANTHROPIC_API_KEY environment variable."
        )

    # Determine output path
    if output_path is None:
        suffix = input_path.suffix
        output_path = input_path.with_name(f"{input_path.stem}_linked{suffix}")

    ext = input_path.suffix.lower()

    # Step 1: Parse input content
    click.echo(f"Parsing {input_path.name}...")
    parser = detect_parser(input_path)
    sections = parser.parse(input_path)
    total_words = sum(len(s.text.split()) for s in sections)
    click.echo(f"  Found {len(sections)} section(s), ~{total_words} words")

    # Step 2: Fetch sitemaps (merge all)
    pages: list[TargetPage] = []
    for sitemap_url in sitemap_urls:
        click.echo(f"Fetching sitemap from {sitemap_url}...")
        sitemap_pages = fetch_sitemap(sitemap_url)
        click.echo(f"  Found {len(sitemap_pages)} URLs")
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
        click.echo(f"  Total unique URLs across {len(sitemap_urls)} sitemaps: {len(pages)}")

    if not pages:
        raise click.ClickException("No URLs found in sitemaps.")

    # Step 2b: Filter out product pages (.html) — keep categories, magazine, landing pages
    before_filter = len(pages)
    pages = [p for p in pages if not p.url.rstrip("/").endswith(".html")]
    if before_filter != len(pages):
        click.echo(f"  Filtered out {before_filter - len(pages)} product pages (.html), {len(pages)} remaining")

    # Step 3: Enrich pages with metadata
    click.echo("Enriching pages with title & meta description...")
    pages = enrich_pages(pages, config.cache_ttl_hours)
    enriched = sum(1 for p in pages if p.title)
    click.echo(f"  Enriched {enriched}/{len(pages)} pages")

    # Step 4: Pre-filter with embeddings
    click.echo(f"Pre-filtering to top {top_n} candidates via embeddings...")
    candidates = prefilter_pages(sections, pages, top_n, config.embedding_model)
    click.echo(f"  Selected {len(candidates)} candidate pages")

    # Step 5: Claude linking
    click.echo(f"Sending to Claude ({model}) for semantic link insertion...")
    result = link_content(
        sections, candidates, config.api_key, model, max_links, current_url
    )
    result.total_sitemap_pages = len(pages)
    result.candidate_pages_count = len(candidates)
    click.echo(f"  Inserted {len(result.insertions)} links")

    # Step 6: Write output
    writer = WRITER_MAP.get(ext)
    if writer is None:
        raise click.ClickException(f"No writer for format '{ext}'")

    writer.write(result, input_path, output_path)
    click.echo(f"Output written to {output_path}")

    # Print report
    if result.insertions:
        click.echo("\nLink report:")
        for ins in result.insertions:
            click.echo(f"  [{ins.anchor_text}] -> {ins.target_url}")
            if ins.reasoning:
                click.echo(f"    Reason: {ins.reasoning}")

    return result
