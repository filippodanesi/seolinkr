# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Markdown file parser."""

from __future__ import annotations

import re
from pathlib import Path

from seo_linker.models import ContentSection
from seo_linker.parsers.base import BaseParser


class MarkdownParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".md", ".markdown"]

    def parse(self, file_path: Path) -> list[ContentSection]:
        text = file_path.read_text(encoding="utf-8")
        # Split by headings to create sections
        sections: list[ContentSection] = []
        # Match lines starting with # (markdown headings)
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
        matches = list(heading_pattern.finditer(text))

        if not matches:
            # No headings: treat entire text as one section
            return [ContentSection(text=text.strip(), index=0)]

        # Text before first heading
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append(ContentSection(text=preamble, index=0))

        for i, match in enumerate(matches):
            heading = match.group(2).strip()
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[start:end].strip()
            sections.append(
                ContentSection(text=section_text, index=len(sections), heading=heading)
            )

        return sections
