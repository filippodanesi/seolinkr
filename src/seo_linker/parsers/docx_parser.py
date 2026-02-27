# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""DOCX file parser."""

from __future__ import annotations

from pathlib import Path

from docx import Document

from seo_linker.models import ContentSection
from seo_linker.parsers.base import BaseParser


class DocxParser(BaseParser):
    def supported_extensions(self) -> list[str]:
        return [".docx"]

    def parse(self, file_path: Path) -> list[ContentSection]:
        doc = Document(str(file_path))
        sections: list[ContentSection] = []
        current_lines: list[str] = []
        current_heading = ""

        def flush():
            nonlocal current_lines, current_heading
            text = "\n".join(current_lines).strip()
            if text:
                sections.append(
                    ContentSection(
                        text=text, index=len(sections), heading=current_heading
                    )
                )
            current_lines = []

        # Build an ordered list of body elements (paragraphs + tables)
        # so tables are emitted in their correct document position.
        body = doc.element.body
        for child in body:
            tag = child.tag.split("}")[-1]  # e.g. "p", "tbl"

            if tag == "tbl":
                # Convert the table to markdown and append to current section
                md_lines = _table_to_markdown(child, doc)
                if md_lines:
                    current_lines.extend(md_lines)

            elif tag == "p":
                # Find the matching Paragraph object
                para_text = child.text or ""
                # Use python-docx Paragraph wrapper for style access
                from docx.text.paragraph import Paragraph

                para = Paragraph(child, doc)
                style_name = (para.style.name or "").lower()
                if "heading" in style_name:
                    flush()
                    current_heading = para.text.strip()
                    current_lines.append(para.text)
                else:
                    current_lines.append(para.text)

        flush()

        if not sections:
            full_text = "\n".join(p.text for p in doc.paragraphs).strip()
            if full_text:
                sections.append(ContentSection(text=full_text, index=0))

        return sections


def _table_to_markdown(tbl_element, doc) -> list[str]:
    """Convert a docx table XML element to markdown table lines."""
    from docx.table import Table

    table = Table(tbl_element, doc)
    if not table.rows:
        return []

    rows: list[list[str]] = []
    for row in table.rows:
        rows.append([cell.text.strip() for cell in row.cells])

    if not rows:
        return []

    n_cols = max(len(r) for r in rows)
    lines: list[str] = []

    # Header row
    header = rows[0] + [""] * (n_cols - len(rows[0]))
    lines.append("| " + " | ".join(header) + " |")

    # Separator
    lines.append("| " + " | ".join("---" for _ in range(n_cols)) + " |")

    # Data rows
    for row in rows[1:]:
        cells = row + [""] * (n_cols - len(row))
        lines.append("| " + " | ".join(cells) + " |")

    return lines
