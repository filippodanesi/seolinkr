# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""GSC routes — opportunity scoring and cross-link gap analysis."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from api.deps import get_config, get_gsc_client

router = APIRouter(tags=["gsc"])


@router.get("/gsc/opportunities")
def get_opportunities(
    site_url: str = Query(...),
    days: int = Query(28),
    min_impressions: int = Query(100),
) -> list[dict[str, Any]]:
    """Compute and rank page opportunities for a GSC property."""
    config = get_config()
    client = get_gsc_client(config)
    if not client:
        raise HTTPException(status_code=400, detail="GSC credentials not configured")

    from seo_linker.gsc.opportunities import compute_opportunities

    opportunities = compute_opportunities(client, site_url, days, min_impressions)
    return [asdict(o) for o in opportunities]


@router.get("/gsc/cross-gaps")
def get_cross_gaps(
    site_url: str = Query(...),
    url_pattern: str = Query("/magazine/|/magazin/"),
    days: int = Query(28),
    min_shared_queries: int = Query(2),
) -> list[dict[str, Any]]:
    """Find cross-linking opportunities between blog articles."""
    config = get_config()
    client = get_gsc_client(config)
    if not client:
        raise HTTPException(status_code=400, detail="GSC credentials not configured")

    from seo_linker.gsc.cross_linker import find_cross_link_gaps

    gaps = find_cross_link_gaps(client, site_url, url_pattern, days, min_shared_queries)
    return [asdict(g) for g in gaps]
