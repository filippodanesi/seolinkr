# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Convert linked markdown to Page Designer styled HTML TXT (Desktop & Mobile)."""

from __future__ import annotations

import re
from typing import Literal

_FF = "var(--highlightFont, var(--baseFont))"

_SIZES = {
    "desktop": {"h2": "32px", "h3": "24px", "table_width": "50%"},
    "mobile": {"h2": "24px", "h3": "20px", "table_width": "100%"},
}


def markdown_to_pagedesigner(
    markdown: str,
    variant: Literal["desktop", "mobile"],
) -> str:
    """Convert linked markdown to Page Designer richtext components (TXT)."""
    sizes = _SIZES[variant]

    # Parse H2 sections
    sections = _parse_h2_sections(markdown.strip())

    # Collect H2 headings for TOC
    h2_entries = [(s["heading"], s["slug"]) for s in sections if s["heading"]]

    components: list[tuple[str, str]] = []

    # TOC
    if len(h2_entries) > 1:
        components.append(("Table of Contents", _build_toc(h2_entries, sizes)))

    # Process each section
    for sec in sections:
        if sec["heading"]:
            h2_html = (
                f'<h2 id="{sec["slug"]}" style="font-weight:400; '
                f'font-size:{sizes["h2"]}; font-family: {_FF};">'
                f"{_inline(sec['heading'])}</h2>"
            )
            components.append(("H2", h2_html))

        if sec["body"]:
            body_parts = _convert_body(sec["body"], sizes)
            components.extend(body_parts)

    return _format_output(components)


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
        elif "|" in block and block.strip().startswith("|"):
            classified.append(("table", block))
        else:
            classified.append(("text", block))

    # Find boundary: structured part (intro + H3s + their content) vs trailing
    last_structured = -1
    after_h3 = False
    for i, (typ, _) in enumerate(classified):
        if typ == "h3":
            last_structured = i
            after_h3 = True
        elif typ == "table":
            last_structured = i
            after_h3 = False
        elif after_h3:
            # First text block after an H3 belongs to structured part
            last_structured = i
            after_h3 = False

    if last_structured >= 0:
        structured = classified[: last_structured + 1]
        trailing = classified[last_structured + 1 :]
    else:
        structured = []
        trailing = classified

    components: list[tuple[str, str]] = []

    # Build structured HTML component
    if structured:
        html_parts: list[str] = []
        first_h3_seen = False
        has_table = False

        for typ, content in structured:
            if typ == "text" and not first_h3_seen:
                # Intro text — no wrapping
                html_parts.append(_inline(content))
            elif typ == "h3":
                if not first_h3_seen:
                    html_parts.append("<br>")
                    first_h3_seen = True
                html_parts.append(
                    f'<h3 style="font-weight:400; font-size:{sizes["h3"]}; '
                    f'line-height:40px; font-family: {_FF};">'
                    f"{_inline(content)}</h3>"
                )
            elif typ == "text":
                html_parts.append(f"<p>{_inline(content)}</p>")
            elif typ == "table":
                has_table = True
                html_parts.append(
                    _table_to_html(content, sizes["table_width"])
                )
                html_parts.append("<br>")

        if has_table:
            label = "Contains table and body text"
        elif first_h3_seen:
            label = "Normal body text with p and H3 tags"
        else:
            label = "Body text"
        components.append((label, "".join(html_parts)))

    # Trailing plain text components
    for typ, content in trailing:
        if typ == "table":
            components.append(
                ("Table", _table_to_html(content, sizes["table_width"]))
            )
        else:
            components.append(("Body text", _inline(content)))

    return components


# -- Inline text processing --------------------------------------------------


def _inline(text: str) -> str:
    """Process inline markdown: links, bold."""
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
    # Convert **bold** to <strong>
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return text


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
        f'font-family: {_FF};">Table of Contents</h2>'
    )
    return h2 + ol


# -- Output formatting -------------------------------------------------------


def _format_output(components: list[tuple[str, str]]) -> str:
    """Format components into the final TXT output."""
    parts: list[str] = []
    for i, (label, html) in enumerate(components):
        if i > 0:
            parts.append("=" * 60)
        parts.append(label)
        parts.append("")
        parts.append(html)
        parts.append("")
    return "\n".join(parts)
