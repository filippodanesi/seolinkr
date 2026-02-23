"""Abstract base writer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from seo_linker.models import LinkingResult


class BaseWriter(ABC):
    @abstractmethod
    def write(
        self,
        result: LinkingResult,
        input_path: Path,
        output_path: Path,
    ) -> None:
        """Write the linked content to the output file."""
        ...
