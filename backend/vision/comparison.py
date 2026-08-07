"""
Visual Comparator – expected vs actual screenshot difference report.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from .vision_manager import VisionManager, VisionResult, HAS_PIL

logger = logging.getLogger("lumora.vision.compare")


class VisualComparator:
    def __init__(self, manager: VisionManager):
        self.mgr = manager

    def compare(self, expected: str | bytes, actual: str | bytes) -> VisionResult:
        issues: List[Dict[str, Any]] = []
        data: Dict[str, Any] = {}

        img_e = self.mgr._load_image(expected)
        img_a = self.mgr._load_image(actual)

        if img_e is None or img_a is None:
            return VisionResult(
                success=False,
                message="Could not load one or both images for comparison",
                confidence=0.0,
            )

        # Resize actual to expected size for fair comparison
        if img_e.size != img_a.size:
            img_a = img_a.resize(img_e.size)
            data["resized"] = True
        else:
            data["resized"] = False

        data["size"] = {"w": img_e.size[0], "h": img_e.size[1]}

        similarity = 0.0
        if HAS_PIL:
            try:
                from PIL import ImageChops, ImageStat
                diff = ImageChops.difference(img_e, img_a)
                stat = ImageStat.Stat(diff)
                # mean absolute difference per channel
                mad = sum(stat.mean) / len(stat.mean)
                # 0 = identical, 255 = completely different
                similarity = max(0.0, 1.0 - (mad / 255.0))
                data["mean_abs_diff"] = round(mad, 2)
                data["similarity"] = round(similarity, 4)

                # save a simple diff image
                diff_path = self.mgr.storage / "comparisons" / f"diff_{int(__import__('time').time())}.png"
                # amplify for visibility
                amplified = diff.point(lambda p: min(255, p * 3))
                amplified.save(diff_path)
                data["diff_image"] = str(diff_path)

                if similarity < 0.95:
                    issues.append({
                        "type": "visual_difference",
                        "severity": "high" if similarity < 0.7 else "medium",
                        "message": f"Similarity {similarity:.1%} – significant visual difference detected",
                        "similarity": similarity,
                        "confidence": 0.85,
                    })
            except Exception as e:
                logger.warning("Pixel comparison failed: %s", e)
                data["similarity"] = None
                issues.append({"type": "compare_error", "message": str(e)})
        else:
            data["similarity"] = None
            issues.append({"type": "no_pil", "message": "Pillow required for pixel comparison"})

        # OCR-based missing / extra text
        from .ocr import OCREngine
        ocr = OCREngine(self.mgr)
        te = set(re_split(ocr.extract(expected).data.get("full_text", "")))
        ta = set(re_split(ocr.extract(actual).data.get("full_text", "")))
        missing = sorted(te - ta)[:30]
        extra = sorted(ta - te)[:30]
        data["missing_text"] = missing
        data["extra_text"] = extra
        if missing:
            issues.append({
                "type": "missing_text_components",
                "severity": "medium",
                "message": f"{len(missing)} text tokens present in expected but not actual",
                "items": missing[:10],
            })
        if extra:
            issues.append({
                "type": "extra_text_components",
                "severity": "low",
                "message": f"{len(extra)} extra text tokens in actual",
                "items": extra[:10],
            })

        conf = similarity if similarity else 0.4
        return VisionResult(
            success=True,
            message=f"Comparison complete – similarity {data.get('similarity', 'n/a')}",
            data=data,
            confidence=conf,
            issues=issues,
        )


def re_split(text: str) -> List[str]:
    import re
    return [t.lower() for t in re.findall(r"[a-zA-Z0-9]{2,}", text or "")]
