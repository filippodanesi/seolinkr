"""Build system and user prompts for content rewriting/optimization."""

from __future__ import annotations


def build_rewrite_system_prompt(
    brand_guidelines: str | None = None,
    content_type: str = "existing_article",
    custom_instructions: str | None = None,
) -> str:
    """Build the system prompt for content rewriting.

    Parameters
    ----------
    brand_guidelines:
        Brand guidelines markdown text (tone of voice, style, etc.).
    content_type:
        ``"existing_article"`` — optimize an already-written article.
        ``"rough_draft"`` — expand and structure a rough draft into a full article.
    custom_instructions:
        Optional free-text instructions from the user appended to the prompt.
    """
    parts: list[str] = []

    # Brand guidelines block
    if brand_guidelines:
        parts.append(
            "## Brand & Content Guidelines\n\n"
            "You MUST follow these brand guidelines for tone of voice, terminology, "
            "and style when rewriting the content.\n\n"
            + brand_guidelines
            + "\n\n---\n\n"
        )

    # Content-type-specific behaviour
    if content_type == "rough_draft":
        parts.append(_ROUGH_DRAFT_PREAMBLE)
    else:
        parts.append(_EXISTING_ARTICLE_PREAMBLE)

    # Shared rules (always appended)
    parts.append(_SHARED_RULES)

    # Custom user instructions
    if custom_instructions:
        parts.append(
            "\n\n## Additional Instructions\n\n"
            + custom_instructions
        )

    return "".join(parts)


def build_rewrite_user_prompt(
    content: str,
    previous_headings: list[str] | None = None,
) -> str:
    """Build the user prompt containing the content to rewrite.

    Parameters
    ----------
    content:
        The markdown content (or chunk) to rewrite.
    previous_headings:
        Headings from earlier chunks, used for inter-chunk context.
    """
    parts: list[str] = []

    if previous_headings:
        parts.append(
            "**Context — previous sections already covered these topics** "
            "(do NOT repeat them, only continue from where they left off):\n"
            + "\n".join(f"- {h}" for h in previous_headings)
            + "\n\n"
        )

    parts.append("## Content to rewrite\n\n")
    parts.append(content)

    return "".join(parts)


# ---------------------------------------------------------------------------
# Prompt fragments
# ---------------------------------------------------------------------------

_EXISTING_ARTICLE_PREAMBLE = """\
You are an expert content editor and SEO copywriter. Your task is to **optimize \
an existing article**. Improve readability, structure, tone of voice, and GEO \
(Generative Engine Optimization) signals while preserving the original meaning \
and information.

### What to do
- Improve sentence clarity and flow.
- Restructure paragraphs so each is 2-4 sentences.
- Convert flat headings into **question-style headings** where appropriate (e.g. \
"How to choose the right running shoe?" instead of "Choosing a running shoe").
- Add a short, engaging introduction if the article lacks one.
- Ensure a clear conclusion or summary paragraph at the end.
- Preserve all factual claims, product names, and data points.

"""

_ROUGH_DRAFT_PREAMBLE = """\
You are an expert content editor and SEO copywriter. Your task is to **expand and \
structure a rough draft** into a complete, publication-ready article. The input may \
be bullet points, notes, or a partial draft.

### What to do
- Expand bullet points and notes into full, well-structured paragraphs (2-4 sentences each).
- Create a logical article structure with clear headings.
- Use **question-style headings** where appropriate (e.g. "What makes a great trail \
running shoe?" instead of "Trail running shoes").
- Write a compelling introduction that hooks the reader.
- Write a conclusion or summary section.
- Fill in transitional sentences between sections for editorial flow.
- Preserve all factual claims, product names, and data points from the draft.

"""

_SHARED_RULES = """\
## Output rules

1. **Output ONLY the rewritten markdown content.** No preamble, no explanation, \
no analysis, no "Here is the rewritten article:" — start IMMEDIATELY with the first \
heading or paragraph of the article. The very first line of your response must be content.
2. **Do NOT insert any links.** No markdown links, no URLs in the text. Links will \
be added in a separate step.
3. **Maintain the original language.** If the input is in German, write in German. \
If in Italian, write in Italian. Never translate.
4. **Heading structure**: Use H2 (`##`) for main sections and H3 (`###`) for \
subsections. Never use H1 (`#`) — that is reserved for the page title which is \
handled separately.
5. **Paragraphs**: Keep paragraphs between 2 and 4 sentences. Break up walls of text.
6. **Preserve product names and brand terminology** exactly as written.
7. **GEO best practices**: Write clear, direct answers in the first sentence of each \
section (this helps AI-generated summaries pick up key information). Use structured \
data signals: lists, bold key terms, concise definitions.
8. **Do NOT add generic filler** ("In this article we will discuss…", \
"As we all know…"). Every sentence should carry information or value.
"""
