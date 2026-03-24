# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Convert linked markdown to Page Designer styled HTML TXT (Desktop & Mobile)."""

from __future__ import annotations

import re
from typing import Literal

_FF = "var(--highlightFont, var(--baseFont))"
_HR = '<hr style="border: none; border-top: 1px solid black; margin: 16px 0;">'

_SIZES = {
    "desktop": {"h2": "32px", "h3": "24px", "h2_mt": "32px", "h3_mt": "32px", "table_width": "50%"},
    "mobile": {"h2": "24px", "h3": "20px", "h2_mt": "20px", "h3_mt": "20px", "table_width": "100%"},
}

_KEY_TAKEAWAYS = {"Key Takeaways", "Die wichtigsten Erkenntnisse"}


def markdown_to_pagedesigner(
    markdown: str,
    variant: Literal["desktop", "mobile"],
    seo_title: str = "",
    seo_meta_description: str = "",
    tldr_text: str = "",
) -> str:
    """Convert linked markdown to Page Designer richtext components (TXT)."""
    sizes = _SIZES[variant]

    # Parse H2 sections
    sections = _parse_h2_sections(markdown.strip())

    # Filter out Key Takeaways, but preserve any trailing italic note (e.g. *Written by...*)
    filtered = []
    trailing_em = ""
    for s in sections:
        if s["heading"] in _KEY_TAKEAWAYS:
            # Check if last paragraph in body is italic text (*...*)
            if s["body"]:
                paragraphs = [p.strip() for p in s["body"].split("\n\n") if p.strip()]
                if paragraphs and re.match(r"^\*[^*]", paragraphs[-1]):
                    trailing_em = paragraphs[-1]
            continue
        filtered.append(s)
    # trailing_em is appended after all article sections (see below)

    # Collect H2 headings for TOC (exclude Key Takeaways)
    h2_entries = [(s["heading"], s["slug"]) for s in filtered if s["heading"]]

    # --- Build section components, separating H1 from article body ---
    h1_component = None
    preamble_components: list[tuple[str, str]] = []
    article_components: list[tuple[str, str]] = []

    section_num = 0
    for sec in filtered:
        if not sec["heading"]:
            # Preamble (contains H1)
            if sec["body"]:
                for label, html in _convert_body(sec["body"], sizes):
                    if label == "H1":
                        h1_component = ("H1", html)
                    else:
                        preamble_components.append((label, html))
        elif sec["heading"].rstrip("s") == "FAQ":
            # FAQ section → accordion
            section_num += 1
            h2_html = _make_h2(sec, section_num, sizes)
            article_components.append(
                (f"H2 - Section {section_num}: {sec['heading']}", h2_html)
            )
            if sec["body"]:
                article_components.append(
                    ("BODY", _convert_faq_accordion(sec["body"]))
                )
        else:
            # Normal H2 section
            section_num += 1
            h2_html = _make_h2(sec, section_num, sizes)
            article_components.append(
                (f"H2 - Section {section_num}: {sec['heading']}", h2_html)
            )
            if sec["body"]:
                article_components.extend(_convert_body(sec["body"], sizes))

    # --- Append trailing <em> note extracted from Key Takeaways ---
    if trailing_em:
        em_html = _inline(trailing_em)
        article_components.append(("BODY", em_html))

    # --- Restyle final <em> ---
    for i in range(len(article_components) - 1, -1, -1):
        label, html = article_components[i]
        if "<em>" in html or "<em " in html:
            html = re.sub(
                r"<em(?:\s[^>]*)?>",
                '<em style="font-size: 14px; color: #666;">',
                html,
            )
            article_components[i] = (label, html)
            break

    # --- Insert <hr> before final <em> block ---
    for i in range(len(article_components) - 1, -1, -1):
        _, html = article_components[i]
        if '<em style="font-size: 14px; color: #666;">' in html:
            article_components.insert(i, ("_HR", _HR))
            break

    # --- Assemble final ordered components ---
    components: list[tuple[str, str]] = []

    # 1. METADATA
    if seo_title or seo_meta_description:
        meta_lines = []
        if seo_title:
            meta_lines.append(f"Title: {seo_title}")
        if seo_meta_description:
            meta_lines.append(f"Meta Description: {seo_meta_description}")
        components.append(("METADATA", "\n".join(meta_lines)))

    # 2. H1
    if h1_component:
        components.append(h1_component)

    # 3. TL;DR
    if tldr_text:
        components.append((
            "BODY",
            f'<p style="font-size: 14px; color: #666; line-height: 1.6;">'
            f"<strong>TL;DR:</strong> {tldr_text}</p>",
        ))

    # 4. <hr> after TL;DR / before TOC
    if tldr_text or len(h2_entries) > 1:
        components.append(("_HR", _HR))

    # 5. TOC
    if len(h2_entries) > 1:
        components.append(("TABLE OF CONTENTS", _build_toc(h2_entries, sizes)))

    # 6. <hr> after TOC
    if len(h2_entries) > 1:
        components.append(("_HR", _HR))

    # 7. Preamble body (non-H1 blocks from intro)
    components.extend(preamble_components)

    # 8. Article body sections (includes <hr> before final <em>)
    components.extend(article_components)

    return _format_output(components)


