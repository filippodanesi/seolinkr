"""Claude API integration for content rewriting/optimization."""

from __future__ import annotations

from collections.abc import Callable

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from seo_linker.models import ContentSection
from seo_linker.rewriting.rewrite_prompt_builder import (
    build_rewrite_system_prompt,
    build_rewrite_user_prompt,
)

CHUNK_WORDS = 3000


def rewrite_content(
    sections: list[ContentSection],
    api_key: str,
    model: str = "claude-opus-4-6",
    brand_guidelines: str | None = None,
    content_type: str = "existing_article",
    custom_instructions: str | None = None,
    log_fn: Callable[[str], None] | None = None,
) -> list[ContentSection]:
    """Rewrite/optimize content sections via Claude.

    Returns a new list of ``ContentSection`` with the rewritten text.
    """
    log_fn = log_fn or (lambda _: None)

    system_prompt = build_rewrite_system_prompt(
        brand_guidelines=brand_guidelines,
        content_type=content_type,
        custom_instructions=custom_instructions,
    )

    full_text = "\n\n".join(s.text for s in sections)
    word_count = len(full_text.split())

    if word_count <= CHUNK_WORDS + 500:
        log_fn("  Rewriting content in a single pass...")
        rewritten = _rewrite_single(full_text, api_key, model, system_prompt)
    else:
        log_fn(f"  Content is ~{word_count} words, rewriting in chunks...")
        rewritten = _rewrite_chunked(full_text, sections, api_key, model, system_prompt, log_fn)

    # Return as a single ContentSection (the rewriter may restructure headings)
    return [ContentSection(text=rewritten, index=0)]


def _strip_preamble(text: str) -> str:
    """Remove any reasoning preamble before the first markdown heading."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("#"):
            return "\n".join(lines[i:])
    return text


def _rewrite_single(
    text: str,
    api_key: str,
    model: str,
    system_prompt: str,
) -> str:
    user_prompt = build_rewrite_user_prompt(text)
    return _strip_preamble(_call_claude(api_key, model, user_prompt, system_prompt))


def _rewrite_chunked(
    full_text: str,
    sections: list[ContentSection],
    api_key: str,
    model: str,
    system_prompt: str,
    log_fn: Callable[[str], None],
) -> str:
    chunks = _split_into_chunks(full_text, CHUNK_WORDS)
    rewritten_chunks: list[str] = []
    previous_headings: list[str] = []

    for i, chunk in enumerate(chunks):
        log_fn(f"  Rewriting chunk {i + 1}/{len(chunks)}...")
        user_prompt = build_rewrite_user_prompt(
            chunk,
            previous_headings=previous_headings if previous_headings else None,
        )
        result = _strip_preamble(_call_claude(api_key, model, user_prompt, system_prompt))
        rewritten_chunks.append(result)

        # Extract headings from this chunk for inter-chunk context
        for line in result.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                # Remove # prefix to get heading text
                heading_text = stripped.lstrip("#").strip()
                if heading_text:
                    previous_headings.append(heading_text)

    return "\n\n".join(rewritten_chunks)


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
        max_tokens=16384,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text
