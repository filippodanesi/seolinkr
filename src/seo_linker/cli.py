# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Click CLI for the SEO internal linking tool."""

from __future__ import annotations

from pathlib import Path

import click

from seo_linker.config import Config
from seo_linker.models import TargetPage


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """SEO Internal Linking Tool — automated internal link insertion powered by AI."""
    pass


# ---------------------------------------------------------------------------
# Helper: resolve sitemaps
# ---------------------------------------------------------------------------

def _resolve_sitemaps(
    sitemaps: tuple[str, ...], all_sitemaps: bool, config: Config
) -> list[str]:
    """Resolve sitemap arguments: URLs pass through, names are looked up in config."""
    if all_sitemaps:
        if not config.sitemaps:
            raise click.ClickException("No saved sitemaps. Add with: seo-linker add-sitemap NAME URL")
        urls = list(config.sitemaps.values())
        names = list(config.sitemaps.keys())
        click.echo(f"Using all saved sitemaps: {', '.join(names)}")
        return urls

    urls: list[str] = []
    for s in sitemaps:
        if s.startswith("http://") or s.startswith("https://"):
            urls.append(s)
        elif s in config.sitemaps:
            click.echo(f"Resolved '{s}' -> {config.sitemaps[s]}")
            urls.append(config.sitemaps[s])
        else:
            raise click.ClickException(
                f"'{s}' is not a URL or a saved sitemap name.\n"
                f"Saved sitemaps: {', '.join(config.sitemaps.keys()) or '(none)'}"
            )
    return urls


# ---------------------------------------------------------------------------
# Helper: GSC client factory
# ---------------------------------------------------------------------------

def _get_gsc_client(config: Config):
    """Create GSC client from config, or return None if not configured."""
    if not config.gsc_service_account and not config.gsc_oauth_secrets:
        return None
    from seo_linker.gsc.client import GSCClient
    return GSCClient(
        service_account_path=config.gsc_service_account or None,
        oauth_client_secrets_path=config.gsc_oauth_secrets or None,
        cache_ttl_hours=config.gsc_cache_ttl,
    )


# ---------------------------------------------------------------------------
# Existing commands (backward-compatible)
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--sitemap", "-s", "sitemaps", multiple=True, help="Sitemap XML URL (repeatable, or use saved names)")
@click.option("--all-sitemaps", is_flag=True, default=False, help="Use all saved sitemaps")
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None, help="Output file path")
@click.option("--max-links", type=int, default=None, help="Maximum number of links to insert (default: 10)")
@click.option("--top-n", type=int, default=None, help="Number of candidate pages from embedding pre-filter (default: 25)")
@click.option("--model", default=None, help="Claude model to use")
@click.option("--current-url", default=None, help="URL of the current page (to prevent self-linking)")
@click.option("--gsc-site", default=None, help="GSC property (e.g. sc-domain:example.com) for enrichment")
@click.option("--rewrite/--no-rewrite", default=False, help="Rewrite/optimize content before linking")
@click.option("--content-type", type=click.Choice(["existing_article", "rough_draft"]), default="existing_article",
              help="Content type: existing_article (optimize) or rough_draft (expand)")
@click.option("--brand-guidelines", type=click.Path(exists=True, path_type=Path), default=None,
              help="Path to a markdown file with brand/tone-of-voice guidelines")
def process(
    file: Path,
    sitemaps: tuple[str, ...],
    all_sitemaps: bool,
    output: Path | None,
    max_links: int | None,
    top_n: int | None,
    model: str | None,
    current_url: str | None,
    gsc_site: str | None,
    rewrite: bool,
    content_type: str,
    brand_guidelines: Path | None,
):
    """Process a file and insert internal links.

    Use --sitemap with a URL or a saved name. Repeat for multiple sitemaps.
    Use --all-sitemaps to use every saved sitemap at once.
    """
    from seo_linker.pipeline import PipelineError, run_pipeline

    config = Config.load()

    # Resolve sitemap URLs
    sitemap_urls = _resolve_sitemaps(sitemaps, all_sitemaps, config)

    if not sitemap_urls:
        raise click.ClickException(
            "No sitemaps specified. Use --sitemap URL, --sitemap NAME, or --all-sitemaps.\n"
            "Save sitemaps with: seo-linker add-sitemap NAME URL"
        )

    # Load brand guidelines from file if provided
    bg_text = brand_guidelines.read_text(encoding="utf-8") if brand_guidelines else None

    try:
        run_pipeline(
            input_path=file,
            sitemap_urls=sitemap_urls,
            output_path=output,
            max_links=max_links or config.max_links,
            top_n=top_n or config.top_n,
            model=model,
            current_url=current_url,
            config=config,
            gsc_site=gsc_site,
            brand_guidelines=bg_text,
            enable_rewrite=rewrite,
            content_type=content_type,
        )
    except PipelineError as e:
        raise click.ClickException(str(e))


