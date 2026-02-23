"""Configuration management for SEO linker."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

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
        # Env vars override file config
        env_key = os.environ.get("ANTHROPIC_API_KEY")
        if env_key:
            config.api_key = env_key
        return config
