# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Audit route — wraps audit_file from the core engine."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, File, Form, UploadFile

from api.deps import temp_upload
from seo_linker.audit.checker import audit_file

router = APIRouter(tags=["audit"])


@router.post("/audit")
async def audit(
    file: UploadFile = File(...),
    site_domain: str | None = Form(None),
):
    """Audit a markdown file's internal links against CLAUDE.md rules."""
    content = await file.read()
    suffix = "." + (file.filename or "file.md").rsplit(".", 1)[-1]

    with temp_upload(content, suffix) as path:
        result = audit_file(path, site_domain)

    return asdict(result)