@cli.command()
@click.option("--api-key", default=None, help="Anthropic API key")
@click.option("--model", default=None, help="Default Claude model")
@click.option("--max-links", type=int, default=None, help="Default max links")
@click.option("--top-n", type=int, default=None, help="Default top-N candidates")
@click.option("--gsc-service-account", default=None, help="Path to GSC service account JSON")
@click.option("--gsc-oauth-secrets", default=None, help="Path to GSC OAuth client secrets JSON")
@click.option("--gsc-cache-ttl", type=int, default=None, help="GSC cache TTL in hours")
def config(api_key, model, max_links, top_n, gsc_service_account, gsc_oauth_secrets, gsc_cache_ttl):
    """Configure API key and default settings."""
    cfg = Config.load()
    if api_key:
        cfg.api_key = api_key
    if model:
        cfg.default_model = model
    if max_links is not None:
        cfg.max_links = max_links
    if top_n is not None:
        cfg.top_n = top_n
    if gsc_service_account:
        cfg.gsc_service_account = gsc_service_account
    if gsc_oauth_secrets:
        cfg.gsc_oauth_secrets = gsc_oauth_secrets
    if gsc_cache_ttl is not None:
        cfg.gsc_cache_ttl = gsc_cache_ttl
    cfg.save()
    click.echo("Configuration saved.")


@cli.command("add-sitemap")
@click.argument("name")
@click.argument("url")
def add_sitemap(name: str, url: str):
    """Save a sitemap URL with a short name for easy reuse.

    Example: seo-linker add-sitemap my-site https://www.example.com/sitemap_index.xml
    """
    cfg = Config.load()
    cfg.sitemaps[name] = url
    cfg.save()
    click.echo(f"Saved sitemap '{name}' -> {url}")
    click.echo(f"Use it with: seo-linker process file.md --sitemap {name}")


@cli.command("remove-sitemap")
@click.argument("name")
def remove_sitemap(name: str):
    """Remove a saved sitemap."""
    cfg = Config.load()
    if name not in cfg.sitemaps:
        raise click.ClickException(f"Sitemap '{name}' not found.")
    del cfg.sitemaps[name]
    cfg.save()
    click.echo(f"Removed sitemap '{name}'")


@cli.command("list-sitemaps")
def list_sitemaps():
    """List all saved sitemaps."""
    cfg = Config.load()
    if not cfg.sitemaps:
        click.echo("No saved sitemaps. Add with: seo-linker add-sitemap NAME URL")
        return
    for name, url in cfg.sitemaps.items():
        click.echo(f"  {name}: {url}")


@cli.command("analyze-sitemap")
@click.argument("url")
def analyze_sitemap(url: str):
    """Fetch and analyze a sitemap, showing page count and sample URLs."""
    from seo_linker.sitemap.fetcher import fetch_sitemap

    click.echo(f"Fetching sitemap from {url}...")
    pages = fetch_sitemap(url)
    click.echo(f"Found {len(pages)} URLs\n")

    if not pages:
        return

    show = min(20, len(pages))
    click.echo(f"First {show} URLs:")
    for page in pages[:show]:
        click.echo(f"  {page.url}")

    if len(pages) > show:
        click.echo(f"  ... and {len(pages) - show} more")


