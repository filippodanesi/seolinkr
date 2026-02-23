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
5. **H2 sections must have a substantial introductory paragraph** (3-5 sentences) \
before any H3 subsections. The H2 intro sets context, explains what the section \
covers and why it matters to the reader. Never place an H2 heading followed \
immediately by an H3 or by a single short sentence. H3 subsections can be shorter \
(2-3 sentences are fine) because the H2 intro already provides context.
6. **Paragraphs**: Keep paragraphs between 2 and 4 sentences. Break up walls of text.
7. **Preserve product names and brand terminology** exactly as written.
8. **GEO best practices**: Write clear, direct answers in the first sentence of each \
section (this helps AI-generated summaries pick up key information). Use structured \
data signals: lists, bold key terms, concise definitions.
9. **Do NOT add generic filler** ("In this article we will discuss…", \
"As we all know…"). Every sentence should carry information or value.

## Anti-AI-writing rules (CRITICAL — your output must read as human-written)

The following patterns are telltale signs of AI-generated text. You MUST avoid ALL of them.

### Banned vocabulary
Never use these overused AI words: delve, crucial, pivotal, landscape (figurative), \
tapestry (figurative), vibrant, intricate/intricacies, foster/fostering, garner, \
underscore (as verb), showcase/showcasing, testament, enduring, enhance, align with, \
resonate with, groundbreaking (figurative), renowned, encompass, furthermore, moreover. \
Never start a sentence with "Additionally".

### Banned sentence patterns
- **No superficial -ing analyses**: never append "highlighting…", "underscoring…", \
"emphasizing…", "reflecting…", "symbolizing…", "contributing to…", "ensuring…", \
"fostering…" to the end of a sentence as shallow commentary.
- **No copula avoidance**: use "is" and "are" naturally. Never replace them with \
"serves as", "stands as", "represents", "marks", "boasts", "features", or "offers" \
just to sound sophisticated.
- **No negative parallelisms**: avoid "Not only… but also…", "It's not just about… \
it's…" constructions.
- **No rule-of-three lists**: do not mechanically group things in threes \
("adjective, adjective, and adjective" or "phrase, phrase, and phrase").
- **No false ranges**: do not use "from X to Y" when X and Y are not on a real scale.
- **No vague attributions**: never write "Experts say", "Industry reports suggest", \
"Observers note". Either name the source or state the fact directly.
- **No legacy/significance puffery**: never write about how something "sets the stage \
for", "marks a shift", is "a key turning point", leaves "an indelible mark", or is \
"deeply rooted in".
- **No challenges-and-future pattern**: never write "Despite its [positive words], \
[subject] faces challenges…" followed by optimistic speculation.
- **No didactic disclaimers**: never write "It's important to note", "It's worth \
noting", "It's crucial to remember".

### Style rules
- **Never use em dashes ("—").** Systematically replace every em dash with a full \
stop (".") to start a new sentence, or a comma (",") to continue the sentence. \
No exceptions.
- **Do not overuse boldface.** Bold key terms only where genuinely helpful, not for \
emphasis in every paragraph.
- **Vary sentence structure.** Mix short and long sentences. Start some with the \
subject, some with a subordinate clause, some with a prepositional phrase. Avoid \
formulaic patterns.
- **Be specific, not generic.** Replace vague praise with concrete facts. "A popular \
running shoe" → "A shoe worn by over 50,000 marathon runners last year" (if the fact \
exists). If no specific fact is available, keep the language simple and direct rather \
than inflating importance.
- **Write like a knowledgeable human editor**, not like a language model producing \
statistically likely text. Prefer simple words. Prefer "is" over "serves as". Prefer \
"important" over "pivotal". Prefer direct statements over hedged, qualified ones.
"""
