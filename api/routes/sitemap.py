"""Sitemap routes — list saved sitemaps and analyze new ones."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from api.deps import get_config
from seo_linker.sitemap.fetcher import fetch_sitemap

router = APIRouter(tags=["sitemap"])


@router.get("/sitemaps")
def list_sitemaps() -> dict[str, str]:
    """Return saved sitemap name->URL mappings from config."""
    config = get_config()
    return config.sitemaps


@router.post("/sitemaps/analyze")
def analyze_sitemap(url: str = Body(..., embed=True)) -> dict[str, Any]:
    """Fetch a sitemap URL and return a preview of pages found."""
    pages = fetch_sitemap(url)
    return {
        "url": url,
        "total_pages": len(pages),
        "sample_urls": [p.url for p in pages[:20]],
        "has_products": any(p.url.rstrip("/").endswith(".html") for p in pages),
        "product_count": sum(1 for p in pages if p.url.rstrip("/").endswith(".html")),
        "category_count": sum(1 for p in pages if not p.url.rstrip("/").endswith(".html")),
    }