# ---------------------------------------------------------------------------
# NEW commands
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--gsc-site", required=True, help="GSC property (e.g. sc-domain:example.com)")
@click.option("--days", default=28, help="Lookback days (default: 28)")
@click.option("--min-impressions", default=100, help="Min impressions to include (default: 100)")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def opportunities(gsc_site: str, days: int, min_impressions: int, fmt: str):
    """Show pages that would benefit most from internal links."""
    cfg = Config.load()
    gsc = _get_gsc_client(cfg)
    if not gsc:
        raise click.ClickException("GSC not configured. Run: seo-linker config --gsc-service-account PATH")

    from seo_linker.gsc.opportunities import compute_opportunities
    opps = compute_opportunities(gsc, gsc_site, days, min_impressions)

    if fmt == "json":
        import json
        from dataclasses import asdict
        click.echo(json.dumps([asdict(o) for o in opps], indent=2))
    else:
        for priority in ["high", "quick_win", "medium"]:
            group = [o for o in opps if o.priority == priority]
            if not group:
                continue
            label = {"high": "High Priority", "quick_win": "Quick Wins", "medium": "Medium"}
            click.echo(f"\n{label[priority]}")
            for o in group[:15]:
                click.echo(f"  {o.url}")
                click.echo(f"    {o.impressions:,} imp | pos {o.position:.1f} | score {o.opportunity_score}")


@cli.command("cross-gaps")
@click.option("--gsc-site", required=True, help="GSC property")
@click.option("--url-pattern", default="/magazine/|/magazin/", help="URL regex for blog pages")
@click.option("--days", default=28)
@click.option("--min-shared", default=2, help="Min shared queries to flag (default: 2)")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def cross_gaps(gsc_site: str, url_pattern: str, days: int, min_shared: int, fmt: str):
    """Find cross-linking opportunities between blog articles."""
    cfg = Config.load()
    gsc = _get_gsc_client(cfg)
    if not gsc:
        raise click.ClickException("GSC not configured.")

    from seo_linker.gsc.cross_linker import find_cross_link_gaps
    gaps = find_cross_link_gaps(gsc, gsc_site, url_pattern, days, min_shared)

    if fmt == "json":
        import json
        from dataclasses import asdict
        click.echo(json.dumps([asdict(g) for g in gaps], indent=2))
    else:
        if not gaps:
            click.echo("No cross-linking gaps found.")
            return
        click.echo(f"\nCross-link opportunities ({len(gaps)} found):\n")
        for g in gaps[:20]:
            click.echo(f"  {g.suggestion}")
            click.echo(f"    Shared queries: {', '.join(g.shared_queries[:5])}")
            click.echo()


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--sitemap", "-s", "sitemaps", multiple=True)
@click.option("--all-sitemaps", is_flag=True, default=False)
@click.option("--gsc-site", default=None, help="GSC property for scoring enrichment")
@click.option("--top-n", type=int, default=None)
@click.option("--current-url", default=None, help="URL of current page (exclude from candidates)")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def candidates(file: Path, sitemaps, all_sitemaps, gsc_site, top_n, current_url, fmt):
    """Find and rank candidate pages for linking (without inserting links)."""
    cfg = Config.load()
    top_n = top_n or cfg.top_n

    sitemap_urls = _resolve_sitemaps(sitemaps, all_sitemaps, cfg)
    if not sitemap_urls:
        raise click.ClickException("No sitemaps specified.")

    from seo_linker.parsers.detector import detect_parser
    from seo_linker.sitemap.fetcher import fetch_sitemap
    from seo_linker.sitemap.enricher import enrich_pages
    from seo_linker.matching.prefilter import prefilter_pages

    parser = detect_parser(file)
    sections = parser.parse(file)

    pages = []
    for sitemap_url in sitemap_urls:
        pages.extend(fetch_sitemap(sitemap_url))

    # Deduplicate
    seen = set()
    pages = [p for p in pages if p.url not in seen and not seen.add(p.url)]

    # Filter product pages
    pages = [p for p in pages if not p.url.rstrip("/").endswith(".html")]

    # Enrich
    pages = enrich_pages(pages, cfg.cache_ttl_hours)

    # Prefilter with embeddings
    result_pages = prefilter_pages(sections, pages, top_n, cfg.embedding_model)

    # Enrich with GSC if available
    if gsc_site:
        gsc = _get_gsc_client(cfg)
        if gsc:
            result_pages = gsc.enrich_candidates(result_pages, gsc_site)

    # Filter out current URL
    if current_url:
        result_pages = [p for p in result_pages if p.url != current_url]

    if fmt == "json":
        import json
        output = [
            {
                "url": p.url,
                "title": p.title,
                "meta_description": p.meta_description,
                "impressions": p.impressions,
                "clicks": p.clicks,
                "avg_position": p.avg_position,
                "opportunity_score": p.opportunity_score,
            }
            for p in result_pages
        ]
        click.echo(json.dumps(output, indent=2))
    else:
        for i, p in enumerate(result_pages, 1):
            click.echo(f"{i}. {p.url}")
            if p.title:
                click.echo(f"   {p.title}")
            if p.impressions > 0:
                click.echo(f"   GSC: {p.impressions:,} imp | pos {p.avg_position:.1f}")


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--candidates", "candidates_file", type=click.Path(exists=True, path_type=Path), required=True,
              help="JSON file with candidate pages (output from 'candidates' command)")
