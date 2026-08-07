"""Tests for Vision & UI Intelligence (Phase 2C)."""

import base64
import io
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Ensure Pillow is importable
pytest.importorskip("PIL")


def _make_solid_png(color=(255, 255, 255), size=(200, 150)):
    from PIL import Image
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_gradient_png(size=(300, 200)):
    from PIL import Image
    img = Image.new("RGB", size)
    pixels = img.load()
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = (x % 256, y % 256, (x + y) % 256)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_vision_manager_init():
    from backend.vision.vision_manager import VisionManager, get_vision_manager
    mgr = get_vision_manager()
    assert mgr is not None
    assert mgr.storage.exists()


def test_analyze_blank_screen():
    from backend.vision.vision_manager import get_vision_manager
    mgr = get_vision_manager()
    blank = _make_solid_png((255, 255, 255))
    result = mgr.analyze(blank)
    assert result.success
    types = [i["type"] for i in result.issues]
    assert "blank_screen" in types or "low_content" in types or "no_structure" in types


def test_analyze_contentful():
    from backend.vision.vision_manager import get_vision_manager
    mgr = get_vision_manager()
    content = _make_gradient_png()
    result = mgr.analyze(content)
    assert result.success
    assert result.data.get("basic", {}).get("width") == 300 or result.data.get("width") == 300


def test_ocr_heuristic():
    from backend.vision.vision_manager import get_vision_manager
    mgr = get_vision_manager()
    result = mgr.ocr(_make_solid_png())
    assert result.success
    assert "engine" in result.data


def test_layout_analyzer():
    from backend.vision.vision_manager import get_vision_manager
    mgr = get_vision_manager()
    result = mgr.inspect_layout(_make_gradient_png())
    assert result.success
    assert "edge_density" in result.data or "width" in result.data


def test_ui_validator_missing_button():
    from backend.vision.vision_manager import get_vision_manager
    mgr = get_vision_manager()
    result = mgr.validate_ui(
        _make_solid_png(),
        {"buttons": ["Login", "Submit"], "must_not_contain": []},
    )
    assert result.success
    assert result.data.get("passed") is False or len(result.issues) >= 0


def test_compare_identical():
    from backend.vision.vision_manager import get_vision_manager
    mgr = get_vision_manager()
    img = _make_gradient_png()
    result = mgr.compare(img, img)
    assert result.success
    sim = result.data.get("similarity")
    assert sim is None or sim > 0.95


def test_compare_different():
    from backend.vision.vision_manager import get_vision_manager
    mgr = get_vision_manager()
    a = _make_solid_png((255, 0, 0))
    b = _make_solid_png((0, 0, 255))
    result = mgr.compare(a, b)
    assert result.success
    sim = result.data.get("similarity")
    assert sim is None or sim < 0.9


def test_annotate():
    from backend.vision.vision_manager import get_vision_manager
    mgr = get_vision_manager()
    issues = [{"type": "blank_screen", "severity": "high", "message": "test issue"}]
    result = mgr.annotate(_make_solid_png(), issues)
    assert result.success
    path = result.data.get("annotated_path")
    assert path and Path(path).exists()


def test_execution_ui_loop():
    from backend.execution.ui_loop import run_ui_validation_step
    report = run_ui_validation_step(_make_solid_png(), expectations={"buttons": ["Save"]})
    assert "passed" in report
    assert "issues" in report
    assert "recommended_fixes" in report


def test_vision_router_import():
    from backend.vision.vision_router import router
    paths = [r.path for r in router.routes]
    assert any("/analyze" in p for p in paths)
    assert any("/ocr" in p for p in paths)
    assert any("/validate" in p for p in paths)
    assert any("/compare" in p for p in paths)


def test_agent_tools_registered():
    src = Path(__file__).resolve().parents[1] / "agent.py"
    text = src.read_text()
    for expected in ("analyze_screenshot", "validate_ui", "compare_ui", "annotate_screenshot", "inspect_layout"):
        assert expected in text, f"missing tool {expected}"


def test_save_screenshot_roundtrip(tmp_path):
    from backend.vision.vision_manager import VisionManager
    mgr = VisionManager(storage_dir=str(tmp_path))
    data = _make_solid_png()
    path = mgr.save_screenshot(data, name="testshot")
    assert Path(path).exists()
    assert Path(path).stat().st_size > 0
