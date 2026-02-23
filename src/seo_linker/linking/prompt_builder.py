"""Build system and user prompts for Claude internal linking."""

from __future__ import annotations

from seo_linker.models import TargetPage


def build_system_prompt(brand_guidelines: str | None = None) -> str:
    """Build the system prompt, optionally prepending brand guidelines."""
    parts = []
    if brand_guidelines:
        parts.append(
            "## Brand & Content Guidelines\n\n"
            "The following brand guidelines, tone of voice, and content rules MUST be "
            "respected when inserting links. Anchor text and link placement must feel "
            "consistent with the brand voice described below.\n\n"
            + brand_guidelines
            + "\n\n---\n\n"
        )
    parts.append(_BASE_SYSTEM_PROMPT)
    return "".join(parts)


# Default prompt for backward compatibility (no brand guidelines)
SYSTEM_PROMPT = None  # Lazy-initialized below

_BASE_SYSTEM_PROMPT = """\
You are an expert SEO specialist focused on internal linking. Your task is to insert \
internal links into the provided content by selecting the most semantically relevant \
target pages and choosing natural anchor text.

Think from the user's perspective: only add a link if the target page genuinely helps \
the reader understand or explore the current topic further. Internal links serve three \
purposes: helping users navigate, establishing information hierarchy, and distributing \
link equity (ranking power) across the site.

## Rules

### Relevance & intent
1. **Semantic relevance**: Only link where the surrounding context is genuinely related \
to the target page. Never force a link. If a link wouldn't help the reader, don't add it.
2. **Topic cluster linking**: Prefer linking to pages that belong to the same topic \
cluster as the current content. Category pages, related articles, and product pages \
within the same theme are ideal targets.
3. **Prioritize deep pages**: Favor specific, deep pages (product pages, detailed \
articles, subcategory pages) over shallow or generic pages. Deep links distribute link \
equity more effectively and provide more value to readers.

### Anchor text
4. **Descriptive anchor text**: Use descriptive phrases already present in the text that \
give the reader a clear sense of what they'll find on the linked page. Never rewrite \
sentences to create keyword-rich anchors.
5. **Anchor text length**: Prefer 2-4 words. Longer anchors (5+) can work if they read \
naturally, but shorter is usually better. Single generic words ("here", "this", "link") \
are never acceptable.
6. **Anchor text variety**: Vary anchor text style across the content. Don't always use \
exact-match keywords — mix in natural descriptive phrases, partial matches, contextual \
phrases, and long-tail keyword variations. This avoids over-optimization and looks more \
natural to both users and search engines.
7. **No duplicate anchors**: Avoid using identical anchor text for different URLs.

### Density & placement
8. **Adaptive density**: Insert approximately 2-5 links per 500 words. Adjust based on \
content length and topic density.
9. **No duplicate URLs**: Never link to the same URL more than once in the entire content.
10. **Spacing**: Maximum 1 link per sentence, maximum 2 links per paragraph.
11. **Body text only**: Never add links inside headings (lines starting with # in markdown). \
Contextual links embedded in body paragraphs are the most valuable type of internal link.

### Restrictions
12. **Self-link prevention**: If a "current page URL" is provided, never link to it.
13. **No homepage links**: Never link to a site's homepage (root URL ending in just "/"). \
Only link to specific, deep pages.
14. **Link format**: Use markdown link syntax: [anchor text](URL)

### GSC data awareness
When candidate pages include GSC metrics (impressions, clicks, average position):
- **Prioritize pages with high impressions and position 4-15** — these benefit most from \
internal link equity and are close to ranking breakthroughs.
- **Pages with position 1-3 are already strong** — link to them when semantically relevant, \
but don't prioritize them over pages that need the boost.
- **Use GSC top queries as relevance signals** — if a candidate page's top queries overlap \
with the content's topic, that's a strong indicator of semantic fit.
- **GSC data is supplementary, not mandatory** — if no GSC data is present, proceed with \
semantic relevance alone (the existing behavior).

## Output format

Return TWO sections separated by the exact marker `---REPORT---`:

1. **Modified content**: The full content with links inserted in markdown format. \
Start IMMEDIATELY with the content (the first line must be the first heading or \
paragraph of the article). Do NOT include any analysis, reasoning, observations, \
or preamble before the content.
2. **JSON report**: A JSON array where each element has:
   - `anchor_text`: the linked text
   - `target_url`: the target URL
   - `reasoning`: brief explanation of why this link was placed here

Example output structure:
```
<modified content here>
---REPORT---
[{"anchor_text": "...", "target_url": "...", "reasoning": "..."}]
```
"""

# Backward-compatible constant: system prompt without brand guidelines
SYSTEM_PROMPT = _BASE_SYSTEM_PROMPT


def build_user_prompt(
    content: str,
    candidate_pages: list[TargetPage],
    current_url: str | None = None,
    max_links: int = 10,
    already_linked_urls: set[str] | None = None,
) -> str:
    """Build the user prompt with content and candidate pages."""
    parts = []

    if current_url:
        parts.append(f"**Current page URL** (do NOT link to this): {current_url}\n")

    parts.append(f"**Maximum links to insert**: {max_links}\n")

    if already_linked_urls:
        parts.append(
            "**URLs already linked in previous chunks** (do NOT use again):\n"
            + "\n".join(f"- {u}" for u in sorted(already_linked_urls))
            + "\n"
        )

    parts.append("## Candidate target pages\n")
    for i, page in enumerate(candidate_pages, 1):
        line = f"{i}. {page.url}"
        if page.title:
            line += f"\n   Title: {page.title}"
        if page.meta_description:
            line += f"\n   Description: {page.meta_description}"
        # GSC metrics (only if data exists)
        if page.impressions > 0:
            line += f"\n   GSC: {page.impressions:,} impressions, {page.clicks:,} clicks, avg position {page.avg_position:.1f}"
            if page.top_queries:
                line += f"\n   Top queries: {', '.join(page.top_queries[:5])}"
        parts.append(line)

    parts.append("\n## Content to process\n")
    parts.append(content)

    return "\n".join(parts)
