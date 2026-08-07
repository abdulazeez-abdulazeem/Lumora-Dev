"""
Lightweight extractive summarizer for documents / search results.
"""

from __future__ import annotations

import re
from typing import List


class Summarizer:
    def summarize(self, text: str, max_sentences: int = 5) -> str:
        if not text or not text.strip():
            return ""
        # split sentences
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        if len(sentences) <= max_sentences:
            return " ".join(sentences)
        # score by length + keyword density (simple)
        scored = []
        for i, s in enumerate(sentences):
            words = re.findall(r"[a-zA-Z]{3,}", s.lower())
            score = len(set(words)) + (2 if i == 0 else 0) + min(len(s) / 80, 3)
            scored.append((score, i, s))
        scored.sort(key=lambda x: -x[0])
        chosen = sorted(scored[:max_sentences], key=lambda x: x[1])
        return " ".join(s for _, _, s in chosen)

    def summarize_hits(self, hits: List[dict], max_chars: int = 800) -> str:
        parts = []
        total = 0
        for h in hits:
            snippet = (h.get("text") or "")[:300]
            line = f"- [{h.get('title') or h.get('source')}] {snippet}"
            if total + len(line) > max_chars:
                break
            parts.append(line)
            total += len(line)
        return "\n".join(parts)
