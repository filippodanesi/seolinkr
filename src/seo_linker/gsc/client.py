"""Lightweight GSC client — bulk fetch, cache, local lookup."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from seo_linker.gsc.auth import authenticate
from seo_linker.gsc.cache import GSCCache
from seo_linker.models import TargetPage


@dataclass
class PageMetrics:
    """GSC metrics for a single page."""
    url: str
    impressions: int = 0
    clicks: int = 0
    ctr: float = 0.0
    position: float = 0.0


@dataclass
class QueryData:
    """A single query with its metrics for a page."""
    query: str
    impressions: int = 0
    clicks: int = 0
    position: float = 0.0


class GSCClient:
    """Google Search Console client with bulk fetch and caching.

    Designed for minimal API usage:
    - get_page_metrics: 1 API call per site (paginated if >25K rows), cached 48h
    - get_magazine_queries: 1 API call per site+pattern, cached 48h
    - enrich_candidates: 0 API calls (local lookup on cached data)
    """

    def __init__(
        self,
        service_account_path: str | None = None,
        oauth_client_secrets_path: str | None = None,
        cache_ttl_hours: int = 48,
    ):
        self._service = authenticate(service_account_path, oauth_client_secrets_path)
        self._cache = GSCCache(ttl_hours=cache_ttl_hours)

    def get_page_metrics(
        self, site_url: str, days: int = 28
    ) -> dict[str, PageMetrics]:
        """Fetch metrics for ALL pages in one bulk API call. Cached.

        Args:
            site_url: GSC property (e.g. "sc-domain:example.com")
            days: Lookback window (default 28 — roughly one month)

        Returns:
            Dict mapping URL -> PageMetrics
        """
        cached = self._cache.read(site_url, "page_metrics")
        if cached is not None:
            return {
                url: PageMetrics(**m) for url, m in cached.items()
            }

        end_date = datetime.now() - timedelta(days=3)  # GSC data has ~3 day lag
        start_date = end_date - timedelta(days=days)

        all_rows = []
        start_row = 0
        ROW_LIMIT = 25000  # Max per API call

        while True:
            response = (
                self._service.searchanalytics()
                .query(
                    siteUrl=site_url,
                    body={
                        "startDate": start_date.strftime("%Y-%m-%d"),
                        "endDate": end_date.strftime("%Y-%m-%d"),
                        "dimensions": ["page"],
                        "rowLimit": ROW_LIMIT,
                        "startRow": start_row,
                    },
                )
                .execute()
            )

            rows = response.get("rows", [])
            if not rows:
                break

            all_rows.extend(rows)

            if len(rows) < ROW_LIMIT:
                break  # Last page
            start_row += ROW_LIMIT

        metrics: dict[str, PageMetrics] = {}
        for row in all_rows:
            url = row["keys"][0]
            metrics[url] = PageMetrics(
                url=url,
                impressions=int(row.get("impressions", 0)),
                clicks=int(row.get("clicks", 0)),
                ctr=float(row.get("ctr", 0.0)),
                position=float(row.get("position", 0.0)),
            )

        # Cache as plain dicts for JSON serialization
        cache_payload = {
            url: {
                "url": m.url,
                "impressions": m.impressions,
                "clicks": m.clicks,
                "ctr": m.ctr,
                "position": m.position,
            }
            for url, m in metrics.items()
        }
        self._cache.write(site_url, "page_metrics", cache_payload)

        return metrics

    def get_magazine_queries(
        self,
        site_url: str,
        url_pattern: str = "/magazine/|/magazin/",
        days: int = 28,
    ) -> dict[str, list[QueryData]]:
        """Fetch queries for all pages matching a URL pattern. ONE API call. Cached.

        Args:
            site_url: GSC property
            url_pattern: Regex pattern for filtering pages (e.g. "/magazine/|/magazin/")
            days: Lookback window

        Returns:
            Dict mapping page URL -> list of QueryData (sorted by impressions desc)
        """
        cache_key = f"queries_{url_pattern.replace('/', '_').replace('|', '_')}"
        cached = self._cache.read(site_url, cache_key)
        if cached is not None:
            return {
                url: [QueryData(**q) for q in queries]
                for url, queries in cached.items()
            }

        end_date = datetime.now() - timedelta(days=3)
        start_date = end_date - timedelta(days=days)

        all_rows = []
        start_row = 0
        ROW_LIMIT = 25000

        while True:
            response = (
                self._service.searchanalytics()
                .query(
                    siteUrl=site_url,
                    body={
                        "startDate": start_date.strftime("%Y-%m-%d"),
                        "endDate": end_date.strftime("%Y-%m-%d"),
                        "dimensions": ["page", "query"],
                        "dimensionFilterGroups": [
                            {
                                "filters": [
                                    {
                                        "dimension": "page",
                                        "operator": "includingRegex",
                                        "expression": url_pattern,
                                    }
                                ]
                            }
                        ],
                        "rowLimit": ROW_LIMIT,
                        "startRow": start_row,
                    },
                )
                .execute()
            )

            rows = response.get("rows", [])
            if not rows:
                break

            all_rows.extend(rows)

            if len(rows) < ROW_LIMIT:
                break
            start_row += ROW_LIMIT

        by_page: dict[str, list[QueryData]] = defaultdict(list)
        for row in all_rows:
            page_url, query_text = row["keys"]
            by_page[page_url].append(
                QueryData(
                    query=query_text,
                    impressions=int(row.get("impressions", 0)),
                    clicks=int(row.get("clicks", 0)),
                    position=float(row.get("position", 0.0)),
                )
            )

        # Sort each page's queries by impressions desc
        for url in by_page:
            by_page[url].sort(key=lambda q: q.impressions, reverse=True)

        # Cache
        cache_payload = {
            url: [
                {
                    "query": q.query,
                    "impressions": q.impressions,
                    "clicks": q.clicks,
                    "position": q.position,
                }
                for q in queries
            ]
            for url, queries in by_page.items()
        }
        self._cache.write(site_url, cache_key, cache_payload)

        return dict(by_page)

    def enrich_candidates(
        self, candidates: list[TargetPage], site_url: str
    ) -> list[TargetPage]:
        """Attach GSC metrics to pre-filtered candidate pages.

        ZERO API calls — reads from cache populated by get_page_metrics().
        If cache is empty, calls get_page_metrics() once (which then caches).

        Args:
            candidates: List of TargetPage objects (already filtered by embeddings)
            site_url: GSC property

        Returns:
            Same list with GSC fields populated where data exists
        """
        all_metrics = self.get_page_metrics(site_url)

        for page in candidates:
            metrics = all_metrics.get(page.url)
            if metrics:
                page.impressions = metrics.impressions
                page.clicks = metrics.clicks
                page.avg_position = metrics.position
            # Also try with/without trailing slash
            alt_url = page.url.rstrip("/") if page.url.endswith("/") else page.url + "/"
            if not metrics:
                metrics = all_metrics.get(alt_url)
                if metrics:
                    page.impressions = metrics.impressions
                    page.clicks = metrics.clicks
                    page.avg_position = metrics.position

        return candidates
