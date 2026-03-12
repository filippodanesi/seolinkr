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

    # Verify all linked URLs return 200 — remove broken links
    linked_html, insertions = _remove_broken_links(linked_html, insertions)

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

    # Build URL → clean title lookup (both full URL and path-only)
    title_map: dict[str, str] = {}
    for page in candidate_pages:
        if page.title:
            clean = _clean_page_title(page.title)
            if clean:
                title_map[page.url] = clean
                parsed = urlparse(page.url)
                if parsed.path:
                    title_map[parsed.path] = clean

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
            parsed = urlparse(href)
            title = title_map.get(parsed.path)
        if not title:
            return tag
        safe_title = title.replace('"', '&quot;')
        # Insert title before the closing > of the tag
        return tag[:href_match.end()] + f' title="{safe_title}"' + tag[href_match.end():]

    return re.sub(r'<a\s[^>]*>', _add_title, html)


def _clean_page_title(title: str) -> str:
    """Clean a page <title> for use as a link title attribute.

    Removes brand suffixes like '| Triumph', '[CATEGORY] im offiziellen...',
    and other boilerplate.
    """
    # Remove patterns like "[SHAPEWEAR] im offiziellen Triumph® Online Shop"
    title = re.sub(r'\[.*?\]\s*im\s+offiziellen.*$', '', title, flags=re.IGNORECASE).strip()
    # Remove "| Triumph", "- Triumph", "| Brand" suffixes
    title = re.sub(r'\s*[|–—-]\s*(Triumph|triumph).*$', '', title).strip()
    # Remove "im offiziellen Triumph® Online Shop" standalone
    title = re.sub(r'\s*im\s+offiziellen\s+Triumph.*$', '', title, flags=re.IGNORECASE).strip()
    # Remove "® " and "™"
    title = title.replace('®', '').replace('™', '').strip()
    return title


def _remove_broken_links(
    html: str, insertions: list[LinkInsertion]
) -> tuple[str, list[LinkInsertion]]:
    """Check all <a> hrefs return HTTP 200. Remove links that don't.

    Broken links are unwrapped: the <a> tag is removed but the anchor
    text is preserved so the content reads naturally.
    """
    import logging
    import requests

    logger = logging.getLogger(__name__)

    # Extract all unique hrefs from the HTML
    hrefs = set(re.findall(r'<a\s[^>]*href=["\']([^"\']+)["\']', html))
    if not hrefs:
        return html, insertions

    # Check each URL (HEAD request with short timeout)
    broken: set[str] = set()
    session = requests.Session()
    session.headers.update({"User-Agent": "SEOLinkr/1.0 (link-checker)"})

    for url in hrefs:
        if not url.startswith(("http://", "https://")):
            continue
        try:
            resp = session.head(url, timeout=8, allow_redirects=True)
            if resp.status_code != 200:
                logger.warning("Broken link removed: %s → HTTP %d", url, resp.status_code)
                broken.add(url)
        except Exception as e:
            logger.warning("Broken link removed: %s → %s", url, e)
            broken.add(url)

    session.close()

    if not broken:
        return html, insertions

    # Unwrap broken <a> tags — keep anchor text, remove the tag
    for url in broken:
        escaped = re.escape(url)
        html = re.sub(
            rf'<a\s[^>]*href=["\']{ escaped }["\'][^>]*>(.*?)</a>',
            r'\1',
            html,
        )

    # Filter insertions report
    valid = [ins for ins in insertions if ins.target_url not in broken]

    logger.info("Link check: %d OK, %d broken removed", len(hrefs) - len(broken), len(broken))
    return html, valid