def _make_h2(sec: dict, section_num: int, sizes: dict) -> str:
    """Build an H2 tag with margin-top."""
    return (
        f'<h2 id="{sec["slug"]}" style="font-weight:400; '
        f'font-size:{sizes["h2"]}; margin-top: {sizes["h2_mt"]}; '
        f'font-family: {_FF};">'
        f"{_inline(sec['heading'])}</h2>"
    )


# -- Parsing -----------------------------------------------------------------


def _parse_h2_sections(md: str) -> list[dict]:
    """Split markdown into sections by ## headings."""
    parts = re.split(r"\n(?=## )", md)
    sections: list[dict] = []
    for part in parts:
        lines = part.split("\n", 1)
        m = re.match(r"^## (.+)", lines[0])
        if m:
            heading = m.group(1).strip()
            body = lines[1].strip() if len(lines) > 1 else ""
            sections.append(
                {"heading": heading, "slug": _slugify(heading), "body": body}
            )
        else:
            body = part.strip()
            if body:
                sections.append({"heading": "", "slug": "", "body": body})
    return sections


def _slugify(text: str) -> str:
    """Create a URL-friendly slug from heading text."""
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug.strip("-")


# -- Body conversion --------------------------------------------------------


def _convert_body(body: str, sizes: dict) -> list[tuple[str, str]]:
    """Convert section body markdown into Page Designer components."""
    blocks = [b.strip() for b in body.split("\n\n") if b.strip()]

    # Classify blocks
    classified: list[tuple[str, str]] = []
    for block in blocks:
        if block.startswith("### "):
            # H3 heading — may have content on subsequent lines
            h3_lines = block.split("\n", 1)
            heading = re.sub(r"^###\s+", "", h3_lines[0])
            classified.append(("h3", heading))
            if len(h3_lines) > 1 and h3_lines[1].strip():
                classified.append(("text", h3_lines[1].strip()))
        elif block.startswith("# ") and not block.startswith("## "):
            # H1 heading
            classified.append(("h1", block))
        elif "|" in block and block.strip().startswith("|"):
            classified.append(("table", block))
        elif all(
            re.match(r"^[-*]\s+", ln) for ln in block.split("\n") if ln.strip()
        ):
            classified.append(("list", block))
        elif all(
            re.match(r"^\d+\.\s+", ln)
            for ln in block.split("\n")
            if ln.strip()
        ):
            classified.append(("list", block))
        else:
            classified.append(("text", block))

    # Group items: intro (before first H3) + H3 sections (each H3 with its content)
    groups: list[tuple[str, list[tuple[str, str]]]] = []
    current: list[tuple[str, str]] = []
    current_type = "intro"

    for typ, content in classified:
        if typ == "h3":
            if current:
                groups.append((current_type, current))
            current = [(typ, content)]
            current_type = "h3"
        else:
            current.append((typ, content))

    if current:
        groups.append((current_type, current))

    # Convert groups to BODY components
    components: list[tuple[str, str]] = []

    for group_type, items in groups:
        if group_type == "intro":
            # Each intro item gets its own BODY block
            for typ, content in items:
                if typ == "table":
                    components.append(
                        ("BODY", _table_to_html(content, sizes["table_width"]))
                    )
                elif typ == "h1":
                    components.append(("H1", _block_to_html(content, sizes)))
                elif typ == "list":
                    components.append(
                        ("BODY - List", _block_to_html(content, sizes))
                    )
                else:
                    components.append(("BODY", _block_to_html(content, sizes)))
        else:
            # H3 section: heading + all following content in one BODY block
            html_parts: list[str] = []
            for typ, content in items:
                if typ == "h3":
                    html_parts.append(
                        f'<h3 style="font-weight:400; font-size:{sizes["h3"]}; '
                        f'line-height:40px; margin-top: {sizes["h3_mt"]}; margin-bottom: 12px; '
                        f'font-family: {_FF};">'
                        f"{_inline(content)}</h3>"
                    )
                elif typ == "table":
                    html_parts.append(
                        _table_to_html(content, sizes["table_width"])
                    )
                elif typ == "list":
                    html_parts.append(_block_to_html(content, sizes))
                elif typ == "h1":
                    html_parts.append(_block_to_html(content, sizes))
                else:
                    html_parts.append(
                        f"<p>{_block_to_html(content, sizes)}</p>"
                    )
            components.append(("BODY", "".join(html_parts)))

    return components


