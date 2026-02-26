"""HuggingFace Inference API wrapper for generating embeddings."""

from __future__ import annotations

import os
from typing import Any

import numpy as np
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

BATCH_SIZE = 64
HF_API_URL = "https://api-inference.huggingface.co/models/{model_name}"


def _is_503(exc: BaseException) -> bool:
    """Retry on 503 (model loading) responses."""
    return isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code == 503


@retry(
    retry=retry_if_exception(_is_503),
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
        timeout=30,
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

    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        result = _call_hf_api(batch, model_name, token)
        all_embeddings.extend(result)

    return np.array(all_embeddings, dtype=np.float32)
