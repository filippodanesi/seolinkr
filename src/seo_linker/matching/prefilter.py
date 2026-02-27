# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""Pre-filter target pages using multi-signal scoring.

Combines embedding similarity, URL taxonomy overlap, GSC opportunity
boost, and heading topic coverage for more precise candidate selection.
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from urllib.parse import urlparse

import numpy as np

from seo_linker.matching.embeddings import encode_texts
from seo_linker.models import ContentSection, TargetPage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Multilingual stop words (EN, DE, FR, IT, ES, NL)
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset({
    # English
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "here", "there", "when",
    "where", "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "because", "and", "but",
    "or", "if", "while", "this", "that", "these", "those", "it", "its",
    "he", "she", "they", "them", "their", "we", "our", "you", "your",
    "my", "his", "her", "what", "which", "who", "whom", "about", "also",
    "best", "top", "new", "good", "great", "like", "get", "make",
    # German
    "der", "die", "das", "ein", "eine", "und", "oder", "ist", "sind",
    "für", "mit", "von", "auf", "den", "dem", "des", "sich", "nicht",
    "auch", "wird", "kann", "hat", "wie", "bei", "noch", "nach",
    # French
    "le", "la", "les", "un", "une", "de", "du", "des", "et", "est",
    "pas", "que", "qui", "dans", "pour", "sur", "avec", "plus", "par",
    # Italian
    "il", "lo", "gli", "una", "di", "da", "per", "con", "che", "non",
    "del", "dei", "alla", "sono", "come", "più",
    # Spanish
    "el", "los", "las", "del", "en", "por", "con", "que", "una",
    "para", "más", "como", "pero", "sus",
    # Dutch
    "het", "een", "van", "en", "voor", "met", "op", "aan", "ook",
    "niet", "maar", "wel", "naar",
})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def prefilter_pages(
    sections: list[ContentSection],
    pages: list[TargetPage],
    top_n: int = 25,
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
) -> list[TargetPage]:
    """Return the top-N most relevant pages using multi-signal scoring.

    Signals:
    1. Embedding similarity  (weight: 0.50 / 0.60 without GSC)
    2. URL taxonomy overlap  (weight: 0.20 / 0.25 without GSC)
    3. GSC opportunity boost  (weight: 0.20 / 0.00 without GSC)
    4. Heading topic overlap  (weight: 0.10 / 0.15 without GSC)
    """
    # Filter out homepages (root URLs with no meaningful path)
    pages = [p for p in pages if urlparse(p.url).path.strip("/")]

    if len(pages) <= top_n:
        return pages

    # Extract article keywords once (used by URL taxonomy + heading overlap)
    article_keywords = _extract_article_keywords(sections)

    # --- Signal 1: Embedding similarity (primary) ---
    content_text = " ".join(s.text for s in sections)
    page_texts = [p.embedding_text for p in pages]

    is_e5 = "e5" in model_name.lower()
    query_prefix = "query: " if is_e5 else ""
    passage_prefix = "passage: " if is_e5 else ""

    logger.info("Encoding query embedding (1 text)...")
    t0 = time.time()
    query_emb = encode_texts([query_prefix + content_text], model_name)[0]
    logger.info("Query embedding done in %.1fs", time.time() - t0)

    logger.info("Encoding %d passage embeddings...", len(page_texts))
    t0 = time.time()
    passage_embs = encode_texts(
        [passage_prefix + t for t in page_texts], model_name
    )
    logger.info("Passage embeddings done in %.1fs", time.time() - t0)
    emb_scores = _cosine_similarity(query_emb, passage_embs)

    # Normalize to 0-1
    emb_min, emb_max = emb_scores.min(), emb_scores.max()
    if emb_max > emb_min:
        emb_scores = (emb_scores - emb_min) / (emb_max - emb_min)

    # --- Signal 2: URL taxonomy overlap ---
    url_scores = np.array([
        _url_taxonomy_score(p, article_keywords) for p in pages
    ])

    # --- Signal 3: GSC opportunity boost ---
    has_gsc = any(p.impressions > 0 for p in pages)
    gsc_scores = np.array([p.opportunity_score for p in pages])
    gsc_max = gsc_scores.max()
    if gsc_max > 0:
        gsc_scores = gsc_scores / gsc_max

    # --- Signal 4: Heading topic overlap ---
    heading_scores = np.array([
        _heading_overlap_score(p, article_keywords) for p in pages
    ])

    # --- Weighted combination ---
    if has_gsc:
        final = (
            0.50 * emb_scores
            + 0.20 * url_scores
            + 0.20 * gsc_scores
            + 0.10 * heading_scores
        )
    else:
        final = (
            0.60 * emb_scores
            + 0.25 * url_scores
            + 0.15 * heading_scores
        )

    top_indices = np.argsort(final)[::-1][:top_n]
    return [pages[i] for i in top_indices]