@click.option("--max-links", type=int, default=None)
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None)
@click.option("--model", default=None)
@click.option("--current-url", default=None)
def link(file: Path, candidates_file: Path, max_links: int | None, output: Path | None, model: str | None, current_url: str | None):
    """Insert internal links using a pre-computed candidates list."""
    import json
    cfg = Config.load()
    model = model or cfg.default_model
    max_links = max_links or cfg.max_links

    if not cfg.api_key:
        raise click.ClickException("Anthropic API key not set.")

    if output is None:
        output = file.with_name(f"{file.stem}_linked{file.suffix}")

    # Parse input
    from seo_linker.parsers.detector import detect_parser
    parser = detect_parser(file)
    sections = parser.parse(file)

    # Load candidates from JSON
    candidates_data = json.loads(candidates_file.read_text())
    candidate_pages = [
        TargetPage(
            url=c["url"],
            title=c.get("title", ""),
            meta_description=c.get("meta_description", ""),
            impressions=c.get("impressions", 0),
            clicks=c.get("clicks", 0),
            avg_position=c.get("avg_position", 0.0),
        )
        for c in candidates_data
    ]

    # Claude linking
    from seo_linker.linking.claude_linker import link_content
    result = link_content(sections, candidate_pages, cfg.api_key, model, max_links, current_url)
    result.candidate_pages_count = len(candidate_pages)

    # Write output
    ext = file.suffix.lower()
    from seo_linker.writers.markdown_writer import MarkdownWriter
    from seo_linker.writers.docx_writer import DocxWriter
    from seo_linker.writers.xlsx_writer import XlsxWriter

    WRITERS = {".md": MarkdownWriter(), ".markdown": MarkdownWriter(), ".docx": DocxWriter(), ".xlsx": XlsxWriter()}
    writer = WRITERS.get(ext)
    if not writer:
        raise click.ClickException(f"No writer for '{ext}'")

    writer.write(result, file, output)
    click.echo(f"Output: {output}")

    # Print report as JSON (always, for Claude Code consumption)
    import json as json_mod
    report = [
        {"anchor_text": ins.anchor_text, "target_url": ins.target_url, "reasoning": ins.reasoning}
        for ins in result.insertions
    ]
    click.echo(json_mod.dumps(report, indent=2))


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--domain", default=None, help="Expected domain (e.g. www.example.com)")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def audit(file: Path, domain: str | None, fmt: str):
    """Audit an article's internal links against CLAUDE.md rules."""
    from seo_linker.audit.checker import audit_file
    from dataclasses import asdict

    result = audit_file(file, domain)

    if fmt == "json":
        import json
        click.echo(json.dumps(asdict(result), indent=2))
    else:
        click.echo(f"\nAudit: {result.file}")
        click.echo(f"  Total links: {result.total_links}")
        click.echo(f"  Category: {result.category_links} | Magazine: {result.magazine_links} | Product: {result.product_links}")
        if result.issues:
            click.echo(f"\n  Issues ({len(result.issues)}):")
            for issue in result.issues:
                icon = {"error": "X", "warning": "!", "info": "i"}.get(issue.severity, "-")
                click.echo(f"    [{icon}] {issue.message}")
        else:
            click.echo("\n  No issues found")


