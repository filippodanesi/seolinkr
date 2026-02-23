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
    # GSC metrics (populated by GSCClient.enrich_candidates)
    impressions: int = 0
    clicks: int = 0
    avg_position: float = 0.0
    top_queries: list[str] = field(default_factory=list)

    @property
    def display_text(self) -> str:
        parts = [self.url]
        if self.title:
            parts.append(f"Title: {self.title}")
        if self.meta_description:
            parts.append(f"Description: {self.meta_description}")
        if self.impressions > 0:
            parts.append(f"GSC: {self.impressions} imp, pos {self.avg_position:.1f}")
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

    @property
    def opportunity_score(self) -> float:
        """Opportunity score: how much this page would benefit from internal links.

        Higher = more benefit. Pages with high impressions in position 4-15
        gain the most from link equity boosts.
        Returns 0.0 if no GSC data.
        """
        if self.impressions == 0:
            return 0.0
        import math
        volume = min(1.0, math.log10(max(self.impressions, 1)) / 4.7)
        if 4 <= self.avg_position <= 15:
            position = 1.0 - abs(self.avg_position - 8) / 12
        elif self.avg_position < 4:
            position = 0.4
        else:
            position = max(0, 0.3 - (self.avg_position - 15) / 50)
        return round(volume * position, 3)


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
    rewritten_text: str = ""
