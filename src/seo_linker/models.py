"""Data models for the SEO internal linking tool."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TargetPage:
    """A page from the sitemap that could be a link target."""

    url: str
    title: str = ""
    meta_description: str = ""
    body_text: str = ""

    @property
    def display_text(self) -> str:
        parts = [self.url]
        if self.title:
            parts.append(f"Title: {self.title}")
        if self.meta_description:
            parts.append(f"Description: {self.meta_description}")
        return " | ".join(parts)

    @property
    def embedding_text(self) -> str:
        parts = []
        if self.title:
            parts.append(self.title)
        if self.meta_description:
            parts.append(self.meta_description)
        if self.body_text:
            parts.append(self.body_text)
        if not parts:
            # Fallback: extract readable text from URL path
            from urllib.parse import urlparse

            path = urlparse(self.url).path.strip("/")
            parts.append(path.replace("-", " ").replace("/", " "))
        return ". ".join(parts)


@dataclass
class ContentSection:
    """A section of the input content."""

    text: str
    index: int = 0
    heading: str = ""


@dataclass
class LinkInsertion:
    """A single link insertion recommended by Claude."""

    anchor_text: str
    target_url: str
    reasoning: str = ""


@dataclass
class LinkingResult:
    """Result of the linking process for a piece of content."""

    original_text: str
    linked_text: str
    insertions: list[LinkInsertion] = field(default_factory=list)
    candidate_pages_count: int = 0
    total_sitemap_pages: int = 0
