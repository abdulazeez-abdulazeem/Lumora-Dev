"""
Document Loader – ingest Markdown, TXT, PDF, HTML, JSON, Python, OpenAPI, etc.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("lumora.knowledge.loader")


class DocumentMeta(BaseModel):
    doc_id: str
    source: str
    title: str = ""
    date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: List[str] = Field(default_factory=list)
    project: str = ""
    content_type: str = "text"
    char_count: int = 0
    extra: Dict[str, Any] = Field(default_factory=dict)


class LoadedDocument(BaseModel):
    meta: DocumentMeta
    text: str


class DocumentLoader:
    SUPPORTED = {".md", ".txt", ".pdf", ".html", ".htm", ".json", ".py", ".rst", ".yaml", ".yml"}

    def load_file(self, path: str | Path, tags: Optional[List[str]] = None, project: str = "") -> LoadedDocument:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Document not found: {path}")
        suffix = p.suffix.lower()
        raw = p.read_bytes()
        text = self._extract_text(p, raw, suffix)
        title = self._guess_title(p, text)
        doc_id = hashlib.sha256(f"{p.resolve()}:{len(raw)}".encode()).hexdigest()[:16]
        meta = DocumentMeta(
            doc_id=doc_id,
            source=str(p.resolve()),
            title=title,
            tags=tags or self._default_tags(p),
            project=project or p.parent.name,
            content_type=suffix.lstrip(".") or "text",
            char_count=len(text),
        )
        return LoadedDocument(meta=meta, text=text)

    def load_text(
        self,
        text: str,
        source: str = "inline",
        title: str = "",
        tags: Optional[List[str]] = None,
        project: str = "",
        content_type: str = "text",
    ) -> LoadedDocument:
        doc_id = hashlib.sha256(f"{source}:{text[:200]}".encode()).hexdigest()[:16]
        meta = DocumentMeta(
            doc_id=doc_id,
            source=source,
            title=title or source,
            tags=tags or [],
            project=project,
            content_type=content_type,
            char_count=len(text),
        )
        return LoadedDocument(meta=meta, text=text)

    def load_directory(
        self,
        directory: str | Path,
        recursive: bool = True,
        tags: Optional[List[str]] = None,
        project: str = "",
        patterns: Optional[List[str]] = None,
    ) -> List[LoadedDocument]:
        root = Path(directory)
        docs: List[LoadedDocument] = []
        if not root.exists():
            return docs
        paths = root.rglob("*") if recursive else root.glob("*")
        for p in paths:
            if not p.is_file():
                continue
            if patterns:
                if not any(p.match(pat) for pat in patterns):
                    continue
            elif p.suffix.lower() not in self.SUPPORTED:
                continue
            # skip huge / binary-ish
            try:
                if p.stat().st_size > 5_000_000:
                    continue
                docs.append(self.load_file(p, tags=tags, project=project or root.name))
            except Exception as e:
                logger.warning("Skip %s: %s", p, e)
        return docs

    def _extract_text(self, path: Path, raw: bytes, suffix: str) -> str:
        if suffix in {".md", ".txt", ".rst", ".py", ".yaml", ".yml"}:
            return raw.decode("utf-8", errors="replace")
        if suffix == ".json":
            try:
                data = json.loads(raw.decode("utf-8", errors="replace"))
                return json.dumps(data, indent=2)
            except Exception:
                return raw.decode("utf-8", errors="replace")
        if suffix in {".html", ".htm"}:
            return self._html_to_text(raw.decode("utf-8", errors="replace"))
        if suffix == ".pdf":
            return self._pdf_to_text(raw, path)
        return raw.decode("utf-8", errors="replace")

    def _html_to_text(self, html: str) -> str:
        # lightweight strip tags
        text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
        text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _pdf_to_text(self, raw: bytes, path: Path) -> str:
        try:
            import pypdf
            from io import BytesIO
            reader = pypdf.PdfReader(BytesIO(raw))
            parts = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            return "\n".join(parts)
        except ImportError:
            logger.warning("pypdf not installed – PDF text empty for %s", path)
            return f"[PDF content unavailable – install pypdf to extract text from {path.name}]"
        except Exception as e:
            logger.warning("PDF extract failed for %s: %s", path, e)
            return f"[PDF extract error: {e}]"

    def _guess_title(self, path: Path, text: str) -> str:
        if path.suffix.lower() == ".md":
            m = re.search(r"^#\s+(.+)$", text, re.M)
            if m:
                return m.group(1).strip()[:120]
        return path.stem.replace("_", " ").replace("-", " ").title()[:120]

    def _default_tags(self, path: Path) -> List[str]:
        name = path.name.lower()
        tags = [path.suffix.lstrip(".")]
        if "readme" in name:
            tags.append("readme")
        if "changelog" in name:
            tags.append("changelog")
        if "roadmap" in name:
            tags.append("roadmap")
        if "api" in name or path.suffix == ".json":
            tags.append("api")
        if path.suffix == ".py":
            tags.append("code")
        return tags
