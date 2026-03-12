# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""FastAPI application — thin API layer over the SEO linker core engine."""

from __future__ import annotations

import logging
import os

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")

from dotenv import load_dotenv

load_dotenv()  # Load .env before anything reads os.environ

from seo_linker.config import Config

_log = logging.getLogger("seolinkr.startup")


def _check_config() -> None:
    """Log a summary of loaded configuration at startup."""
    cfg = Config.load()
    _log.info("--- Configuration check ---")

    # API key
    if cfg.api_key:
        _log.info("ANTHROPIC_API_KEY: OK (%s...%s)", cfg.api_key[:7], cfg.api_key[-4:])
    else:
        _log.warning("ANTHROPIC_API_KEY: MISSING")

    # HF token
    hf = os.environ.get("HF_TOKEN", "")
    if hf:
        _log.info("HF_TOKEN: OK (%s...%s)", hf[:5], hf[-4:])
    else:
        _log.warning("HF_TOKEN: MISSING")

    # Brand guidelines
    if cfg.brand_guidelines:
        _log.info("BRAND_GUIDELINES: OK (%d chars)", len(cfg.brand_guidelines))
    else:
        _log.warning("BRAND_GUIDELINES: NOT LOADED (no URL, file, or inline value)")

    # Sitemaps
    if cfg.sitemaps:
        _log.info("SITEMAPS: %d configured (%s)", len(cfg.sitemaps), ", ".join(cfg.sitemaps))
    else:
        _log.warning("SITEMAPS: NONE")

    # GSC
    if cfg.gsc_service_account:
        _log.info("GSC_SERVICE_ACCOUNT: OK")
    elif cfg.gsc_oauth_secrets:
        _log.info("GSC_OAUTH_SECRETS: OK")
    else:
        _log.warning("GSC: NO CREDENTIALS (GSC features disabled)")

    # Frontend URL
    frontend = os.environ.get("FRONTEND_URL", "")
    if frontend:
        _log.info("FRONTEND_URL: %s", frontend)
    else:
        _log.info("FRONTEND_URL: not set (CORS localhost only)")

    _log.info("Model: %s | Max links: %d | Top-N: %d", cfg.default_model, cfg.max_links, cfg.top_n)
    _log.info("--- End configuration check ---")


_check_config()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import audit, batch, candidates, config, gsc, link_map, pipeline, plp, sitemap, xlsx_utils

app = FastAPI(
    title="SEO Internal Linker API",
    version="0.4.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

_allowed_origins = ["http://localhost:3000"]
_frontend_url = os.environ.get("FRONTEND_URL")
if _frontend_url:
    _allowed_origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audit.router, prefix="/api")
app.include_router(batch.router, prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(gsc.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(plp.router, prefix="/api")
app.include_router(link_map.router, prefix="/api")
app.include_router(sitemap.router, prefix="/api")
app.include_router(xlsx_utils.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
