"""
UI Validator – check expected buttons, forms, text, navigation, images
against OCR + basic visual signals. Returns confidence scores.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from .vision_manager import VisionManager, VisionResult
from .ocr import OCREngine

logger = logging.getLogger("lumora.vision.validator")


class UIValidator:
    def __init__(self, manager: VisionManager):
        self.mgr = manager

    def validate(self, screenshot: str | bytes, expectations: Dict[str, Any]) -> VisionResult:
        """
        expectations example:
        {
          "buttons": ["Login", "Sign up"],
          "texts": ["Welcome", "Dashboard"],
          "forms": ["email", "password"],
          "navigation": ["Home", "Settings"],
          "min_images": 1,
          "must_not_contain": ["Error", "404"]
        }
        """
        issues: List[Dict[str, Any]] = []
        results: Dict[str, Any] = {"checks": []}

        ocr = OCREngine(self.mgr).extract(screenshot)
        full_text = (ocr.data.get("full_text") or "").lower()
        categories = ocr.data.get("categories") or {}

        def check_list(key: str, expected: List[str], source_text: str) -> None:
            found, missing = [], []
            for item in expected:
                if item.lower() in source_text:
                    found.append(item)
                else:
                    missing.append(item)
                    issues.append({
                        "type": f"missing_{key}",
                        "severity": "high",
                        "message": f"Expected {key[:-1]} '{item}' not found in visible text",
                        "expected": item,
                        "confidence": 0.75 if ocr.data.get("engine") == "tesseract" else 0.4,
                    })
            results["checks"].append({"category": key, "found": found, "missing": missing})

        if "buttons" in expectations:
            check_list("buttons", expectations["buttons"], full_text)
        if "texts" in expectations:
            check_list("texts", expectations["texts"], full_text)
        if "navigation" in expectations:
            check_list("navigation", expectations["navigation"], full_text)
        if "forms" in expectations:
            check_list("forms", expectations["forms"], full_text)

        if "must_not_contain" in expectations:
            for bad in expectations["must_not_contain"]:
                if bad.lower() in full_text:
                    issues.append({
                        "type": "forbidden_text",
                        "severity": "high",
                        "message": f"Forbidden text '{bad}' is visible",
                        "confidence": 0.8,
                    })
                    results["checks"].append({"category": "forbidden", "item": bad, "present": True})

        # simple image presence heuristic (edge density already known from layout)
        if "min_images" in expectations:
            # we cannot truly count images without CV; use edge density proxy
            from .layout_analyzer import LayoutAnalyzer
            layout = LayoutAnalyzer(self.mgr).analyze(screenshot)
            edge = layout.data.get("edge_density", 0)
            if edge < 5 and expectations["min_images"] > 0:
                issues.append({
                    "type": "possible_missing_images",
                    "severity": "medium",
                    "message": "Low visual complexity – expected images may be missing",
                    "confidence": 0.45,
                })

        passed = len([i for i in issues if i.get("severity") == "high"]) == 0
        score = max(0.0, 1.0 - 0.25 * len(issues))
        results["passed"] = passed
        results["score"] = round(score, 3)
        results["ocr_engine"] = ocr.data.get("engine")
        results["categories_detected"] = categories

        return VisionResult(
            success=True,
            message="UI validation " + ("passed" if passed else "failed"),
            data=results,
            confidence=score,
            issues=issues,
        )
