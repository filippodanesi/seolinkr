# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Batch processing and audit routes."""

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
from seo_linker.audit.checker import audit_file
from seo_linker.batch import run_batch_audit, run_batch_pipeline

router = APIRouter(tags=["batch"])

_executor = ThreadPoolExecutor(max_workers=2)


@router.post("/batch-process")
async def batch_process(
    files: list[UploadFile] = File(...),
    sitemaps: str = Form(...),
    max_links: int = Form(10),
    top_n: int = Form(40),
    model: str | None = Form(None),
    gsc_site: str | None = Form(None),
    brand_guidelines: str | None = Form(None),
    enable_rewrite: bool = Form(False),
    content_type: str = Form("existing_article"),
    generate_html: bool = Form(False),
    brand_name: str = Form("Triumph\u00ae"),
):
    """Batch process multiple files with SSE progress streaming."""
    config = get_config()
    sitemap_urls = [s.strip() for s in sitemaps.split(",") if s.strip()]
    effective_guidelines = brand_guidelines or config.brand_guidelines or None

    # Read all file contents upfront
    file_data: list[tuple[str, bytes, str]] = []
    for f in files:
        content = await f.read()
        filename = f.filename or "file.md"
        suffix = "." + filename.rsplit(".", 1)[-1]
        file_data.append((filename, content, suffix))

    queue: asyncio.Queue[str] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def emit(event: dict[str, Any]) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, json.dumps(event))

    def _run() -> dict[str, Any]:
        import tempfile
        from pathlib import Path

        temp_paths: list[Path] = []
        try:
            # Write all uploads to temp files
            input_paths: list[Path] = []
            for filename, content, suffix in file_data:
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                    f.write(content)
                    f.flush()
                    path = Path(f.name)
                temp_paths.append(path)
                input_paths.append(path)

            # Build a filename map: temp_path.name -> original filename
            name_map = {input_paths[i].name: file_data[i][0] for i in range(len(file_data))}

            def log_fn(msg: str) -> None:
                emit({"type": "log", "message": msg})

            def file_start_fn(idx: int, fname: str, total: int) -> None:
                emit({
                    "type": "file_start",
                    "file_index": idx,
                    "filename": name_map.get(fname, fname),
                    "total_files": total,
                })

            def file_log_fn(idx: int, fname: str, msg: str) -> None:
                emit({
                    "type": "file_log",
                    "file_index": idx,
                    "filename": name_map.get(fname, fname),
                    "message": msg,
                })

            def file_done_fn(idx: int, fname: str, result: object) -> None:
                from seo_linker.models import LinkingResult

                data = asdict(result) if isinstance(result, LinkingResult) else {}
                # Read the output file for download
                out_path = input_paths[idx].with_name(
                    f"{input_paths[idx].stem}_linked{input_paths[idx].suffix}"
                )
                if out_path.exists():
                    try:
                        data["output_content"] = out_path.read_text(encoding="utf-8")
                    except Exception:
                        data["output_content"] = ""
                    raw = out_path.read_bytes()
                    data["output_base64"] = base64.b64encode(raw).decode("ascii")
                    orig = name_map.get(fname, fname)
                    stem = orig.rsplit(".", 1)[0]
                    ext = orig.rsplit(".", 1)[-1]
                    data["output_filename"] = f"{stem}_linked.{ext}"
                    temp_paths.append(out_path)

                emit({
                    "type": "file_done",
                    "file_index": idx,
                    "filename": name_map.get(fname, fname),
                    "result": data,
                })

            def file_error_fn(idx: int, fname: str, error: str) -> None:
                emit({
                    "type": "file_error",
                    "file_index": idx,
                    "filename": name_map.get(fname, fname),
                    "error": error,
                })

            result = run_batch_pipeline(
                input_paths=input_paths,
                sitemap_urls=sitemap_urls,
                max_links=max_links,
                top_n=top_n,
                model=model,
                config=config,
                gsc_site=gsc_site,
                brand_guidelines=effective_guidelines,
                enable_rewrite=enable_rewrite,
                content_type=content_type,
                generate_html=generate_html,
                brand_name=brand_name,
                log_fn=log_fn,
                file_start_fn=file_start_fn,
                file_log_fn=file_log_fn,
                file_done_fn=file_done_fn,
                file_error_fn=file_error_fn,
            )

            summary = asdict(result)
            return summary

        finally:
            for p in temp_paths:
                p.unlink(missing_ok=True)

    async def event_stream():
        future = loop.run_in_executor(_executor, _run)

        while not future.done():
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=10)
                yield f"data: {msg}\n\n"
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"

        # Drain remaining
        while not queue.empty():
            msg = queue.get_nowait()
            yield f"data: {msg}\n\n"

        try:
            result = future.result()
            yield f"data: {json.dumps({'type': 'batch_summary', 'data': result})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/batch-audit")
async def batch_audit(
    files: list[UploadFile] = File(...),
    site_domain: str | None = Form(None),
):
    """Audit multiple files, returning aggregate results."""
    import tempfile
    from pathlib import Path

    temp_paths: list[Path] = []
    input_paths: list[Path] = []
    name_map: dict[str, str] = {}

    try:
        for f in files:
            content = await f.read()
            filename = f.filename or "file.md"
            suffix = "." + filename.rsplit(".", 1)[-1]
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(content)
                tmp.flush()
                path = Path(tmp.name)
            temp_paths.append(path)
            input_paths.append(path)
            name_map[path.name] = filename

        result = run_batch_audit(
            input_paths=input_paths,
            site_domain=site_domain or None,
            log_fn=lambda _: None,
        )

        # Replace temp filenames with original filenames in results
        data = asdict(result)
        for fr in data["file_results"]:
            fr["filename"] = name_map.get(fr["filename"], fr["filename"])

        return data

    finally:
        for p in temp_paths:
            p.unlink(missing_ok=True)
