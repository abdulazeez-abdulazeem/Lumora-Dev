"""
Embedding provider – local hashing / bag-of-words vectors (no heavy deps).
Optional: OpenAI-compatible embeddings via existing providers if configured.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import List, Optional


class EmbeddingProvider:
    """Deterministic local embeddings so search works offline without extra packages."""

    def __init__(self, dim: int = 256, use_api: bool = False):
        self.dim = dim
        self.use_api = use_api

    def embed(self, text: str) -> List[float]:
        if self.use_api:
            try:
                return self._api_embed(text)
            except Exception:
                pass
        return self._local_embed(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]

    def _local_embed(self, text: str) -> List[float]:
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self.dim
        counts = Counter(tokens)
        vec = [0.0] * self.dim
        for tok, cnt in counts.items():
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            # tf * simple idf proxy
            tf = 1.0 + math.log(cnt)
            vec[idx] += sign * tf
        # L2 norm
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        # keep identifiers / code-ish tokens
        return re.findall(r"[a-z0-9_]{2,}", text)

    def _api_embed(self, text: str) -> List[float]:
        # optional path via providers if available
        try:
            from backend.providers import get_embedding  # type: ignore
            return get_embedding(text)
        except Exception:
            raise RuntimeError("API embeddings unavailable")

    @staticmethod
    def cosine(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        return max(-1.0, min(1.0, dot))  # already normalised
