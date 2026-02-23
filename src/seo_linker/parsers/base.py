"""Abstract base parser."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from seo_linker.models import ContentSection


class BaseParser(ABC):
    """Base class for content parsers."""

    @abstractmethod
    def parse(self, file_path: Path) -> list[ContentSection]:
        """Parse a file and return content sections."""
        ...

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions (e.g. ['.md'])."""
        ...
