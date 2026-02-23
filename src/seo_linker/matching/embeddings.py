"""SentenceTransformer wrapper for generating embeddings."""

from __future__ import annotations

import os

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
from sentence_transformers import SentenceTransformer

_model_cache: dict[str, SentenceTransformer] = {}

BATCH_SIZE = 64


def get_model(model_name: str = "intfloat/multilingual-e5-small") -> SentenceTransformer:
    if model_name not in _model_cache:
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


def encode_texts(texts: list[str], model_name: str = "intfloat/multilingual-e5-small") -> np.ndarray:
    model = get_model(model_name)
    return model.encode(
        texts,
        show_progress_bar=len(texts) > BATCH_SIZE,
        convert_to_numpy=True,
        batch_size=BATCH_SIZE,
    )
