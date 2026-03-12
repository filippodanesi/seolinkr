# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""PLP batch processing route — inject links into PLP HTML content via SSE."""

from __future__ import annotations

import asyncio
import base64
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from api.deps import get_config, get_gsc_client, temp_upload
from seo_linker.plp_pipeline import run_plp_pipeline

router = APIRouter(tags=["plp"])

_executor = ThreadPoolExecutor(max_workers=2)


@router.post("/process-plps")
async def process_plps(
    file: UploadFile = File(...),
    sitemaps: str = Form(...),
    max_links: int = Form(5),
    top_n: int = Form(25),
    model: str | None = Form(None),
    gsc_site: str | None = Form(None),
    brand_guidelines: str | None = Form(None),
    sheet_name: str | None = Form(None),
    url_col: str | None = Form(None),
    content_col: str | None = Form(None),
    keyword_col: str | None = Form(None),
    related_kw_col: str | None = Form(None),
):
    """Run PLP batch pipeline with SSE progress streaming."""
    config = get_config()
    content = await file.read()
    filename = file.filename or "file.xlsx"
    stem = filename.rsplit(".", 1)[0]
    sitemap_urls = [s.strip() for s in sitemaps.split(",") if s.strip()]

    effective_guidelines = brand_guidelines or config.brand_guidelines or None

    queue: asyncio.Queue[str] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def log_fn(msg: str) -> None:
        loop.call_soon_threadsafe(
            queue.put_nowait,
            json.dumps({"type": "log", "message": msg}),
        )

    def _run() -> dict[str, Any]:
        with temp_upload(content, ".xlsx") as input_path:
            output_path = input_path.with_name(f"{input_path.stem}_linked.xlsx")
            gsc_client = get_gsc_client(config) if gsc_site else None
            result = run_plp_pipeline(
                input_path=input_path,
                sitemap_urls=sitemap_urls,
                output_path=output_path,
                sheet_name=sheet_name,
                url_col=url_col,
                content_col=content_col,
                keyword_col=keyword_col,
                related_kw_col=related_kw_col,
                max_links=max_links,
                top_n=top_n,
                model=model,
                config=config,
                gsc_site=gsc_site,
                brand_guidelines=effective_guidelines,
                gsc_client=gsc_client,
                log_fn=log_fn,
            )
            data = asdict(result)
            if output_path.exists():
                raw_bytes = output_path.read_bytes()
                data["output_base64"] = base64.b64encode(raw_bytes).decode("ascii")
                data["output_filename"] = f"{stem}_linked.xlsx"
            return data

    async def event_stream():
        future = loop.run_in_executor(_executor, _run)

        while not future.done():
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=10)
                yield f"data: {msg}\n\n"
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"

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
