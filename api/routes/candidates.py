"""Candidates route — wraps prefilter_pages pipeline."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile

from api.deps import get_config, get_gsc_client, temp_upload
from seo_linker.matching.prefilter import prefilter_pages
from seo_linker.models import TargetPage
from seo_linker.parsers.detector import detect_parser
from seo_linker.sitemap.enricher import enrich_pages
from seo_linker.sitemap.fetcher import fetch_sitemap

router = APIRouter(tags=["candidates"])


@router.post("/candidates")
async def get_candidates(
    file: UploadFile = File(...),
    sitemaps: str = Form(...),
    top_n: int = Form(40),
    gsc_site: str | None = Form(None),
) -> list[dict[str, Any]]:
    """Pre-filter and return top candidate pages for an article."""
    config = get_config()
    content = await file.read()
    suffix = "." + (file.filename or "file.md").rsplit(".", 1)[-1]
    sitemap_urls = [s.strip() for s in sitemaps.split(",") if s.strip()]

    with temp_upload(content, suffix) as path:
        parser = detect_parser(path)
        sections = parser.parse(path)

    # Fetch and merge sitemaps
    pages: list[TargetPage] = []
    for url in sitemap_urls:
        pages.extend(fetch_sitemap(url))

    # Deduplicate
    seen: set[str] = set()
    unique: list[TargetPage] = []
    for p in pages:
        if p.url not in seen:
            seen.add(p.url)
            unique.append(p)
    pages = unique

    # Filter product pages
    pages = [p for p in pages if not p.url.rstrip("/").endswith(".html")]

    # Enrich metadata
    pages = enrich_pages(pages, config.cache_ttl_hours)

    # GSC enrichment
    if gsc_site:
        client = get_gsc_client(config)
        if client:
            pages = client.enrich_candidates(pages, gsc_site)

    # Pre-filter
    candidates = prefilter_pages(sections, pages, top_n, config.embedding_model)

    return [
        {
            "url": p.url,
            "title": p.title,
            "meta_description": p.meta_description,
            "h1": p.h1,
            "impressions": p.impressions,
            "clicks": p.clicks,
            "avg_position": p.avg_position,
            "top_queries": p.top_queries,
            "opportunity_score": p.opportunity_score,
        }
        for p in candidates
    ]
