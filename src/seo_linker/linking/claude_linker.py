# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Claude API integration for semantic link insertion."""

from __future__ import annotations

import json
import re

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from seo_linker.linking.prompt_builder import build_system_prompt, build_user_prompt
from seo_linker.models import (
    ContentSection,
    LinkInsertion,
    LinkingResult,
    TargetPage,
)

CHUNK_WORDS = 3000
REPORT_SEPARATOR = "---REPORT---"


def link_content(
    sections: list[ContentSection],
    candidate_pages: list[TargetPage],
    api_key: str,
    model: str = "claude-opus-4-6",
    max_links: int = 10,
    current_url: str | None = None,
    brand_guidelines: str | None = None,
) -> LinkingResult:
    """Process content sections through Claude to insert internal links."""
    system_prompt = build_system_prompt(brand_guidelines)
    full_text = "\n\n".join(s.text for s in sections)
    word_count = len(full_text.split())

    if word_count <= CHUNK_WORDS + 500:
        return _process_single(
            full_text, candidate_pages, api_key, model, max_links, current_url,
            system_prompt,
        )
    else:
        return _process_chunked(
            full_text, candidate_pages, api_key, model, max_links, current_url,
            system_prompt,
        )


def _process_single(
    text: str,
    pages: list[TargetPage],
    api_key: str,
    model: str,
    max_links: int,
    current_url: str | None,
    system_prompt: str,
) -> LinkingResult:
    user_prompt = build_user_prompt(text, pages, current_url, max_links)
    response = _call_claude(api_key, model, user_prompt, system_prompt)
    linked_text, insertions = _parse_response(response)

    return LinkingResult(
        original_text=text,
        linked_text=linked_text,
        insertions=insertions,
        candidate_pages_count=len(pages),
    )


def _process_chunked(
    text: str,
    pages: list[TargetPage],
    api_key: str,
    model: str,
    max_links: int,
    current_url: str | None,
    system_prompt: str,
) -> LinkingResult:
    chunks = _split_into_chunks(text, CHUNK_WORDS)
    linked_chunks: list[str] = []
    all_insertions: list[LinkInsertion] = []
    already_linked: set[str] = set()
    links_per_chunk = max(2, max_links // len(chunks))

    for i, chunk in enumerate(chunks):
        # Last chunk gets remaining link budget
        remaining = max_links - len(all_insertions)
        chunk_max = min(links_per_chunk, remaining) if remaining > 0 else 0

        if chunk_max <= 0:
            linked_chunks.append(chunk)
            continue

        user_prompt = build_user_prompt(
            chunk, pages, current_url, chunk_max, already_linked
        )
        response = _call_claude(api_key, model, user_prompt, system_prompt)
        linked_text, insertions = _parse_response(response)

        linked_chunks.append(linked_text)
        all_insertions.extend(insertions)
        already_linked.update(ins.target_url for ins in insertions)

    return LinkingResult(
        original_text=text,
        linked_text="\n\n".join(linked_chunks),
        insertions=all_insertions,
        candidate_pages_count=len(pages),
    )


def _split_into_chunks(text: str, max_words: int) -> list[str]:
    """Split text into chunks at paragraph boundaries."""
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for para in paragraphs:
        para_words = len(para.split())
        if current_words + para_words > max_words and current:
            chunks.append("\n\n".join(current))
            current = [para]
            current_words = para_words
        else:
            current.append(para)
            current_words += para_words

    if current:
        chunks.append("\n\n".join(current))

    return chunks


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


def _strip_preamble(text: str) -> str:
    """Remove any analysis/reasoning preamble before the actual content.

    Claude sometimes prepends reasoning text before the markdown content.
    We detect this by finding the first markdown heading (line starting with #)
    and stripping everything before it.
    """
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("#"):
            return "\n".join(lines[i:])
    # No heading found — return as-is
    return text


def _parse_response(response: str) -> tuple[str, list[LinkInsertion]]:
    """Parse Claude's response into linked text and insertion report."""
    if REPORT_SEPARATOR in response:
        parts = response.split(REPORT_SEPARATOR, 1)
        linked_text = parts[0].strip()
        report_text = parts[1].strip()
    else:
        linked_text = response.strip()
        report_text = ""

    # Strip any reasoning preamble before the actual content
    linked_text = _strip_preamble(linked_text)

    insertions: list[LinkInsertion] = []
    if report_text:
        # Extract JSON array from report (may be wrapped in code fences)
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

    # Cross-check: verify reported insertions actually exist in the text
    raw_links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", linked_text)
    # Strip optional title from URL portion: 'url "title"' → 'url'
    actual_links = set()
    for anchor, raw_url in raw_links:
        url = re.sub(r"""\s+["'].*["']\s*$""", "", raw_url.strip())
        actual_links.add((anchor, url))
    verified: list[LinkInsertion] = []
    for ins in insertions:
        if any(url == ins.target_url for _, url in actual_links):
            verified.append(ins)

    return linked_text, verified
