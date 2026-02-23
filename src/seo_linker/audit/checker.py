"""Audit an article's internal links against CLAUDE.md rules."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class AuditIssue:
    type: str          # "missing_cross_link", "generic_anchor", "heading_link", "too_few_links", etc.
    severity: str      # "error", "warning", "info"
    message: str
    url: str = ""
    anchor: str = ""


@dataclass
class LinkInfo:
    anchor_text: str
    target_url: str
    link_type: str     # "category", "magazine", "product", "external", "other"


@dataclass
class AuditResult:
    file: str
    total_links: int
    category_links: int
    magazine_links: int
    product_links: int
    external_links: int
    issues: list[AuditIssue] = field(default_factory=list)
    links: list[LinkInfo] = field(default_factory=list)


# Markdown link pattern
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Generic anchor patterns to flag
GENERIC_ANCHORS = {"hier", "here", "klicken", "click", "mehr", "more", "link", "this", "diese"}


def audit_file(file_path: Path, site_domain: str | None = None) -> AuditResult:
    """Audit a markdown file's internal links.

    Args:
        file_path: Path to the markdown file
        site_domain: Expected domain (e.g. "www.example.com") for classifying links.
                     If None, inferred from the first internal link found.

    Returns:
        AuditResult with link inventory and issues
    """
    text = file_path.read_text(encoding="utf-8")
    matches = LINK_RE.findall(text)

    links: list[LinkInfo] = []
    issues: list[AuditIssue] = []

    # Detect domain from first link if not provided
    if not site_domain:
        for _, url in matches:
            parsed = urlparse(url)
            if parsed.hostname and parsed.scheme in ("http", "https"):
                site_domain = parsed.hostname
                break

    for anchor, url in matches:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        path = parsed.path or ""

        # Classify link type
        if site_domain and site_domain in hostname:
            if "/magazine/" in path or "/magazin/" in path:
                link_type = "magazine"
            elif path.rstrip("/").endswith(".html"):
                link_type = "product"
            else:
                link_type = "category"
        elif hostname:
            link_type = "external"
        else:
            link_type = "other"

        links.append(LinkInfo(anchor_text=anchor, target_url=url, link_type=link_type))

        # Check for generic anchors
        anchor_lower = anchor.strip().lower()
        if anchor_lower in GENERIC_ANCHORS or len(anchor_lower.split()) < 2:
            if anchor_lower not in GENERIC_ANCHORS and len(anchor_lower) > 10:
                pass  # Long single-word anchors like brand names are OK
            else:
                issues.append(AuditIssue(
                    type="generic_anchor",
                    severity="info",
                    message=f"Anchor text '{anchor}' is generic — consider more descriptive phrasing",
                    url=url,
                    anchor=anchor,
                ))

    # Count by type
    category_count = sum(1 for l in links if l.link_type == "category")
    magazine_count = sum(1 for l in links if l.link_type == "magazine")
    product_count = sum(1 for l in links if l.link_type == "product")
    external_count = sum(1 for l in links if l.link_type == "external")

    # CLAUDE.md rule checks
    if category_count < 3:
        issues.append(AuditIssue(
            type="too_few_category_links",
            severity="warning",
            message=f"Only {category_count} category links (CLAUDE.md rule: minimum 3)",
        ))

    if magazine_count < 1:
        issues.append(AuditIssue(
            type="missing_cross_link",
            severity="warning",
            message="No links to other magazine articles (CLAUDE.md rule: minimum 1)",
        ))

    # Check for links in headings
    heading_lines = [line for line in text.split("\n") if line.strip().startswith("#")]
    for heading_line in heading_lines:
        if LINK_RE.search(heading_line):
            issues.append(AuditIssue(
                type="heading_link",
                severity="error",
                message=f"Link found in heading: {heading_line.strip()[:80]}",
            ))

    # Check for duplicate URLs
    url_counts: dict[str, int] = {}
    for l in links:
        url_counts[l.target_url] = url_counts.get(l.target_url, 0) + 1
    for url, count in url_counts.items():
        if count > 1:
            issues.append(AuditIssue(
                type="duplicate_url",
                severity="warning",
                message=f"URL linked {count} times: {url}",
                url=url,
            ))

    return AuditResult(
        file=file_path.name,
        total_links=len(links),
        category_links=category_count,
        magazine_links=magazine_count,
        product_links=product_count,
        external_links=external_count,
        issues=issues,
        links=links,
    )
