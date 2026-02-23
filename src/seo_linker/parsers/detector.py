"""Auto-detect file format and return the appropriate parser."""

from __future__ import annotations

from pathlib import Path

from seo_linker.parsers.base import BaseParser
from seo_linker.parsers.docx_parser import DocxParser
from seo_linker.parsers.markdown_parser import MarkdownParser
from seo_linker.parsers.xlsx_parser import XlsxParser

_PARSERS: list[BaseParser] = [
    MarkdownParser(),
    DocxParser(),
    XlsxParser(),
]


def detect_parser(file_path: Path) -> BaseParser:
    """Return the appropriate parser for the given file extension."""
    ext = file_path.suffix.lower()
    for parser in _PARSERS:
        if ext in parser.supported_extensions():
            return parser
    supported = [e for p in _PARSERS for e in p.supported_extensions()]
    raise ValueError(
        f"Unsupported file format '{ext}'. Supported: {', '.join(supported)}"
    )
