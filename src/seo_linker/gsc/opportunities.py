# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Opportunity scoring — identifies pages that benefit most from internal links."""

from __future__ import annotations

import math
from dataclasses import dataclass

from seo_linker.gsc.client import GSCClient, PageMetrics


@dataclass
class Opportunity:
    """A page with its opportunity score and classification."""
    url: str
    impressions: int
    clicks: int
    position: float
    ctr: float
    opportunity_score: float
    priority: str  # "high", "medium", "quick_win", "low"
    reason: str


def score_opportunity(m: PageMetrics) -> tuple[float, str, str]:
    """Calculate opportunity score for a page.

    Returns (score, priority_level, reason).

    Scoring logic:
    - High priority: high impressions (>5K) + position 4-15
    - Quick win: high impressions + position 1-5
    - Medium: moderate impressions (1K-5K) + position 5-20
    - Low: everything else
    """
    imp = m.impressions
    pos = m.position

    # Volume factor: logarithmic scale, caps at ~1.0 for 50K+ impressions
    volume_factor = min(1.0, math.log10(max(imp, 1)) / 4.7)  # log10(50000) ~ 4.7

    # Position factor: bell curve centered on position ~8
    if 4 <= pos <= 15:
        position_factor = 1.0 - abs(pos - 8) / 12
    elif pos < 4:
        position_factor = 0.4  # Already strong, less marginal value
    else:
        position_factor = max(0, 0.3 - (pos - 15) / 50)  # Rapidly diminishing

    score = round(volume_factor * position_factor, 3)

    # Classify
    if imp >= 5000 and 4 <= pos <= 15:
        return score, "high", f"High impressions ({imp:,}) at position {pos:.1f} — link equity can push to top 3"
    elif imp >= 5000 and pos < 4:
        return score, "quick_win", f"Already near top ({pos:.1f}) with {imp:,} impressions — consolidate with links"
    elif imp >= 1000 and 5 <= pos <= 20:
        return score, "medium", f"Moderate volume ({imp:,}) at position {pos:.1f} — worth linking when relevant"
    else:
        return score, "low", f"{imp:,} impressions at position {pos:.1f}"


def compute_opportunities(
    gsc_client: GSCClient,
    site_url: str,
    days: int = 28,
    min_impressions: int = 100,
) -> list[Opportunity]:
    """Compute and rank all page opportunities for a site.

    Args:
        gsc_client: Authenticated GSC client
        site_url: GSC property
        days: Lookback window
        min_impressions: Minimum impressions threshold to include

    Returns:
        List of Opportunity objects, sorted by score descending
    """
    metrics = gsc_client.get_page_metrics(site_url, days=days)

    opportunities = []
    for url, m in metrics.items():
        if m.impressions < min_impressions:
            continue
        score, priority, reason = score_opportunity(m)
        opportunities.append(
            Opportunity(
                url=url,
                impressions=m.impressions,
                clicks=m.clicks,
                position=m.position,
                ctr=m.ctr,
                opportunity_score=score,
                priority=priority,
                reason=reason,
            )
        )

    opportunities.sort(key=lambda o: o.opportunity_score, reverse=True)
    return opportunities