# -- FAQ accordion -----------------------------------------------------------


def _convert_faq_accordion(body: str) -> str:
    """Convert FAQ section body markdown into <details>/<summary> accordion HTML."""
    blocks = [b.strip() for b in body.split("\n\n") if b.strip()]
    parts: list[str] = []
    for block in blocks:
        lines = block.split("\n", 1)
        # Question line: **Q: question** or **question**
        q_match = re.match(r"\*\*(?:[QF]:\s*)?(.+?)\*\*", lines[0])
        if not q_match:
            continue
        question = _inline(q_match.group(1).strip())
        # Answer: rest of first line after ** + subsequent lines
        answer_start = lines[0][q_match.end():].strip()
        answer_rest = lines[1].strip() if len(lines) > 1 else ""
        answer = (answer_start + " " + answer_rest).strip() if answer_start else answer_rest
        answer = re.sub(r"^[A]:\s*", "", answer)
        answer = _inline(answer)
        parts.append(
            '<details style="margin-bottom: 8px; border-bottom: 1px solid #eee; '
            'padding-bottom: 8px;"><summary style="cursor: pointer; font-weight: '
            'bold; font-size: 16px; padding: 8px 0;">'
            f"{question}</summary><p style=\"margin: 8px 0 0 0; font-size: 15px; "
            f'color: #444;">{answer}</p></details>'
        )
    return "\n".join(parts)


# -- Inline text processing --------------------------------------------------


def _inline(text: str) -> str:
    """Convert ALL inline markdown to HTML."""
    # Convert markdown links [text](url "title") or [text](url) to <a> tags
    def _link_replace(m: re.Match) -> str:
        anchor = m.group(1)
        raw = m.group(2).strip()
        # Check for optional title: url "title" or url 'title'
        title_match = re.match(r"""^(\S+)\s+["'](.+?)["']$""", raw)
        if title_match:
            url = title_match.group(1)
            title = title_match.group(2)
            return f'<a href="{url}" title="{title}">{anchor}</a>'
        return f'<a href="{raw}">{anchor}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link_replace, text)
    # Convert **bold** to <strong> (must come before *italic*)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Convert *italic* to <em>
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    return text


