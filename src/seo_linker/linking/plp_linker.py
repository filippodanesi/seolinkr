# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Claude API integration for PLP HTML link injection."""

from __future__ import annotations

import json
import re

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from seo_linker.linking.plp_prompt_builder import (
    build_plp_system_prompt,
    build_plp_user_prompt,
)
from seo_linker.models import LinkInsertion, TargetPage

REPORT_SEPARATOR = "---REPORT---"


def link_plp_html(
    html_content: str,
    candidate_pages: list[TargetPage],
    api_key: str,
    model: str = "claude-sonnet-4-6",
    max_links: int = 5,
    current_url: str | None = None,
    brand_guidelines: str | None = None,
    target_keyword: str | None = None,
    related_keywords: str | None = None,
) -> tuple[str, list[LinkInsertion]]:
    """Inject internal links into PLP HTML content via Claude.

    Returns:
        Tuple of (linked_html, list of LinkInsertion).
    """
    system_prompt = build_plp_system_prompt(brand_guidelines)
    user_prompt = build_plp_user_prompt(
        html_content, candidate_pages, current_url, max_links,
        target_keyword, related_keywords,
    )

    response = _call_claude(api_key, model, user_prompt, system_prompt)
    linked_html, insertions = _parse_html_response(response)

    # Normalize all hrefs to absolute URLs
    if current_url:
        linked_html = _normalize_urls(linked_html, current_url)

    # Ensure every <a> has a title attribute — fallback to candidate page title
    linked_html = _ensure_title_attrs(linked_html, candidate_pages)

    return linked_html, insertions


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def _call_claude(api_key: str, model: str, user_prompt: str, system_prompt: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text


def _parse_html_response(response: str) -> tuple[str, list[LinkInsertion]]:
    """Parse Claude's response into linked HTML and insertion report."""
    if REPORT_SEPARATOR in response:
        parts = response.split(REPORT_SEPARATOR, 1)
        linked_html = parts[0].strip()
        report_text = parts[1].strip()
    else:
        linked_html = response.strip()
        report_text = ""

    # Strip code fences if Claude wrapped the HTML
    linked_html = re.sub(r"^```html?\s*\n?", "", linked_html)
    linked_html = re.sub(r"\n?```\s*$", "", linked_html)

    # Strip any preamble before the first HTML tag
    first_tag = re.search(r"<[a-zA-Z]", linked_html)
    if first_tag and first_tag.start() > 0:
        linked_html = linked_html[first_tag.start():]

    insertions: list[LinkInsertion] = []
    if report_text:
        json_match = re.search(r"\[.*\]", report_text, re.DOTALL)
        if json_match:
            try:
                items = json.loads(json_match.group())
                for item in items:
                    insertions.append(
                        LinkInsertion(
                            anchor_text=item.get("anchor_text", ""),
                            target_url=item.get("target_url", ""),
                            reasoning=item.get("reasoning", ""),
                        )
                    )
            except json.JSONDecodeError:
                pass

    # Cross-check: verify reported links exist in HTML
    actual_links = set(re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\']', linked_html))
    verified = [ins for ins in insertions if ins.target_url in actual_links]

    return linked_html, verified


def _normalize_urls(html: str, current_url: str) -> str:
    """Convert relative hrefs to absolute URLs based on the current page's domain."""
    from urllib.parse import urlparse, urljoin

    parsed = urlparse(current_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    def _make_absolute(match: re.Match) -> str:
        quote = match.group(1)
        href = match.group(2)
        if href.startswith(("http://", "https://")):
            return match.group(0)
        absolute = urljoin(base, href)
        return f'href={quote}{absolute}{quote}'

    return re.sub(r'href=(["\'])([^"\']+)\1', _make_absolute, html)


def _ensure_title_attrs(html: str, candidate_pages: list[TargetPage]) -> str:
    """Add missing title attributes to <a> tags using candidate page titles."""
    from urllib.parse import urlparse

    # Build URL → title lookup (both full URL and path-only)
    title_map: dict[str, str] = {}
    for page in candidate_pages:
        if page.title:
            title_map[page.url] = page.title
            parsed = urlparse(page.url)
            if parsed.path:
                title_map[parsed.path] = page.title

    def _add_title(match: re.Match) -> str:
        tag = match.group(0)
        # Already has title — skip
        if re.search(r'\btitle\s*=', tag):
            return tag
        # Extract href
        href_match = re.search(r'href=["\']([^"\']+)["\']', tag)
        if not href_match:
            return tag
        href = href_match.group(1)
        # Look up title from candidates
        title = title_map.get(href)
        if not title:
            # Try path only
            parsed = urlparse(href)
            title = title_map.get(parsed.path)
        if not title:
            return tag
        # Escape quotes in title
        safe_title = title.replace('"', '&quot;')
        # Insert title after href
        return tag[:href_match.end() + 1] + f' title="{safe_title}"' + tag[href_match.end() + 1:]

    return re.sub(r'<a\s[^>]*>', _add_title, html)
