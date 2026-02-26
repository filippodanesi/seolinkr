# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""GSC data cache — avoids redundant API calls across multiple runs."""

from __future__ import annotations

import json
import time
from pathlib import Path

GSC_CACHE_DIR = Path.home() / ".seo-linker" / "gsc_cache"


class GSCCache:
    def __init__(self, ttl_hours: int = 48):
        self.ttl_hours = ttl_hours
        GSC_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _key_path(self, site_url: str, data_type: str) -> Path:
        """Generate cache file path from site URL and data type."""
        safe_name = site_url.replace("://", "_").replace("/", "_").replace(":", "_")
        return GSC_CACHE_DIR / f"{safe_name}_{data_type}.json"

    def read(self, site_url: str, data_type: str) -> dict | None:
        """Read cached data if it exists and hasn't expired."""
        path = self._key_path(site_url, data_type)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            if time.time() - data.get("_ts", 0) < self.ttl_hours * 3600:
                return data.get("payload")
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    def write(self, site_url: str, data_type: str, payload: dict | list) -> None:
        """Write data to cache with timestamp."""
        path = self._key_path(site_url, data_type)
        try:
            path.write_text(json.dumps({"_ts": time.time(), "payload": payload}))
        except Exception:
            pass  # Cache write failure is non-fatal

    def clear(self, site_url: str | None = None) -> int:
        """Clear cache. If site_url given, clear only that site. Returns files removed."""
        count = 0
        if site_url:
            safe_name = site_url.replace("://", "_").replace("/", "_").replace(":", "_")
            for f in GSC_CACHE_DIR.glob(f"{safe_name}_*.json"):
                f.unlink()
                count += 1
        else:
            for f in GSC_CACHE_DIR.glob("*.json"):
                f.unlink()
                count += 1
        return count
