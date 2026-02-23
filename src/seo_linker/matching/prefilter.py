"""Pre-filter target pages using cosine similarity with content embeddings."""

from __future__ import annotations

import numpy as np

from urllib.parse import urlparse

from seo_linker.matching.embeddings import encode_texts
from seo_linker.models import ContentSection, TargetPage


def prefilter_pages(
    sections: list[ContentSection],
    pages: list[TargetPage],
    top_n: int = 25,
    model_name: str = "intfloat/multilingual-e5-small",
) -> list[TargetPage]:
    """Return the top-N most relevant pages based on embedding similarity."""
    # Filter out homepages (root URLs with no meaningful path)
    pages = [p for p in pages if urlparse(p.url).path.strip("/")]

    if len(pages) <= top_n:
        return pages

    # Build content text (query) and page texts (passages)
    content_text = " ".join(s.text for s in sections)
    page_texts = [p.embedding_text for p in pages]

    # E5 models require "query: " / "passage: " prefixes
    is_e5 = "e5" in model_name.lower()
    query_prefix = "query: " if is_e5 else ""
    passage_prefix = "passage: " if is_e5 else ""

    # Encode query and passages separately with correct prefixes
    query_emb = encode_texts([query_prefix + content_text], model_name)[0]
    passage_embs = encode_texts(
        [passage_prefix + t for t in page_texts], model_name
    )

    # Cosine similarity
    scores = _cosine_similarity(query_emb, passage_embs)

    # Get top-N indices
    top_indices = np.argsort(scores)[::-1][:top_n]
    return [pages[i] for i in top_indices]


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
