"""Enrich target pages with title and meta description via concurrent HTTP fetches."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

from seo_linker.models import TargetPage

CACHE_DIR = Path.home() / ".seo-linker" / "cache"
CONCURRENCY = 20
FETCH_TIMEOUT = 15

# Small pool of recent, realistic browser UAs
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# Accept-Language per TLD/subdomain market
_LANG_MAP = {
    "uk": "en-GB,en;q=0.9",
    "de": "de-DE,de;q=0.9,en;q=0.5",
    "fr": "fr-FR,fr;q=0.9,en;q=0.5",
    "it": "it-IT,it;q=0.9,en;q=0.5",
    "es": "es-ES,es;q=0.9,en;q=0.5",
    "nl": "nl-NL,nl;q=0.9,en;q=0.5",
    "com": "en-US,en;q=0.9",
}

# Status codes that are intentional blocks — never retry
_NO_RETRY_STATUSES = {403, 404, 410, 451}


def enrich_pages(
    pages: list[TargetPage], cache_ttl_hours: int = 24
) -> list[TargetPage]:
    """Enrich pages with title and meta description. Uses async I/O internally."""
    return asyncio.run(_enrich_all(pages, cache_ttl_hours))


def _detect_accept_language(urls: list[str]) -> str:
    """Detect the best Accept-Language from the sitemap URLs."""
    if not urls:
        return "en-US,en;q=0.9"
    # Check subdomain first (e.g. uk.triumph.com), then TLD
    host = urlparse(urls[0]).hostname or ""
    parts = host.split(".")
    # Subdomain: uk.triumph.com → "uk"
    if len(parts) >= 3:
        subdomain = parts[0].lower()
        if subdomain in _LANG_MAP:
            return _LANG_MAP[subdomain]
    # TLD: triumph.de → "de"
    tld = parts[-1].lower() if parts else ""
    return _LANG_MAP.get(tld, "en-US,en;q=0.9")


async def _enrich_all(
    pages: list[TargetPage], cache_ttl_hours: int
) -> list[TargetPage]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)
    timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT)
    accept_lang = _detect_accept_language([p.url for p in pages])

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [
            _enrich_one(session, sem, page, cache_ttl_hours, idx, accept_lang)
            for idx, page in enumerate(pages)
        ]
        return await asyncio.gather(*tasks)


async def _enrich_one(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    page: TargetPage,
    cache_ttl_hours: int,
    idx: int,
    accept_lang: str,
) -> TargetPage:
    # Check cache first
    cached = _read_cache(page.url, cache_ttl_hours)
    if cached:
        page.title = cached.get("title", "")
        page.meta_description = cached.get("meta_description", "")
        page.body_text = cached.get("body_text", "")
        return page

    async with sem:
        html = await _fetch_with_retry(session, page.url, idx, accept_lang)
        if not html:
            return page

    soup = BeautifulSoup(html, "lxml")

    # Extract title
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        page.title = _clean_title(title_tag.string.strip())

    # Extract meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        page.meta_description = str(meta_desc["content"]).strip()

    # Fallback: if no title from <title> tag, try og:title or <h1>
    if not page.title:
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            page.title = _clean_title(str(og_title["content"]).strip())

    if not page.title:
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            page.title = h1.get_text(strip=True)

    # Fallback: if no meta description, try og:description
    if not page.meta_description:
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            page.meta_description = str(og_desc["content"]).strip()

    # Extract main body text for richer embeddings
    page.body_text = _extract_body_text(soup)

    _write_cache(
        page.url,
        {
            "title": page.title,
            "meta_description": page.meta_description,
            "body_text": page.body_text,
        },
    )
    return page


def _extract_body_text(soup: BeautifulSoup) -> str:
    """Extract main body text, stripping nav, footer, sidebar, scripts, styles."""
    # Remove noise elements
    for tag in soup.find_all(
        ["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]
    ):
        tag.decompose()

    # Also remove common noise by class/id/role patterns
    for attr in ("class", "id", "role"):
        for el in soup.find_all(
            attrs={attr: re.compile(r"nav|menu|footer|sidebar|cookie|banner|breadcrumb", re.I)}
        ):
            el.decompose()

    # Try to find main content container
    main = soup.find("main") or soup.find(attrs={"role": "main"}) or soup.find("article")
    source = main if main else soup.body if soup.body else soup

    # Get text, collapse whitespace
    text = source.get_text(separator=" ", strip=True)
    # Collapse multiple spaces/newlines
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _clean_title(title: str) -> str:
    """Strip brand suffix from titles like 'Sports Bras | BrandName - Shop Now'.

    Splits on common separators (|, -, –, —, :) and keeps the meaningful part.
    If the first segment is too short (1 word), keeps first + second segment
    to avoid over-trimming (e.g. "Bras | Triumph | Women's Lingerie" → "Bras | Triumph"
    would still be too generic, so we get "Bras Triumph" instead of just "Bras").
    """
    parts = re.split(r"\s*[|–—]\s*|\s+-\s+|\s*:\s+", title)
    if len(parts) <= 1:
        return title

    first = parts[0].strip()

    # First segment is substantive (2+ words or 15+ chars) — use it alone
    if len(first.split()) >= 2 or len(first) >= 15:
        return first

    # First segment is too short (e.g. "Bras") — join first two segments
    if len(parts) >= 2:
        second = parts[1].strip()
        return f"{first} {second}".strip()

    return title


async def _fetch_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    idx: int,
    accept_lang: str,
    max_retries: int = 2,
) -> str | None:
    """Fetch URL with retry (1s → 3s backoff) and rotating User-Agent."""
    backoff_delays = [1, 3]

    for attempt in range(max_retries + 1):
        try:
            ua = USER_AGENTS[(idx + attempt) % len(USER_AGENTS)]
            headers = {
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": accept_lang,
            }
            async with session.get(url, headers=headers, allow_redirects=True) as resp:
                if resp.status == 200:
                    return await resp.text(errors="replace")
                # Intentional blocks — don't retry
                if resp.status in _NO_RETRY_STATUSES:
                    return None
                # Transient errors (429, 5xx) — retry with backoff
                if attempt < max_retries:
                    await asyncio.sleep(backoff_delays[attempt])
                    continue
                return None
        except Exception:
            if attempt < max_retries:
                await asyncio.sleep(backoff_delays[attempt])
                continue
            return None
    return None


def _cache_key(url: str) -> Path:
    h = hashlib.sha256(url.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{h}.json"


def _read_cache(url: str, ttl_hours: int) -> dict | None:
    path = _cache_key(url)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data.get("ts", 0) < ttl_hours * 3600:
            return data
    except Exception:
        pass
    return None


def _write_cache(url: str, data: dict) -> None:
    path = _cache_key(url)
    try:
        data["ts"] = time.time()
        path.write_text(json.dumps(data))
    except Exception:
        pass
