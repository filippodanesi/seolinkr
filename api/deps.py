"""Shared dependencies for API routes."""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from seo_linker.config import Config


def get_config() -> Config:
    return Config.load()


def get_gsc_client(config: Config | None = None):
    """Create a GSCClient if credentials are configured, else None."""
    config = config or get_config()
    if not config.gsc_service_account and not config.gsc_oauth_secrets:
        return None
    from seo_linker.gsc.client import GSCClient

    return GSCClient(
        service_account_path=config.gsc_service_account or None,
        oauth_client_secrets_path=config.gsc_oauth_secrets or None,
        cache_ttl_hours=config.gsc_cache_ttl,
    )


@contextmanager
def temp_upload(content: bytes, suffix: str) -> Generator[Path, None, None]:
    """Write uploaded bytes to a temp file, yield the path, clean up."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(content)
        f.flush()
        path = Path(f.name)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)
