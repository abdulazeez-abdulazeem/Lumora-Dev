"""
Annotator – draw issue boxes / labels onto a screenshot for the Vision panel.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from .vision_manager import VisionManager, VisionResult, HAS_PIL

logger = logging.getLogger("lumora.vision.annotation")


class Annotator:
    def __init__(self, manager: VisionManager):
        self.mgr = manager

    def annotate(
        self,
        screenshot: str | bytes,
        issues: List[Dict[str, Any]],
        output_name: Optional[str] = None,
    ) -> VisionResult:
        img = self.mgr._load_image(screenshot)
        if img is None or not HAS_PIL:
            return VisionResult(
                success=False,
                message="Cannot annotate – image load or PIL missing",
                confidence=0.0,
            )

        from PIL import ImageDraw, ImageFont

        draw = ImageDraw.Draw(img)
        # try a default font
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        colours = {
            "high": (220, 40, 40),
            "medium": (230, 160, 30),
            "low": (40, 140, 220),
        }

        for idx, issue in enumerate(issues[:15]):
            sev = issue.get("severity", "medium")
            colour = colours.get(sev, (180, 180, 40))
            # place labels stacked on the left
            y = 10 + idx * 22
            label = f"[{sev}] {issue.get('type', 'issue')}: {issue.get('message', '')[:60]}"
            # background box
            try:
                bbox = draw.textbbox((8, y), label, font=font)
                draw.rectangle([bbox[0]-2, bbox[1]-1, bbox[2]+2, bbox[3]+1], fill=(0, 0, 0, 180))
            except Exception:
                pass
            draw.text((8, y), label, fill=colour, font=font)

            # if region coords present, draw rectangle
            if "left" in issue and "top" in issue:
                x0 = issue["left"]
                y0 = issue["top"]
                x1 = x0 + issue.get("width", 40)
                y1 = y0 + issue.get("height", 20)
                draw.rectangle([x0, y0, x1, y1], outline=colour, width=2)

        name = output_name or f"annot_{int(time.time())}"
        out_path = self.mgr.storage / "annotations" / f"{name}.png"
        img.save(out_path, "PNG")

        return VisionResult(
            success=True,
            message=f"Annotated image saved ({len(issues)} issue(s))",
            data={"annotated_path": str(out_path), "issue_count": len(issues)},
            confidence=0.9,
            issues=issues,
        )
