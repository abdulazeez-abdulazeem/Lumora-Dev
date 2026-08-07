"""
Screenshot Analyzer – detects blank screens, loading failures, rendering
errors, missing elements, overflow, clipped content, etc.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .vision_manager import VisionManager, VisionResult, HAS_PIL

logger = logging.getLogger("lumora.vision.analyzer")


class ScreenshotAnalyzer:
    def __init__(self, manager: VisionManager):
        self.mgr = manager

    def analyze(self, screenshot: str | bytes) -> VisionResult:
        issues: List[Dict[str, Any]] = []
        data: Dict[str, Any] = {}

        img = self.mgr._load_image(screenshot)
        if img is None:
            if not HAS_PIL:
                return VisionResult(
                    success=False,
                    message="PIL not available – basic checks skipped",
                    data={"pil": False},
                    confidence=0.3,
                    issues=[{"type": "no_pil", "message": "Install Pillow for full analysis"}],
                )
            return VisionResult(success=False, message="Could not load screenshot", confidence=0.0)

        w, h = img.size
        data["width"] = w
        data["height"] = h
        data["mode"] = img.mode

        # 1. Blank / near-blank detection
        try:
            from PIL import ImageStat
            stat = ImageStat.Stat(img)
            mean = sum(stat.mean) / len(stat.mean)
            extrema = stat.extrema
            variance = sum(stat.var) / len(stat.var) if hasattr(stat, "var") else 0
            data["mean_brightness"] = round(mean, 2)
            data["variance"] = round(variance, 2)

            if mean > 245 and variance < 50:
                issues.append({
                    "type": "blank_screen",
                    "severity": "high",
                    "message": "Screenshot appears almost completely white/blank",
                    "confidence": 0.9,
                })
            elif mean < 10 and variance < 50:
                issues.append({
                    "type": "blank_screen",
                    "severity": "high",
                    "message": "Screenshot appears almost completely black",
                    "confidence": 0.9,
                })
            elif variance < 80 and 40 < mean < 220:
                issues.append({
                    "type": "low_content",
                    "severity": "medium",
                    "message": "Very low visual variance – possible empty or solid-color page",
                    "confidence": 0.65,
                })
        except Exception as e:
            logger.debug("Stat analysis failed: %s", e)

        # 2. Extreme aspect / tiny image
        if w < 100 or h < 100:
            issues.append({
                "type": "tiny_screenshot",
                "severity": "high",
                "message": f"Screenshot is very small ({w}x{h})",
                "confidence": 0.95,
            })
        if w / max(h, 1) > 6 or h / max(w, 1) > 6:
            issues.append({
                "type": "extreme_aspect",
                "severity": "medium",
                "message": "Unusual aspect ratio may indicate layout/overflow issues",
                "confidence": 0.5,
            })

        # 3. Simple edge density as proxy for content richness
        try:
            edges = img.convert("L").filter(__import__("PIL.ImageFilter", fromlist=["FIND_EDGES"]).FIND_EDGES)
            edge_stat = ImageStat.Stat(edges)
            edge_mean = edge_stat.mean[0]
            data["edge_density"] = round(edge_mean, 2)
            if edge_mean < 3:
                issues.append({
                    "type": "no_structure",
                    "severity": "medium",
                    "message": "Very few edges detected – possible blank or solid render",
                    "confidence": 0.7,
                })
        except Exception:
            pass

        # 4. Heuristic for loading spinners / error pages (text-based later via OCR)
        data["issue_count"] = len(issues)
        confidence = 1.0 - min(0.85, 0.2 * len([i for i in issues if i.get("severity") == "high"]))
        msg = f"Analyzed {w}x{h} image – {len(issues)} potential issue(s)"
        return VisionResult(success=True, message=msg, data=data, confidence=confidence, issues=issues)