@cli.command("batch-process")
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--pattern", "-p", default="*.md", help="Glob pattern for input files (default: *.md)")
@click.option("--files", "-f", "explicit_files", multiple=True, type=click.Path(exists=True, path_type=Path),
              help="Explicit file paths (repeatable, overrides --pattern)")
@click.option("--sitemap", "-s", "sitemaps", multiple=True, help="Sitemap URL or saved name (repeatable)")
@click.option("--all-sitemaps", is_flag=True, default=False)
@click.option("--max-links", type=int, default=None)
@click.option("--top-n", type=int, default=None)
@click.option("--model", default=None)
@click.option("--gsc-site", default=None)
@click.option("--rewrite/--no-rewrite", default=False)
@click.option("--content-type", type=click.Choice(["existing_article", "rough_draft"]), default="existing_article")
@click.option("--brand-guidelines", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def batch_process(
    directory: Path,
    pattern: str,
    explicit_files: tuple[Path, ...],
    sitemaps: tuple[str, ...],
    all_sitemaps: bool,
    max_links: int | None,
    top_n: int | None,
    model: str | None,
    gsc_site: str | None,
    rewrite: bool,
    content_type: str,
    brand_guidelines: Path | None,
    fmt: str,
):
    """Batch process a directory of articles with shared sitemap fetch."""
    from seo_linker.batch import run_batch_pipeline

    config = Config.load()
    sitemap_urls = _resolve_sitemaps(sitemaps, all_sitemaps, config)
    if not sitemap_urls:
        raise click.ClickException("No sitemaps specified.")

    # Resolve file list
    if explicit_files:
        input_paths = list(explicit_files)
    else:
        input_paths = sorted(
            p for p in directory.glob(pattern)
            if "_linked" not in p.stem
        )

    if not input_paths:
        raise click.ClickException(f"No files matching '{pattern}' in {directory}")

    click.echo(f"Found {len(input_paths)} files to process")

    bg_text = brand_guidelines.read_text(encoding="utf-8") if brand_guidelines else None

    try:
        result = run_batch_pipeline(
            input_paths=input_paths,
            sitemap_urls=sitemap_urls,
            max_links=max_links or config.max_links,
            top_n=top_n or config.top_n,
            model=model,
            config=config,
            gsc_site=gsc_site,
            brand_guidelines=bg_text,
            enable_rewrite=rewrite,
            content_type=content_type,
        )
    except Exception as e:
        raise click.ClickException(str(e))

    if fmt == "json":
        import json
        from dataclasses import asdict
        click.echo(json.dumps(asdict(result), indent=2))
    else:
        click.echo(f"\nSummary: {result.succeeded}/{result.total_files} succeeded, "
                    f"{result.total_links_inserted} links inserted")


@cli.command("batch-audit")
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--pattern", "-p", default="*_linked.md", help="Glob pattern (default: *_linked.md)")
@click.option("--files", "-f", "explicit_files", multiple=True, type=click.Path(exists=True, path_type=Path))
@click.option("--domain", default=None, help="Expected site domain")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def batch_audit(
    directory: Path,
    pattern: str,
    explicit_files: tuple[Path, ...],
    domain: str | None,
    fmt: str,
):
    """Batch audit a directory of linked articles."""
    from seo_linker.batch import run_batch_audit

    if explicit_files:
        input_paths = list(explicit_files)
    else:
        input_paths = sorted(directory.glob(pattern))

    if not input_paths:
        raise click.ClickException(f"No files matching '{pattern}' in {directory}")

    click.echo(f"Auditing {len(input_paths)} files...")

    result = run_batch_audit(input_paths, site_domain=domain)

    if fmt == "json":
        import json
        from dataclasses import asdict
        click.echo(json.dumps(asdict(result), indent=2))
    else:
        click.echo(f"\nSummary: {result.files_passing} passing, "
                    f"{result.files_with_errors} with errors, "
                    f"{result.total_issues} total issues")


@cli.command("gsc-clear-cache")
@click.option("--site", default=None, help="Clear cache for specific GSC site only")
def gsc_clear_cache(site: str | None):
    """Clear cached GSC data."""
    from seo_linker.gsc.cache import GSCCache
    cache = GSCCache()
    count = cache.clear(site)
    click.echo(f"Cleared {count} cached file(s)")


if __name__ == "__main__":
    cli()
