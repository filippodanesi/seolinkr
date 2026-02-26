# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Tests for GSC cache module."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from seo_linker.gsc.cache import GSCCache, GSC_CACHE_DIR


@pytest.fixture
def cache(tmp_path):
    """Create a GSCCache that uses a temp directory."""
    with patch("seo_linker.gsc.cache.GSC_CACHE_DIR", tmp_path):
        yield GSCCache(ttl_hours=48)


class TestGSCCache:
    def test_write_and_read(self, cache, tmp_path):
        with patch("seo_linker.gsc.cache.GSC_CACHE_DIR", tmp_path):
            payload = {"page1": {"impressions": 100, "clicks": 10}}
            cache.write("sc-domain:example.com", "page_metrics", payload)
            result = cache.read("sc-domain:example.com", "page_metrics")
            assert result == payload

    def test_read_missing_returns_none(self, cache, tmp_path):
        with patch("seo_linker.gsc.cache.GSC_CACHE_DIR", tmp_path):
            result = cache.read("sc-domain:nonexistent.com", "page_metrics")
            assert result is None

    def test_expired_cache_returns_none(self, cache, tmp_path):
        with patch("seo_linker.gsc.cache.GSC_CACHE_DIR", tmp_path):
            payload = {"data": "old"}
            cache.write("sc-domain:example.com", "test_data", payload)

            # Manually set timestamp to past
            key_path = cache._key_path("sc-domain:example.com", "test_data")
            data = json.loads(key_path.read_text())
            data["_ts"] = time.time() - (49 * 3600)  # 49 hours ago (exceeds 48h TTL)
            key_path.write_text(json.dumps(data))

            result = cache.read("sc-domain:example.com", "test_data")
            assert result is None

    def test_valid_cache_within_ttl(self, cache, tmp_path):
        with patch("seo_linker.gsc.cache.GSC_CACHE_DIR", tmp_path):
            payload = {"data": "fresh"}
            cache.write("sc-domain:example.com", "test_data", payload)

            # Manually set timestamp to 1 hour ago
            key_path = cache._key_path("sc-domain:example.com", "test_data")
            data = json.loads(key_path.read_text())
            data["_ts"] = time.time() - 3600
            key_path.write_text(json.dumps(data))

            result = cache.read("sc-domain:example.com", "test_data")
            assert result == payload

    def test_clear_specific_site(self, cache, tmp_path):
        with patch("seo_linker.gsc.cache.GSC_CACHE_DIR", tmp_path):
            cache.write("sc-domain:site1.com", "page_metrics", {"a": 1})
            cache.write("sc-domain:site2.com", "page_metrics", {"b": 2})

            count = cache.clear("sc-domain:site1.com")
            assert count == 1

            # site1 cleared, site2 still there
            assert cache.read("sc-domain:site1.com", "page_metrics") is None
            assert cache.read("sc-domain:site2.com", "page_metrics") == {"b": 2}

    def test_clear_all(self, cache, tmp_path):
        with patch("seo_linker.gsc.cache.GSC_CACHE_DIR", tmp_path):
            cache.write("sc-domain:site1.com", "page_metrics", {"a": 1})
            cache.write("sc-domain:site2.com", "page_metrics", {"b": 2})

            count = cache.clear()
            assert count == 2
            assert cache.read("sc-domain:site1.com", "page_metrics") is None
            assert cache.read("sc-domain:site2.com", "page_metrics") is None

    def test_key_path_sanitizes_url(self, cache, tmp_path):
        with patch("seo_linker.gsc.cache.GSC_CACHE_DIR", tmp_path):
            path = cache._key_path("sc-domain:example.com", "page_metrics")
            assert "://" not in path.name
            assert path.suffix == ".json"
