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

        for para in doc.paragraphs:
            style_name = (para.style.name or "").lower()
            if "heading" in style_name:
                flush()
                current_heading = para.text.strip()
                current_lines.append(para.text)
            else:
                current_lines.append(para.text)

        flush()

        if not sections:
            # Fallback: entire document as single section
            full_text = "\n".join(p.text for p in doc.paragraphs).strip()
            if full_text:
                sections.append(ContentSection(text=full_text, index=0))

        return sections
