# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Fetch and parse sitemap XML, handling sitemap index and gzip."""

from __future__ import annotations

import gzip
from io import BytesIO
from urllib.parse import urlparse

import requests
from lxml import etree

from seo_linker.models import TargetPage

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
TIMEOUT = 30


def fetch_sitemap(url: str) -> list[TargetPage]:
    """Fetch a sitemap URL and return all pages found (handles index sitemaps)."""
    pages: list[TargetPage] = []
    _fetch_recursive(url, pages, depth=0)
    return pages


def _fetch_recursive(url: str, pages: list[TargetPage], depth: int) -> None:
    if depth > 3:
        return

    content = _download(url)
    root = etree.fromstring(content)
    tag = etree.QName(root.tag).localname if isinstance(root.tag, str) else root.tag

    if tag == "sitemapindex":
        # It's a sitemap index — recurse into child sitemaps
        for sitemap_el in root.findall("sm:sitemap/sm:loc", SITEMAP_NS):
            if sitemap_el.text:
                _fetch_recursive(sitemap_el.text.strip(), pages, depth + 1)
    elif tag == "urlset":
        for url_el in root.findall("sm:url/sm:loc", SITEMAP_NS):
            if url_el.text:
                pages.append(TargetPage(url=url_el.text.strip()))


def _download(url: str) -> bytes:
    resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "SEOLinker/0.1"})
    resp.raise_for_status()
    data = resp.content
    # Detect gzip
    if url.endswith(".gz") or data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return data
