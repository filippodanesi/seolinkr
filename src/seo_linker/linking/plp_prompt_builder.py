# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Build system and user prompts for PLP HTML internal link injection."""

from __future__ import annotations

from seo_linker.models import TargetPage


PLP_SYSTEM_PROMPT = """\
You are an expert SEO specialist focused on internal linking for e-commerce \
category pages (PLPs — Product Listing Pages). Your task is to inject internal \
links into HTML content blocks that appear on category pages.

The content is HTML (with <h2>, <p>, <ul>, <li> tags). You must return HTML \
with <a> tags inserted — NOT markdown links.

## Rules

### Relevance & intent
1. **Semantic relevance**: Only link where the surrounding context is genuinely \
related to the target page. Category pages link to related categories, subcategories, \
and informational content within the same product universe.
2. **Cross-category linking**: Prefer linking to sibling or child categories. \
For example, a "Bras" page should link to "Push-Up Bras", "Sports Bras", \
"Strapless Bras" — not to unrelated categories like "Pyjamas".
3. **Magazine/blog links**: Include 1-2 links to relevant magazine/blog articles \
if they cover topics mentioned in the text (e.g., sizing guides, style tips).
4. **No product links**: Never link to individual product pages (.html URLs).

### Anchor text & HTML format
5. **Use <a> tags**: Insert links as `<a href="URL" title="description">anchor text</a>`.
6. **Descriptive anchor text**: Use 2-4 word phrases naturally present in the text. \
Never rewrite sentences to create anchors.
7. **Anchor text variety**: Mix exact keywords, partial matches, and natural phrases.
8. **No duplicate URLs**: Never link to the same URL twice in the content.

### Density & placement
9. **Adaptive density**: Insert 2-5 links per content block. Short blocks (1-2 \
paragraphs) get 2-3 links; longer blocks get 3-5.
10. **Body text only**: Never add links inside headings (<h2>, <h3> tags).
11. **Max 1 link per sentence**, max 2 per paragraph.
12. **Self-link prevention**: If a "current page URL" is provided, never link to it.
13. **No homepage links**: Never link to the site root URL.

### HTML integrity
14. **Preserve HTML structure**: Do not change the HTML structure, tags, or attributes. \
Only add <a> tags within existing text content.
15. **Valid HTML**: Ensure all <a> tags are properly opened and closed.
16. **No nested links**: Never place an <a> tag inside another <a> tag.

### Human-sounding text (CRITICAL)
17. Do NOT rewrite or "improve" the existing text. Only wrap existing phrases in <a> \
tags. The surrounding text must remain EXACTLY as provided.
18. **Banned AI vocabulary**: never use delve, crucial, pivotal, landscape (figurative), \
tapestry, vibrant, intricate, foster, garner, underscore, showcase, testament, \
enduring, enhance, align with, resonate with, groundbreaking, renowned, encompass.

### GSC data awareness
19. **Prioritize pages with position 4-15** — they benefit most from link equity.
20. **Use GSC top queries as relevance signals** — overlapping queries indicate semantic fit.
21. **GSC data is supplementary** — proceed with semantic relevance if no GSC data.

## Output format

Return TWO sections separated by the exact marker `---REPORT---`:

1. **Modified HTML**: The full HTML content with <a> tags inserted. Start IMMEDIATELY \
with the HTML (no preamble, no analysis).
2. **JSON report**: A JSON array where each element has:
   - `anchor_text`: the linked text
   - `target_url`: the target URL
   - `reasoning`: brief explanation

Example:
```
<h2>Our Bra Collection</h2>
<p>Discover our range of <a href="/collections/push-up-bras" title="Shop push-up bras">push-up bras</a> \
designed for comfort and support.</p>
---REPORT---
[{"anchor_text": "push-up bras", "target_url": "/collections/push-up-bras", "reasoning": "Direct subcategory link"}]
```
"""


def build_plp_system_prompt(brand_guidelines: str | None = None) -> str:
    """Build PLP system prompt, optionally prepending brand guidelines."""
    parts = []
    if brand_guidelines:
        parts.append(
            "## Brand & Content Guidelines\n\n"
            + brand_guidelines
            + "\n\n---\n\n"
        )
    parts.append(PLP_SYSTEM_PROMPT)
    return "".join(parts)


def build_plp_user_prompt(
    html_content: str,
    candidate_pages: list[TargetPage],
    current_url: str | None = None,
    max_links: int = 5,
    target_keyword: str | None = None,
    related_keywords: str | None = None,
) -> str:
    """Build the user prompt for PLP HTML link injection."""
    parts = []

    if current_url:
        parts.append(f"**Current page URL** (do NOT link to this): {current_url}\n")

    parts.append(f"**Maximum links to insert**: {max_links}\n")

    if target_keyword:
        parts.append(f"**Target keyword for this PLP**: {target_keyword}\n")
    if related_keywords:
        parts.append(f"**Related keywords**: {related_keywords}\n")

    parts.append("## Candidate target pages\n")
    for i, page in enumerate(candidate_pages, 1):
        line = f"{i}. {page.url}"
        if page.title:
            line += f"\n   Title: {page.title}"
        if page.meta_description:
            line += f"\n   Description: {page.meta_description}"
        if page.impressions > 0:
            line += f"\n   GSC: {page.impressions:,} impressions, {page.clicks:,} clicks, avg position {page.avg_position:.1f}"
            if page.top_queries:
                line += f"\n   Top queries: {', '.join(page.top_queries[:5])}"
        parts.append(line)

    parts.append("\n## HTML content to process\n")
    parts.append(f"```html\n{html_content}\n```")

    return "\n".join(parts)
