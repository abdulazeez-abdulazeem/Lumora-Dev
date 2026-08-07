"""
Vision-aware validation step used by the autonomous development loop.

Flow after app launch + browser open:
  Capture Screenshot → Analyze → Detect UI Problems → (optionally) Repair signal
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("lumora.execution.ui_loop")


class UIValidationReport(BaseModel):
    passed: bool = False
    confidence: float = 0.0
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    ocr_summary: str = ""
    screenshot_path: Optional[str] = None
    recommended_fixes: List[str] = Field(default_factory=list)
    raw: Dict[str, Any] = Field(default_factory=dict)


class VisionAwareValidator:
    """Called by the execution engine after browser navigation."""

    def __init__(self):
        pass

    def validate(
        self,
        screenshot: str | bytes,
        expectations: Optional[Dict[str, Any]] = None,
        auto_annotate: bool = True,
    ) -> UIValidationReport:
        from backend.vision.vision_manager import get_vision_manager

        mgr = get_vision_manager()
        analysis = mgr.analyze(screenshot)
        expectations = expectations or {}
        validation = mgr.validate_ui(screenshot, expectations) if expectations else None

        issues = list(analysis.issues)
        if validation:
            issues.extend(validation.issues)

        fixes: List[str] = []
        for iss in issues:
            t = iss.get("type", "")
            if t == "blank_screen":
                fixes.append("Check that the route renders content; inspect server logs and React/Vue mount errors.")
            elif t.startswith("missing_"):
                fixes.append(f"Add or fix the missing UI element: {iss.get('expected') or iss.get('message')}")
            elif t == "visual_difference":
                fixes.append("Visual regression detected – review recent CSS/layout changes.")
            elif t == "possible_overflow":
                fixes.append("Inspect containers for missing overflow/height constraints.")
            else:
                fixes.append(iss.get("message", "Review UI issue"))

        annotated = None
        if auto_annotate and issues:
            ann = mgr.annotate(screenshot, issues)
            annotated = ann.data.get("annotated_path")

        passed = len([i for i in issues if i.get("severity") == "high"]) == 0
        conf = analysis.confidence
        if validation:
            conf = min(conf, validation.confidence)

        ocr_text = ""
        try:
            ocr = mgr.ocr(screenshot)
            ocr_text = (ocr.data.get("full_text") or "")[:500]
        except Exception:
            pass

        return UIValidationReport(
            passed=passed,
            confidence=conf,
            issues=issues,
            ocr_summary=ocr_text,
            screenshot_path=annotated or (screenshot if isinstance(screenshot, str) else None),
            recommended_fixes=fixes[:10],
            raw={"analysis": analysis.model_dump(), "validation": validation.model_dump() if validation else None},
        )


def run_ui_validation_step(
    screenshot: str | bytes,
    expectations: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convenience entry point for the execution loop."""
    report = VisionAwareValidator().validate(screenshot, expectations=expectations)
    return report.model_dump()


def knowledge_context_for_goal(goal: str, top_k: int = 6) -> str:
    """Fetch documentation context before code changes (Execution Engine integration)."""
    try:
        from backend.knowledge.knowledge_manager import get_knowledge_manager
        return get_knowledge_manager().context_for_execution(goal, top_k=top_k)
    except Exception as e:
        logger.warning("knowledge context failed: %s", e)
        return ""
