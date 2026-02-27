# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Configuration management for SEO linker."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

import requests

CONFIG_DIR = Path.home() / ".seo-linker"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Config:
    api_key: str = ""
    default_model: str = "claude-opus-4-6"
    max_links: int = 10
    top_n: int = 40
    embedding_model: str = "intfloat/multilingual-e5-small"
    cache_ttl_hours: int = 24
    sitemaps: dict[str, str] = field(default_factory=dict)  # name -> sitemap URL
    brand_guidelines: str = ""
    # GSC settings
    gsc_service_account: str = ""       # Path to service account JSON
    gsc_oauth_secrets: str = ""         # Path to OAuth client secrets JSON
    gsc_cache_ttl: int = 48             # Hours to cache GSC data (default: 48)

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls) -> Config:
        config = cls()
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text())
            for k, v in data.items():
                if hasattr(config, k):
                    setattr(config, k, v)

        # --- Env vars override file config ---
        env_key = os.environ.get("ANTHROPIC_API_KEY")
        if env_key:
            config.api_key = env_key

        # Brand guidelines: URL (blob storage) > local file > inline env var
        bg_url = os.environ.get("BRAND_GUIDELINES_URL")
        if bg_url:
            config.brand_guidelines = _fetch_text(bg_url)
        else:
            bg_file = os.environ.get("BRAND_GUIDELINES_FILE")
            if bg_file and Path(bg_file).is_file():
                config.brand_guidelines = Path(bg_file).read_text(encoding="utf-8")
            else:
                env_bg = os.environ.get("BRAND_GUIDELINES")
                if env_bg:
                    config.brand_guidelines = env_bg

        # Sitemaps: JSON string from env
        env_sitemaps = os.environ.get("SITEMAPS")
        if env_sitemaps:
            try:
                config.sitemaps = json.loads(env_sitemaps)
            except json.JSONDecodeError:
                pass

        # GSC service account: inline JSON > file path
        env_gsc_json = os.environ.get("GSC_SERVICE_ACCOUNT_JSON")
        if env_gsc_json:
            config.gsc_service_account = _write_temp_json(env_gsc_json)
        else:
            env_gsc_file = os.environ.get("GSC_SERVICE_ACCOUNT_FILE")
            if env_gsc_file and Path(env_gsc_file).is_file():
                config.gsc_service_account = env_gsc_file

        return config


def _fetch_text(url: str) -> str:
    """Fetch text content from a URL (blob storage, CDN, etc.)."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException:
        return ""


def _write_temp_json(json_str: str) -> str:
    """Write a JSON string to a persistent temp file and return its path."""
    tmp = Path(tempfile.gettempdir()) / "seo_linker_gsc_sa.json"
    tmp.write_text(json_str, encoding="utf-8")
    return str(tmp)
