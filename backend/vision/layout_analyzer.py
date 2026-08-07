"""
Layout Analyzer – alignment, spacing, overflow, empty regions, colour consistency.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from .vision_manager import VisionManager, VisionResult, HAS_PIL

logger = logging.getLogger("lumora.vision.layout")


class LayoutAnalyzer:
    def __init__(self, manager: VisionManager):
        self.mgr = manager

    def analyze(self, screenshot: str | bytes) -> VisionResult:
        issues: List[Dict[str, Any]] = []
        data: Dict[str, Any] = {}

        img = self.mgr._load_image(screenshot)
        if img is None:
            return VisionResult(success=False, message="Cannot load image", confidence=0.0)

        w, h = img.size
        data["width"] = w
        data["height"] = h

        # Colour palette / theme consistency (simple quantisation)
        try:
            from collections import Counter
            # resize for speed
            small = img.resize((min(w, 200), min(h, 150)))
            colors = list(small.getdata())
            # bucket
            buckets = Counter((c[0] // 32, c[1] // 32, c[2] // 32) for c in colors)
            dominant = buckets.most_common(8)
            data["dominant_colors"] = [
                {"rgb": (k[0]*32, k[1]*32, k[2]*32), "pct": round(100 * v / len(colors), 1)}
                for k, v in dominant
            ]
            # large empty / solid regions
            if dominant and dominant[0][1] / len(colors) > 0.85:
                issues.append({
                    "type": "large_empty_or_solid",
                    "severity": "medium",
                    "message": "One colour occupies >85% of the screenshot – possible empty layout",
                    "confidence": 0.7,
                })
        except Exception as e:
            logger.debug("colour analysis failed: %s", e)

        # Edge-based "structure" score
        try:
            from PIL import ImageFilter, ImageStat, ImageOps
            gray = ImageOps.grayscale(img)
            edges = gray.filter(ImageFilter.FIND_EDGES)
            e_stat = ImageStat.Stat(edges)
            edge_mean = e_stat.mean[0]
            data["edge_density"] = round(edge_mean, 2)
            if edge_mean < 4:
                issues.append({
                    "type": "weak_structure",
                    "severity": "low",
                    "message": "Low edge density – sparse or broken layout possible",
                    "confidence": 0.55,
                })
        except Exception:
            pass

        # Simple border / margin check (sample corners & edges)
        try:
            pixels = img.load()
            corner_samples = [
                pixels[2, 2], pixels[w-3, 2], pixels[2, h-3], pixels[w-3, h-3]
            ]
            # if all corners identical and image not tiny → possible full-bleed solid
            if len(set(corner_samples)) == 1 and w > 200:
                data["uniform_corners"] = True
            else:
                data["uniform_corners"] = False
        except Exception:
            pass

        # Heuristic overflow proxy: very tall images often indicate vertical overflow
        if h > 3000:
            issues.append({
                "type": "possible_overflow",
                "severity": "low",
                "message": f"Very tall screenshot ({h}px) – may indicate uncontained content",
                "confidence": 0.4,
            })

        confidence = 1.0 - min(0.7, 0.12 * len(issues))
        return VisionResult(
            success=True,
            message=f"Layout analysis complete – {len(issues)} note(s)",
            data=data,
            confidence=confidence,
            issues=issues,
        )
