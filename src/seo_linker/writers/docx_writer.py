"""DOCX writer — inserts hyperlinks via python-docx XML manipulation."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from seo_linker.models import LinkingResult
from seo_linker.writers.base import BaseWriter

# Pattern to find markdown links
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


class DocxWriter(BaseWriter):
    def write(self, result: LinkingResult, input_path: Path, output_path: Path) -> None:
        doc = Document(str(input_path))

        # Build a map of original paragraph text -> linked text with replacements
        link_map = _build_link_map(result)

        for para in doc.paragraphs:
            plain = para.text.strip()
            if plain in link_map:
                _replace_paragraph_with_links(para, link_map[plain])

        # Insert SEO metadata block at the top of the document
        if result.seo_title or result.seo_meta_description:
            _insert_seo_metadata(doc, result.seo_title, result.seo_meta_description)

        doc.save(str(output_path))


def _build_link_map(result: LinkingResult) -> dict[str, str]:
    """Map original paragraph text to linked version for paragraphs that changed."""
    orig_paras = result.original_text.split("\n")
    linked_paras = result.linked_text.split("\n")

    mapping: dict[str, str] = {}

    # Try to match paragraphs by position
    orig_clean = [p.strip() for p in orig_paras if p.strip()]
    linked_clean = [p.strip() for p in linked_paras if p.strip()]

    for orig, linked in zip(orig_clean, linked_clean):
        if orig != linked and LINK_RE.search(linked):
            # Strip any existing markdown links from orig for matching
            orig_no_links = LINK_RE.sub(r"\1", orig)
            mapping[orig_no_links] = linked
            mapping[orig] = linked

    return mapping


def _replace_paragraph_with_links(para, linked_text: str) -> None:
    """Replace paragraph content with text containing hyperlinks."""
    # Clear existing runs
    for run in para.runs:
        run.text = ""

    # Remove all existing run and hyperlink elements
    for child in list(para._element):
        if child.tag.endswith("}r") or child.tag.endswith("}hyperlink"):
            para._element.remove(child)

    # Parse the linked text and insert runs + hyperlinks
    last_end = 0
    for match in LINK_RE.finditer(linked_text):
        # Add text before link
        before = linked_text[last_end : match.start()]
        if before:
            _add_run(para, before)

        anchor = match.group(1)
        url = match.group(2)
        _add_hyperlink(para, anchor, url)
        last_end = match.end()

    # Add remaining text
    remaining = linked_text[last_end:]
    if remaining:
        _add_run(para, remaining)


def _add_run(para, text: str) -> None:
    run_el = OxmlElement("w:r")
    text_el = OxmlElement("w:t")
    text_el.text = text
    text_el.set(qn("xml:space"), "preserve")
    run_el.append(text_el)
    para._element.append(run_el)


def _add_hyperlink(para, anchor_text: str, url: str) -> None:
    """Add a hyperlink to a paragraph."""
    part = para.part
    r_id = part.relate_to(url, RT.HYPERLINK, is_external=True)

    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rStyle = OxmlElement("w:rStyle")
    rStyle.set(qn("w:val"), "Hyperlink")
    rPr.append(rStyle)
    run.append(rPr)

    text_el = OxmlElement("w:t")
    text_el.text = anchor_text
    text_el.set(qn("xml:space"), "preserve")
    run.append(text_el)

    hyperlink.append(run)
    para._element.append(hyperlink)


def _insert_seo_metadata(doc: Document, title: str, meta_description: str) -> None:
    """Insert a styled SEO metadata block at the top of the document."""
    body = doc.element.body
    first_child = body[0] if len(body) > 0 else None

    # Build paragraphs to insert (in order: header, title, meta, separator)
    meta_color = RGBColor(0x66, 0x66, 0x66)
    entries: list[tuple[str, bool]] = [
        ("SEO METADATA", True),
        (f"Title: {title}", False),
        (f"Meta Description: {meta_description}", False),
        ("", False),
    ]

    # Insert in reverse so they end up in the correct order at the top
    for text, is_header in reversed(entries):
        p_el = OxmlElement("w:p")

        # Paragraph formatting: add bottom border on the empty separator line
        if not text and not is_header:
            pPr = OxmlElement("w:pPr")
            pBdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "4")
            bottom.set(qn("w:space"), "1")
            bottom.set(qn("w:color"), "999999")
            pBdr.append(bottom)
            pPr.append(pBdr)
            p_el.append(pPr)

        r_el = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")

        if is_header:
            b = OxmlElement("w:b")
            rPr.append(b)
            sz = OxmlElement("w:sz")
            sz.set(qn("w:val"), "20")  # 10pt
            rPr.append(sz)

        # Gray color for all metadata text
        color = OxmlElement("w:color")
        color.set(qn("w:val"), "666666")
        rPr.append(color)

        # Smaller font for non-header lines
        if not is_header and text:
            sz = OxmlElement("w:sz")
            sz.set(qn("w:val"), "18")  # 9pt
            rPr.append(sz)

        r_el.append(rPr)

        t_el = OxmlElement("w:t")
        t_el.text = text
        t_el.set(qn("xml:space"), "preserve")
        r_el.append(t_el)
        p_el.append(r_el)

        if first_child is not None:
            first_child.addprevious(p_el)
        else:
            body.append(p_el)
