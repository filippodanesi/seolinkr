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
