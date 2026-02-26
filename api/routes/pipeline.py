# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Pipeline route — wraps run_pipeline with SSE for real-time progress."""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from api.deps import get_config, get_gsc_client, temp_upload
from seo_linker.pipeline import run_pipeline

router = APIRouter(tags=["pipeline"])

_executor = ThreadPoolExecutor(max_workers=2)


@router.post("/process")
async def process(
    file: UploadFile = File(...),
    sitemaps: str = Form(...),
    max_links: int = Form(10),
    top_n: int = Form(40),
    model: str | None = Form(None),
    current_url: str | None = Form(None),
    gsc_site: str | None = Form(None),
    brand_guidelines: str | None = Form(None),
    enable_rewrite: bool = Form(False),
    content_type: str = Form("existing_article"),
    rewrite_instructions: str | None = Form(None),
    generate_html: bool = Form(False),
    brand_name: str = Form("Triumph®"),
):
    """Run the full linking pipeline with SSE progress streaming."""
    config = get_config()
    content = await file.read()
    filename = file.filename or "file.md"
    suffix = "." + filename.rsplit(".", 1)[-1]
    sitemap_urls = [s.strip() for s in sitemaps.split(",") if s.strip()]

    # Fall back to brand guidelines from config/.env if not provided in request
    effective_guidelines = brand_guidelines or config.brand_guidelines or None

    queue: asyncio.Queue[str] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def log_fn(msg: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, json.dumps({"type": "log", "message": msg}))

    def _run() -> dict[str, Any]:
        with temp_upload(content, suffix) as input_path:
            output_path = input_path.with_name(f"{input_path.stem}_linked{suffix}")
            gsc_client = get_gsc_client(config) if gsc_site else None
            result = run_pipeline(
                input_path=input_path,
                sitemap_urls=sitemap_urls,
                output_path=output_path,
                max_links=max_links,
                top_n=top_n,
                model=model,
                current_url=current_url,
                config=config,
                gsc_site=gsc_site,
                log_fn=log_fn,
                brand_guidelines=effective_guidelines,
                gsc_client=gsc_client,
                enable_rewrite=enable_rewrite,
                content_type=content_type,
                rewrite_instructions=rewrite_instructions,
                generate_html=generate_html,
                brand_name=brand_name,
            )
            data = asdict(result)
            # Read output file content if it exists
            if output_path.exists():
                data["output_content"] = output_path.read_text(encoding="utf-8")
            return data

    async def event_stream():
        future = loop.run_in_executor(_executor, _run)

        while not future.done():
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=0.5)
                yield f"data: {msg}\n\n"
            except asyncio.TimeoutError:
                continue

        # Drain remaining log messages
        while not queue.empty():
            msg = queue.get_nowait()
            yield f"data: {msg}\n\n"

        try:
            result = future.result()
            yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
