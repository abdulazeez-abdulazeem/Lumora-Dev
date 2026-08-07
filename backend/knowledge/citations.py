"""
Citation helpers for knowledge search results.
"""

from __future__ import annotations

from typing import Any, Dict, List


class CitationFormatter:
    def format_hits(self, hits: List[dict]) -> List[Dict[str, Any]]:
        cites = []
        for i, h in enumerate(hits, 1):
            cites.append({
                "index": i,
                "title": h.get("title") or "Untitled",
                "source": h.get("source") or "",
                "heading": h.get("heading") or "",
                "score": h.get("score"),
                "snippet": (h.get("text") or "")[:240],
            })
        return cites

    def as_context_block(self, hits: List[dict], max_chars: int = 3000) -> str:
        lines = ["# Knowledge context\n"]
        total = 0
        for i, h in enumerate(hits, 1):
            block = (
                f"[{i}] {h.get('title') or 'doc'} "
                f"({h.get('source')}) score={h.get('score')}\n"
                f"{h.get('heading') and '## ' + h.get('heading') + chr(10) or ''}"
                f"{h.get('text') or ''}\n\n"
            )
            if total + len(block) > max_chars:
                break
            lines.append(block)
            total += len(block)
        return "".join(lines)

    def cite_inline(self, hits: List[dict]) -> str:
        return "; ".join(
            f"[{i}] {h.get('title') or h.get('source')} (score={h.get('score')})"
            for i, h in enumerate(hits, 1)
        )
