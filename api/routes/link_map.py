# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Link Map route — generate strategic internal link recommendations via SSE."""

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
from seo_linker.link_map_pipeline import run_link_map_pipeline

router = APIRouter(tags=["link-map"])

_executor = ThreadPoolExecutor(max_workers=2)


@router.post("/link-map")
async def link_map(
    gsc_site: str = Form(...),
    urls: str | None = Form(None),
    urls_file: UploadFile | None = File(None),
    url_pattern: str | None = Form(None),
    days: int = Form(90),
    min_shared: int = Form(1),
):
    """Generate a strategic link map with SSE progress streaming."""
    config = get_config()

    # Resolve URL list
    url_list: list[str] = []
    if urls:
        url_list = [u.strip() for u in urls.split(",") if u.strip()]
    elif urls_file and urls_file.filename:
        content = await urls_file.read()
        suffix = "." + (urls_file.filename or "urls.txt").rsplit(".", 1)[-1]
        # Parse URLs from file content
        if suffix == ".xlsx":
            import tempfile
            from pathlib import Path

            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
                f.write(content)
                tmp_path = Path(f.name)
            from seo_linker.cli import _load_urls_from_file
            url_list = _load_urls_from_file(tmp_path)
            tmp_path.unlink(missing_ok=True)
        else:
            text = content.decode("utf-8")
            url_list = [
                line.strip() for line in text.splitlines()
                if line.strip().startswith("http")
            ]

    queue: asyncio.Queue[str] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def log_fn(msg: str) -> None:
        loop.call_soon_threadsafe(
            queue.put_nowait,
            json.dumps({"type": "log", "message": msg}),
        )

    def _run() -> dict[str, Any]:
        import tempfile
        from pathlib import Path

        output_path = Path(tempfile.mktemp(suffix=".xlsx"))
        gsc_client = get_gsc_client(config)
        result = run_link_map_pipeline(
            urls=url_list,
            gsc_site=gsc_site,
            output_path=output_path,
            url_pattern=url_pattern,
            days=days,
            min_shared_queries=min_shared,
            config=config,
            gsc_client=gsc_client,
            log_fn=log_fn,
        )
        data = asdict(result)
        if output_path.exists():
            raw_bytes = output_path.read_bytes()
            data["output_base64"] = base64.b64encode(raw_bytes).decode("ascii")
            data["output_filename"] = "link_map.xlsx"
            output_path.unlink(missing_ok=True)
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
