"""Click CLI for the SEO internal linking tool."""

from __future__ import annotations

from pathlib import Path

import click

from seo_linker.config import Config


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """SEO Internal Linking Tool — automated internal link insertion powered by AI."""
    pass


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--sitemap", "-s", "sitemaps", multiple=True, help="Sitemap XML URL (repeatable, or use saved names)")
@click.option("--all-sitemaps", is_flag=True, default=False, help="Use all saved sitemaps")
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None, help="Output file path")
@click.option("--max-links", type=int, default=None, help="Maximum number of links to insert (default: 10)")
@click.option("--top-n", type=int, default=None, help="Number of candidate pages from embedding pre-filter (default: 25)")
@click.option("--model", default=None, help="Claude model to use")
@click.option("--current-url", default=None, help="URL of the current page (to prevent self-linking)")
def process(
    file: Path,
    sitemaps: tuple[str, ...],
    all_sitemaps: bool,
    output: Path | None,
    max_links: int | None,
    top_n: int | None,
    model: str | None,
    current_url: str | None,
):
    """Process a file and insert internal links.

    Use --sitemap with a URL or a saved name. Repeat for multiple sitemaps.
    Use --all-sitemaps to use every saved sitemap at once.
    """
    from seo_linker.pipeline import run_pipeline

    config = Config.load()

    # Resolve sitemap URLs
    sitemap_urls = _resolve_sitemaps(sitemaps, all_sitemaps, config)

    if not sitemap_urls:
        raise click.ClickException(
            "No sitemaps specified. Use --sitemap URL, --sitemap NAME, or --all-sitemaps.\n"
            "Save sitemaps with: seo-linker add-sitemap NAME URL"
        )

    run_pipeline(
        input_path=file,
        sitemap_urls=sitemap_urls,
        output_path=output,
        max_links=max_links or config.max_links,
        top_n=top_n or config.top_n,
        model=model,
        current_url=current_url,
        config=config,
    )


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


@cli.command()
@click.option("--api-key", default=None, help="Anthropic API key")
@click.option("--model", default=None, help="Default Claude model")
@click.option("--max-links", type=int, default=None, help="Default max links")
@click.option("--top-n", type=int, default=None, help="Default top-N candidates")
def config(api_key: str | None, model: str | None, max_links: int | None, top_n: int | None):
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
    cfg.save()
    click.echo("Configuration saved to ~/.seo-linker/config.json")


@cli.command("add-sitemap")
@click.argument("name")
@click.argument("url")
def add_sitemap(name: str, url: str):
    """Save a sitemap URL with a short name for easy reuse.

    Example: seo-linker add-sitemap triumph-uk https://uk.triumph.com/sitemap_index.xml
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


if __name__ == "__main__":
    cli()
