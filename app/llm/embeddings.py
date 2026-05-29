"""Embedding helpers with an optional Hugging Face backend."""
from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache


VECTOR_SIZE = 384


@lru_cache(maxsize=1)
def _load_sentence_transformer():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None
    return SentenceTransformer("all-MiniLM-L6-v2")


def _fallback_embed_text(text: str) -> list[float]:
    """Generate a deterministic local embedding without external ML packages."""
    vector = [0.0] * VECTOR_SIZE
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % VECTOR_SIZE
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def embed_text(text: str) -> list[float]:
    """Generate a 384-dimensional embedding for text.

    Uses sentence-transformers when installed. Otherwise falls back to a
    deterministic hashed bag-of-words vector so local setup stays lightweight.
    """
    model = _load_sentence_transformer()
    if model is None:
        return _fallback_embed_text(text)

    embedding = model.encode(text, convert_to_tensor=False)
    return embedding.tolist()


async def embed_text_async(text: str) -> list[float]:
    """Async wrapper for embedding (runs in thread pool to avoid blocking)."""
    # For now, just call sync version
    # In production, use asyncio.to_thread or similar
    return embed_text(text)
