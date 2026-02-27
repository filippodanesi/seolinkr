# Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"""HuggingFace Inference API wrapper for generating embeddings."""

from __future__ import annotations

import logging
import os
import time

import numpy as np
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

logger = logging.getLogger(__name__)

BATCH_SIZE = 64
MAX_CHARS = 2000  # Truncate long texts to stay within model token limits
HF_API_URL = "https://api-inference.huggingface.co/models/{model_name}"


def _is_retryable(exc: BaseException) -> bool:
    """Retry on 503 (model loading) and 429 (rate limit) responses."""
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return exc.response.status_code in (503, 429)
    return False


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _call_hf_api(texts: list[str], model_name: str, token: str) -> list[list[float]]:
    """Call HuggingFace Inference API for a single batch."""
    url = HF_API_URL.format(model_name=model_name)
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={"inputs": texts, "options": {"wait_for_model": True}},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def encode_texts(
    texts: list[str],
    model_name: str = "intfloat/multilingual-e5-small",
) -> np.ndarray:
    """Encode texts into embeddings via HuggingFace Inference API.

    Args:
        texts: List of strings to encode.
        model_name: HuggingFace model identifier.

    Returns:
        numpy array of shape (len(texts), embedding_dim).
    """
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        raise RuntimeError(
            "HF_TOKEN environment variable not set. "
            "Get a token at https://huggingface.co/settings/tokens"
        )

    # Truncate long texts to avoid token limit issues
    truncated = [t[:MAX_CHARS] for t in texts]

    all_embeddings: list[list[float]] = []
    total_batches = (len(truncated) + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_idx, i in enumerate(range(0, len(truncated), BATCH_SIZE)):
        batch = truncated[i : i + BATCH_SIZE]
        logger.info("Embedding batch %d/%d (%d texts)...", batch_idx + 1, total_batches, len(batch))
        t0 = time.time()
        result = _call_hf_api(batch, model_name, token)
        logger.info("  Batch %d/%d done in %.1fs", batch_idx + 1, total_batches, time.time() - t0)
        all_embeddings.extend(result)

    return np.array(all_embeddings, dtype=np.float32)