def _block_to_html(block: str, sizes: dict) -> str:
    """Convert a full block of markdown text to HTML, handling all elements."""
    lines = block.split("\n")

    # Check if entire block is a bullet list
    if all(re.match(r"^[-*]\s+", ln) for ln in lines if ln.strip()):
        return _list_to_html(lines, ordered=False)

    # Check if entire block is a numbered list
    if all(re.match(r"^\d+\.\s+", ln) for ln in lines if ln.strip()):
        return _list_to_html(lines, ordered=True)

    # Check for H1 heading
    h1_match = re.match(r"^#\s+(.+)", block)
    if h1_match:
        heading = h1_match.group(1).strip()
        return (
            f'<h1 style="font-weight:400; font-family: {_FF};">'
            f"{_inline(heading)}</h1>"
        )

    # Regular text block — convert inline markdown
    return _inline(block)


def _list_to_html(lines: list[str], ordered: bool = False) -> str:
    """Convert markdown list lines to HTML <ul> or <ol>."""
    tag = "ol" if ordered else "ul"
    items: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        # Strip bullet/number prefix
        text = re.sub(r"^[-*]\s+", "", line) if not ordered else re.sub(r"^\d+\.\s+", "", line)
        items.append(f"<li>{_inline(text.strip())}</li>")
    return f"<{tag}>{''.join(items)}</{tag}>"


# -- Table conversion --------------------------------------------------------


def _table_to_html(md_table: str, width: str) -> str:
    """Convert a markdown table to styled HTML table."""
    lines = [ln.strip() for ln in md_table.strip().split("\n") if ln.strip()]
    if len(lines) < 2:
        return _inline(md_table)

    th_style = (
        "border: 1px solid #ccc; padding: 8px; "
        "font-weight: bold; text-align: left;"
    )
    td_style = "border: 1px solid #ccc; padding: 8px;"

    # Header row
    header_cells = [c.strip() for c in lines[0].strip("|").split("|")]
    thead = (
        "<thead><tr>"
        + "".join(f'<th style="{th_style}">{_inline(c)}</th>' for c in header_cells)
        + "</tr></thead>"
    )

    # Skip separator row (line 1), process data rows
    tbody_rows: list[str] = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        row = "<tr>" + "".join(
            f'<td style="{td_style}">{_inline(c)}</td>' for c in cells
        ) + "</tr>"
        tbody_rows.append(row)
    tbody = "<tbody>" + "".join(tbody_rows) + "</tbody>"

    return (
        f'<table style="border-collapse: collapse; width: {width};">'
        f"{thead}{tbody}</table>"
    )


# -- TOC ---------------------------------------------------------------------


def _build_toc(entries: list[tuple[str, str]], sizes: dict) -> str:
    """Build Table of Contents HTML component."""
    items: list[str] = []
    for i, (text, slug) in enumerate(entries, 1):
        items.append(
            f'<li style="display: flex; gap: 6px; justify-content:center;">'
            f"<span>{i}.</span>"
            f'<a style="text-decoration: none;" href="#{slug}">{text}</a>'
            f"</li>"
        )
    ol = (
        '<ol style="list-style:none; display:flex; flex-direction: column; '
        f'gap: 8px; font-family: {_FF}; align-items:flex-start; '
        f'padding-left: 0px;">'
        + "".join(items)
        + "</ol>"
    )
    h2 = (
        f'<h2 id="toc" style="font-weight:400; font-size:{sizes["h2"]}; '
        f'margin-top: {sizes["h2_mt"]}; font-family: {_FF};">Table of Contents</h2>'
    )
    return h2 + ol


# -- Output formatting -------------------------------------------------------


def _format_output(components: list[tuple[str, str]]) -> str:
    """Format components into the final TXT output with HTML comment separators."""
    parts: list[str] = []
    for label, html in components:
        if label == "_HR":
            parts.append(html)
        else:
            parts.append(f"<!-- {label} -->")
            parts.append(html)
    return "\n".join(parts)
