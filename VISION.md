# Lumora Dev Vision & UI Intelligence (v3 Phase 2C)

## Overview

Vision gives Lumora the ability to **see** the application the same way a user does.
It reuses Browser Automation (Phase 2A) screenshots and plugs into the autonomous
Execution loop so that UI problems trigger automatic repair cycles.

## Module layout

```
backend/vision/
  __init__.py
  vision_manager.py      # coordinator + storage
  screenshot_analyzer.py # blank / broken / low-content detection
  ocr.py                 # text extraction (tesseract or heuristic)
  layout_analyzer.py     # spacing, empty regions, colour dominance
  ui_validator.py        # expected buttons / forms / text checks
  comparison.py          # expected vs actual similarity
  annotation.py          # draw issue labels on screenshots
  vision_router.py       # FastAPI /vision/*
```

## API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/vision/analyze` | POST | Full analysis (blank, layout, OCR summary) |
| `/vision/ocr` | POST | Extract visible text |
| `/vision/validate` | POST | Check expectations (buttons, texts, …) |
| `/vision/compare` | POST | Expected vs actual similarity + diff image |
| `/vision/annotate` | POST | Overlay issues on screenshot |
| `/vision/layout` | POST | Layout-only analysis |
| `/vision/history` | GET | Recent vision actions |
| `/vision/status` | GET | PIL / tesseract availability |

Request bodies accept screenshot as **file path**, **raw base64**, or **data-URL**.

## Agent tools

- `analyze_screenshot`
- `validate_ui`
- `compare_ui`
- `annotate_screenshot`
- `inspect_layout`

## Execution integration

After the browser opens a page the loop should call:

```python
from backend.execution.ui_loop import run_ui_validation_step
report = run_ui_validation_step(screenshot_path_or_b64, expectations={...})
if not report["passed"]:
    # feed recommended_fixes back into planner / agent for repair
```

## Dependencies

- **Pillow** (required for analysis)
- **pytesseract** + system `tesseract-ocr` (optional, enables real OCR)

## Frontend

Sidebar → **Vision** panel:

- Analyze / OCR / Layout buttons (capture via Browser first)
- Confidence, issues list, OCR text, recommended fixes, annotated preview

## Design principles

- Independent & reusable – no hard dependency on a running browser
- Graceful degradation when tesseract or heavy CV libs are absent
- Never duplicates Browser Automation; only consumes its screenshots
- Feeds structured issues + fix suggestions into the existing Execution / Planner / Agent stack