# ---------------------------------------------------------------------------
# Signal helpers
# ---------------------------------------------------------------------------

def _extract_article_keywords(sections: list[ContentSection]) -> set[str]:
    """Extract meaningful keywords from article headings and content."""
    keywords: set[str] = set()

    # Headings are the strongest topic signals
    for s in sections:
        if s.heading:
            for word in s.heading.lower().split():
                cleaned = word.strip("?!.,;:()[]\"'#*")
                if cleaned and len(cleaned) > 2 and cleaned not in _STOP_WORDS:
                    keywords.add(cleaned)

    # Frequent words from body text (top 20)
    word_freq: Counter[str] = Counter()
    for s in sections:
        for word in s.text.lower().split():
            cleaned = word.strip("?!.,;:()[]\"'#*")
            if cleaned and len(cleaned) > 2 and cleaned not in _STOP_WORDS:
                word_freq[cleaned] += 1

    for word, _ in word_freq.most_common(20):
        keywords.add(word)

    return keywords


def _url_taxonomy_score(page: TargetPage, article_keywords: set[str]) -> float:
    """Score URL path token overlap with article keywords."""
    url_tokens = page.url_tokens
    if not url_tokens or not article_keywords:
        return 0.0
    overlap = len(url_tokens & article_keywords)
    return overlap / len(url_tokens)


def _heading_overlap_score(page: TargetPage, article_keywords: set[str]) -> float:
    """Score page heading word overlap with article keywords."""
    if not page.headings or not article_keywords:
        return 0.0
    page_words: set[str] = set()
    for h in page.headings:
        for word in h.lower().split():
            cleaned = word.strip("?!.,;:()[]\"'")
            if cleaned and len(cleaned) > 2 and cleaned not in _STOP_WORDS:
                page_words.add(cleaned)
    if not page_words:
        return 0.0
    # Overlap coefficient (Szymkiewicz-Simpson): intersection / min(|A|, |B|)
    intersection = len(page_words & article_keywords)
    denominator = min(len(page_words), len(article_keywords))
    return intersection / denominator if denominator > 0 else 0.0


# ---------------------------------------------------------------------------
# Math
# ---------------------------------------------------------------------------

def _cosine_similarity(query: np.ndarray, candidates: np.ndarray) -> np.ndarray:
    # Work in float64 to avoid overflow in matmul with float16/bfloat16 embeddings
    query = query.astype(np.float64)
    candidates = candidates.astype(np.float64)

    query_norm = np.linalg.norm(query)
    if query_norm == 0:
        return np.zeros(candidates.shape[0])

    q = query / query_norm
    norms = np.linalg.norm(candidates, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    c = candidates / norms

    # Clean any residual NaN/Inf from degenerate embeddings
    np.nan_to_num(q, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
    np.nan_to_num(c, copy=False, nan=0.0, posinf=0.0, neginf=0.0)

    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        scores = c @ q
    return np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)
