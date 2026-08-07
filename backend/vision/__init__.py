"""
Lumora Dev Vision & UI Intelligence (v3 Phase 2C)

Provides screenshot analysis, OCR, layout detection, UI validation,
visual comparison, and annotation. Reuses Browser Automation screenshots
and integrates with the Execution Engine for automatic UI repair loops.
"""

from .vision_manager import VisionManager, get_vision_manager
from .screenshot_analyzer import ScreenshotAnalyzer
from .ui_validator import UIValidator
from .layout_analyzer import LayoutAnalyzer
from .ocr import OCREngine
from .comparison import VisualComparator
from .annotation import Annotator

__all__ = [
    "VisionManager",
    "get_vision_manager",
    "ScreenshotAnalyzer",
    "UIValidator",
    "LayoutAnalyzer",
    "OCREngine",
    "VisualComparator",
    "Annotator",
]
