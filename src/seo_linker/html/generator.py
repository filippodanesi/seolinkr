"""Generate HTML output with SEO metadata and title attributes on links."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from html import escape
from urllib.parse import urlparse

import anthropic
import markdown
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from seo_linker.models import TargetPage


def generate_html_output(
    linked_text: str,
    candidates: list[TargetPage],
    api_key: str,
    model: str,
    brand_name: str = "Triumph®",
    log_fn: Callable[[str], None] | None = None,
) -> tuple[str, dict[str, str]]:
    """Generate complete HTML output with SEO metadata and link titles.

    Returns
    -------
    tuple[str, dict[str, str]]
        The full HTML string and a dict with ``title`` and ``meta_description``.
    """
    log_fn = log_fn or (lambda _: None)

    # Build URL -> page title mapping from candidates
    url_titles: dict[str, str] = {}
    for p in candidates:
        if p.title:
            url_titles[p.url.rstrip("/")] = p.title

    # Generate title tag and meta description via Claude
    log_fn("Generating SEO title and meta description...")
    meta = _generate_meta(linked_text, api_key, model, brand_name)
    log_fn(f"  Title: {meta['title']}")
    log_fn(f"  Meta description: {meta['meta_description']}")

    # Convert markdown to HTML
    log_fn("Converting to HTML...")
    html_body = _md_to_html(linked_text)

    # Add title attributes to <a> tags
    html_body = _add_link_titles(html_body, url_titles)

    # Assemble final output
    parts = [
        "<!-- SEO Metadata -->",
        f"<title>{escape(meta['title'])}</title>",
        f'<meta name="description" content="{escape(meta["meta_description"])}" />',
        "",
        "<!-- Article Content -->",
        html_body,
    ]

    return "\n".join(parts), meta


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_META_SYSTEM_PROMPT = """\
You are an SEO metadata specialist. Generate a title tag and meta description \
for the provided article.

## Title tag rules
- MUST be under 60 characters total (including the brand suffix)
- End with " | {brand_name}"
- Front-load the primary keyword (place it as early as possible)
- Make it different from the H1: more concise, search-result-optimized
- Include a number or power word if it fits naturally
- Add the current year if the content is time-sensitive (guides, trends, etc.)
- Use sentence case, not Title Case

## Meta description rules
- Between 150 and 160 characters
- Include the primary keyword naturally in the first half
- End with a clear value proposition or subtle call to action
- Summarize what the reader will learn or gain
- Write in the same language as the article

## Output
Respond with a JSON object ONLY. No explanation, no markdown fences.
{{"title": "...", "meta_description": "..."}}
"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def _call_claude(api_key: str, model: str, user_prompt: str, system_prompt: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=300,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text


def _generate_meta(
    linked_text: str,
    api_key: str,
    model: str,
    brand_name: str,
) -> dict[str, str]:
    """Generate title tag and meta description via Claude."""
    # Extract H1 and first ~500 words for context
    lines = linked_text.strip().split("\n")
    h1 = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            h1 = stripped.lstrip("# ").strip("*").strip()
            break

    # Take first 500 words for context (enough for Claude to understand the topic)
    words = linked_text.split()
    excerpt = " ".join(words[:500])

    system = _META_SYSTEM_PROMPT.replace("{brand_name}", brand_name)

    user_prompt = f"## H1\n{h1}\n\n## Article excerpt\n{excerpt}"

    response = _call_claude(api_key, model, user_prompt, system)

    # Parse JSON from response (may be wrapped in code fences)
    json_match = re.search(r"\{.*\}", response, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return {
                "title": data.get("title", h1),
                "meta_description": data.get("meta_description", ""),
            }
        except json.JSONDecodeError:
            pass

    # Fallback: use H1 + brand as title
    return {
        "title": f"{h1} | {brand_name}" if h1 else brand_name,
        "meta_description": "",
    }


def _md_to_html(md_text: str) -> str:
    """Convert markdown to HTML."""
    html = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code"],
        output_format="html",
    )
    return html


def _add_link_titles(html: str, url_titles: dict[str, str]) -> str:
    """Add title attributes to <a> tags based on URL-to-title mapping."""
    if not url_titles:
        return html

    soup = BeautifulSoup(html, "html.parser")

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].rstrip("/")
        title = url_titles.get(href)
        if title and not a_tag.get("title"):
            a_tag["title"] = title

    return str(soup)
