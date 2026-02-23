"""Cross-link intelligence — finds linking opportunities between blog articles based on shared GSC queries."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from urllib.parse import urlparse

from seo_linker.gsc.client import GSCClient


@dataclass
class CrossLinkOpportunity:
    """A cross-linking opportunity between two articles."""
    source_url: str
    target_url: str
    shared_queries: list[str]
    shared_query_count: int
    target_impressions: int
    target_position: float
    relevance_score: float
    suggestion: str  # Human-readable suggestion


def find_cross_link_gaps(
    gsc_client: GSCClient,
    site_url: str,
    url_pattern: str = "/magazine/|/magazin/",
    days: int = 28,
    min_shared_queries: int = 2,
) -> list[CrossLinkOpportunity]:
    """Find cross-linking opportunities between blog articles.

    Logic:
    1. Fetch queries for all magazine articles (one API call, cached)
    2. For every pair of articles, compute query overlap
    3. Pairs with significant overlap are cross-link candidates
    4. Score by: shared query count x target page opportunity value

    Args:
        gsc_client: Authenticated GSC client
        site_url: GSC property
        url_pattern: Regex for filtering magazine/blog URLs
        days: Lookback window
        min_shared_queries: Minimum shared queries to consider a pair

    Returns:
        List of CrossLinkOpportunity, sorted by relevance_score desc
    """
    page_queries = gsc_client.get_magazine_queries(site_url, url_pattern, days)
    page_metrics = gsc_client.get_page_metrics(site_url, days)

    if len(page_queries) < 2:
        return []

    # Build query sets per page (use top 50 queries by impressions)
    query_sets: dict[str, set[str]] = {}
    for url, queries in page_queries.items():
        query_sets[url] = {q.query for q in queries[:50]}

    opportunities: list[CrossLinkOpportunity] = []

    for url_a, url_b in combinations(query_sets.keys(), 2):
        shared = query_sets[url_a] & query_sets[url_b]
        if len(shared) < min_shared_queries:
            continue

        # Create bidirectional opportunities (A->B and B->A)
        for source, target in [(url_a, url_b), (url_b, url_a)]:
            target_metrics = page_metrics.get(target)
            target_imp = target_metrics.impressions if target_metrics else 0
            target_pos = target_metrics.position if target_metrics else 0.0

            # Score: more shared queries + higher target opportunity = better
            score = len(shared) * (1 + target_imp / 10000) * (1 / max(target_pos, 1))
            score = round(score, 3)

            opportunities.append(
                CrossLinkOpportunity(
                    source_url=source,
                    target_url=target,
                    shared_queries=sorted(shared)[:10],  # Cap at 10 for readability
                    shared_query_count=len(shared),
                    target_impressions=target_imp,
                    target_position=target_pos,
                    relevance_score=score,
                    suggestion=f"Link from {_short_path(source)} to {_short_path(target)} — "
                    f"{len(shared)} shared queries, target at pos {target_pos:.1f}",
                )
            )

    opportunities.sort(key=lambda o: o.relevance_score, reverse=True)
    return opportunities


def _short_path(url: str) -> str:
    """Extract readable path from URL."""
    return urlparse(url).path.rstrip("/").split("/")[-1] or url
