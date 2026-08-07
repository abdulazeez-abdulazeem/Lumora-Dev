"""
Chunker – split documents while preserving headings and code blocks.
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Optional

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    heading: str = ""
    index: int = 0
    start_char: int = 0
    end_char: int = 0
    tags: List[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class Chunker:
    def __init__(self, max_chars: int = 1200, overlap: int = 150):
        self.max_chars = max_chars
        self.overlap = overlap

    def chunk(self, doc_id: str, text: str, tags: Optional[List[str]] = None) -> List[Chunk]:
        tags = tags or []
        # protect fenced code blocks
        code_blocks: List[str] = []
        def _protect(m):
            code_blocks.append(m.group(0))
            return f"\n@@CODEBLOCK{len(code_blocks)-1}@@\n"
        protected = re.sub(r"```[\s\S]*?```", _protect, text)

        # split by markdown headings
        sections = re.split(r"(?m)(?=^#{1,6}\s+)", protected)
        chunks: List[Chunk] = []
        char_pos = 0
        idx = 0

        for section in sections:
            if not section.strip():
                continue
            heading = ""
            hm = re.match(r"^(#{1,6})\s+(.+)$", section, re.M)
            if hm:
                heading = hm.group(2).strip()[:200]

            # restore code blocks
            body = section
            for i, cb in enumerate(code_blocks):
                body = body.replace(f"@@CODEBLOCK{i}@@", cb)

            # further split long sections
            pieces = self._split_long(body)
            for piece in pieces:
                piece = piece.strip()
                if len(piece) < 20:
                    continue
                cid = hashlib.sha256(f"{doc_id}:{idx}:{piece[:80]}".encode()).hexdigest()[:12]
                chunks.append(Chunk(
                    chunk_id=cid,
                    doc_id=doc_id,
                    text=piece,
                    heading=heading,
                    index=idx,
                    start_char=char_pos,
                    end_char=char_pos + len(piece),
                    tags=list(tags),
                    metadata={"heading": heading},
                ))
                idx += 1
                char_pos += len(piece)
        if not chunks and text.strip():
            cid = hashlib.sha256(f"{doc_id}:0:{text[:80]}".encode()).hexdigest()[:12]
            chunks.append(Chunk(
                chunk_id=cid,
                doc_id=doc_id,
                text=text.strip()[: self.max_chars],
                index=0,
                tags=list(tags),
            ))
        return chunks

    def _split_long(self, text: str) -> List[str]:
        if len(text) <= self.max_chars:
            return [text]
        parts: List[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.max_chars, len(text))
            # prefer break at paragraph
            if end < len(text):
                br = text.rfind("\n\n", start, end)
                if br > start + self.max_chars // 3:
                    end = br
                else:
                    br = text.rfind("\n", start, end)
                    if br > start + self.max_chars // 3:
                        end = br
            parts.append(text[start:end])
            start = max(end - self.overlap, end) if end < len(text) else end
        return parts
