"""Markdown writer — simply writes the linked text."""

from __future__ import annotations

from pathlib import Path

from seo_linker.models import LinkingResult
from seo_linker.writers.base import BaseWriter


class MarkdownWriter(BaseWriter):
    def write(self, result: LinkingResult, input_path: Path, output_path: Path) -> None:
        output_path.write_text(result.linked_text, encoding="utf-8")
