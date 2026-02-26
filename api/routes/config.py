"""Config routes — read and update tool configuration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Body

from api.deps import get_config

router = APIRouter(tags=["config"])


@router.get("/config")
def read_config() -> dict[str, Any]:
    """Return current configuration (API keys are masked)."""
    config = get_config()
    data = asdict(config)
    # Mask sensitive values
    if data.get("api_key"):
        data["api_key"] = data["api_key"][:10] + "..."
    return data


@router.put("/config")
def update_config(updates: dict[str, Any] = Body(...)) -> dict[str, str]:
    """Update configuration fields and persist to disk."""
    config = get_config()
    for key, value in updates.items():
        if hasattr(config, key):
            setattr(config, key, value)
    config.save()
    return {"status": "ok"}
