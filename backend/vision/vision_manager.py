"""
Vision Manager – central coordinator for screenshot analysis, OCR,
layout checks, validation, comparison and annotation.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger("lumora.vision")

# Optional heavy deps – degrade gracefully
try:
    from PIL import Image, ImageDraw, ImageFont, ImageStat, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None  # type: ignore

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


class VisionResult(BaseModel):
    success: bool = True
    message: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


class VisionManager:
    """Singleton-style manager that orchestrates all vision sub-modules."""

    def __init__(self, storage_dir: Optional[str] = None):
        root = Path(storage_dir or os.environ.get("LUMORA_VISION_DIR", ".lumora-vision"))
        self.storage = root
        self.storage.mkdir(parents=True, exist_ok=True)
        (self.storage / "screenshots").mkdir(exist_ok=True)
        (self.storage / "annotations").mkdir(exist_ok=True)
        (self.storage / "comparisons").mkdir(exist_ok=True)
        self._history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Screenshot helpers
    # ------------------------------------------------------------------
    def _load_image(self, source: str | bytes) -> Optional[Any]:
        if not HAS_PIL:
            return None
        try:
            if isinstance(source, bytes):
                return Image.open(io.BytesIO(source)).convert("RGB")
            if isinstance(source, str):
                if source.startswith("data:image"):
                    b64 = source.split(",", 1)[-1]
                    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
                path = Path(source)
                if path.exists():
                    return Image.open(path).convert("RGB")
                # try base64 without prefix
                try:
                    return Image.open(io.BytesIO(base64.b64decode(source))).convert("RGB")
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Failed to load image: %s", e)
        return None

    def save_screenshot(self, image_data: bytes | str, name: Optional[str] = None) -> str:
        sid = name or f"shot_{uuid.uuid4().hex[:12]}"
        path = self.storage / "screenshots" / f"{sid}.png"
        img = self._load_image(image_data)
        if img is not None:
            img.save(path, "PNG")
        elif isinstance(image_data, bytes):
            path.write_bytes(image_data)
        else:
            # assume base64
            raw = image_data
            if raw.startswith("data:"):
                raw = raw.split(",", 1)[-1]
            path.write_bytes(base64.b64decode(raw))
        return str(path)

    # ------------------------------------------------------------------
    # High-level pipelines
    # ------------------------------------------------------------------
    def analyze(self, screenshot: str | bytes, context: Optional[Dict] = None) -> VisionResult:
        """Full analysis: blank/broken detection, layout, OCR summary, issues."""
        from .screenshot_analyzer import ScreenshotAnalyzer
        from .layout_analyzer import LayoutAnalyzer
        from .ocr import OCREngine

        analyzer = ScreenshotAnalyzer(self)
        layout = LayoutAnalyzer(self)
        ocr = OCREngine(self)

        issues: List[Dict[str, Any]] = []
        data: Dict[str, Any] = {}

        basic = analyzer.analyze(screenshot)
        data["basic"] = basic.data
        issues.extend(basic.issues)

        layout_res = layout.analyze(screenshot)
        data["layout"] = layout_res.data
        issues.extend(layout_res.issues)

        ocr_res = ocr.extract(screenshot)
        data["ocr"] = ocr_res.data
        if not ocr_res.success:
            issues.append({"type": "ocr_failed", "message": ocr_res.message})

        confidence = 1.0 - min(0.9, 0.15 * len(issues))
        msg = f"Found {len(issues)} issue(s)" if issues else "No major visual issues detected"
        result = VisionResult(success=True, message=msg, data=data, confidence=confidence, issues=issues)
        self._history.append({"action": "analyze", "result": result.model_dump()})
        return result

    def ocr(self, screenshot: str | bytes, regions: Optional[List[Dict]] = None) -> VisionResult:
        from .ocr import OCREngine
        return OCREngine(self).extract(screenshot, regions=regions)

    def validate_ui(self, screenshot: str | bytes, expectations: Dict[str, Any]) -> VisionResult:
        from .ui_validator import UIValidator
        return UIValidator(self).validate(screenshot, expectations)

    def compare(self, expected: str | bytes, actual: str | bytes) -> VisionResult:
        from .comparison import VisualComparator
        return VisualComparator(self).compare(expected, actual)

    def annotate(self, screenshot: str | bytes, issues: List[Dict], output_name: Optional[str] = None) -> VisionResult:
        from .annotation import Annotator
        return Annotator(self).annotate(screenshot, issues, output_name=output_name)

    def inspect_layout(self, screenshot: str | bytes) -> VisionResult:
        from .layout_analyzer import LayoutAnalyzer
        return LayoutAnalyzer(self).analyze(screenshot)

    def history(self, limit: int = 20) -> List[Dict]:
        return self._history[-limit:]


_manager: Optional[VisionManager] = None


def get_vision_manager() -> VisionManager:
    global _manager
    if _manager is None:
        _manager = VisionManager()
    return _manager
