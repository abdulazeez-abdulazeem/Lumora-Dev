"""
OCR Engine – extract visible text from screenshots (buttons, labels, forms, etc.)
Uses pytesseract when available; falls back to a lightweight heuristic stub.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from .vision_manager import VisionManager, VisionResult, HAS_PIL, HAS_TESSERACT

logger = logging.getLogger("lumora.vision.ocr")


class OCREngine:
    def __init__(self, manager: VisionManager):
        self.mgr = manager

    def extract(self, screenshot: str | bytes, regions: Optional[List[Dict]] = None) -> VisionResult:
        img = self.mgr._load_image(screenshot)
        if img is None:
            return VisionResult(success=False, message="Cannot load image for OCR", confidence=0.0)

        text = ""
        blocks: List[Dict[str, Any]] = []
        engine = "none"

        if HAS_TESSERACT and HAS_PIL:
            try:
                import pytesseract
                from pytesseract import Output
                if regions:
                    # crop and OCR each region
                    for r in regions:
                        box = (r.get("x", 0), r.get("y", 0), r.get("x", 0) + r.get("w", 50), r.get("y", 0) + r.get("h", 20))
                        crop = img.crop(box)
                        t = pytesseract.image_to_string(crop).strip()
                        if t:
                            blocks.append({"text": t, "region": r, "confidence": 0.8})
                            text += t + "\n"
                else:
                    data = pytesseract.image_to_data(img, output_type=Output.DICT)
                    n = len(data["text"])
                    for i in range(n):
                        conf = int(data["conf"][i]) if data["conf"][i] != "-1" else 0
                        t = data["text"][i].strip()
                        if t and conf > 30:
                            blocks.append({
                                "text": t,
                                "left": data["left"][i],
                                "top": data["top"][i],
                                "width": data["width"][i],
                                "height": data["height"][i],
                                "confidence": conf / 100.0,
                            })
                            text += t + " "
                    engine = "tesseract"
            except Exception as e:
                logger.warning("Tesseract OCR failed: %s", e)
                text = self._fallback_text_heuristic(img)
                engine = "heuristic"
        else:
            text = self._fallback_text_heuristic(img)
            engine = "heuristic"

        # Categorise common UI strings
        categories = self._categorise(text)

        data = {
            "full_text": text.strip(),
            "blocks": blocks[:200],  # cap
            "engine": engine,
            "char_count": len(text),
            "categories": categories,
            "has_tesseract": HAS_TESSERACT,
        }
        conf = 0.85 if engine == "tesseract" else 0.35
        return VisionResult(
            success=True,
            message=f"OCR via {engine}: {len(blocks)} blocks, {len(text)} chars",
            data=data,
            confidence=conf,
        )

    def _fallback_text_heuristic(self, img) -> str:
        """Very weak fallback when tesseract missing – returns placeholder."""
        return "[OCR unavailable – install pytesseract + tesseract-ocr for real text extraction]"

    def _categorise(self, text: str) -> Dict[str, List[str]]:
        lower = text.lower()
        cats: Dict[str, List[str]] = {
            "buttons": [],
            "labels": [],
            "errors": [],
            "headings": [],
            "nav": [],
            "forms": [],
        }
        # simple keyword heuristics
        button_words = re.findall(r"\b(submit|save|cancel|delete|login|sign up|next|back|create|update|ok|yes|no)\b", lower, re.I)
        cats["buttons"] = list(set(button_words))[:20]
        err_words = re.findall(r"\b(error|failed|invalid|required|missing|not found|exception|404|500)\b", lower, re.I)
        cats["errors"] = list(set(err_words))[:20]
        nav_words = re.findall(r"\b(home|dashboard|settings|profile|logout|menu|about|contact)\b", lower, re.I)
        cats["nav"] = list(set(nav_words))[:20]
        form_words = re.findall(r"\b(email|password|username|name|phone|address|search)\b", lower, re.I)
        cats["forms"] = list(set(form_words))[:20]
        return cats
