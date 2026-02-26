# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Markdown writer — simply writes the linked text."""

from __future__ import annotations

from pathlib import Path

from seo_linker.models import LinkingResult
from seo_linker.writers.base import BaseWriter


class MarkdownWriter(BaseWriter):
    def write(self, result: LinkingResult, input_path: Path, output_path: Path) -> None:
        parts: list[str] = []

        # Prepend SEO metadata as HTML comment block
        if result.seo_title or result.seo_meta_description:
            parts.append("<!--")
            parts.append(f"Title: {result.seo_title}")
            parts.append(f"Meta Description: {result.seo_meta_description}")
            parts.append("-->")
            parts.append("")

        parts.append(result.linked_text)
        output_path.write_text("\n".join(parts), encoding="utf-8")
