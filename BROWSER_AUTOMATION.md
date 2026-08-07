# Lumora Dev — Browser Automation (v3 Phase 2A)

Playwright-powered browser control for the agent and REST API.

## Setup

```bash
pip install playwright
playwright install chromium
```

## Module layout

```
backend/browser/
  __init__.py
  browser_manager.py   # launch/close, tabs, navigation
  actions.py           # click, type, keys, select, upload, drag, scroll
  screenshots.py       # viewport / full page / element
  inspector.py         # title, URL, text, HTML, find, forms, buttons
  recorder.py          # record + replay action sequences
  browser_router.py    # FastAPI routes under /browser
```

## REST API (prefix `/browser`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/launch` | Start Chromium (`headless` default true) |
| POST | `/close` | Shut down browser |
| GET | `/status` | Running state, tabs, active tab |
| POST | `/goto` | Navigate to URL |
| POST | `/refresh` `/back` `/forward` | History |
| POST | `/tab/new` `/tab/select` `/tab/close` | Tabs |
| POST | `/click` `/hover` `/type` `/press` `/select` `/upload` `/drag` `/scroll` | Interactions |
| GET | `/info` `/text` `/html` `/find` `/attribute` `/forms` `/buttons` | Inspection |
| POST | `/screenshot` | Capture PNG under `frontend/screenshots/` |
| POST | `/record/start` `/record/stop` | Recording |
| GET | `/record/list` `/record/{id}` | Saved recordings |
| POST | `/record/{id}/replay` | Replay |

## Agent tools

- `browser_open(url)`
- `browser_click(selector)`
- `browser_type(selector, text)`
- `browser_inspect(what)` — info | text | forms | buttons
- `browser_screenshot(full_page?)`
- `browser_close()`

## UI

Sidebar **Browser** panel: launch/close, status, URL/title, go-to URL, tab list.

## Notes

- Local single-user; browser runs headless by default.
- Timeouts and navigation errors are caught and returned as structured errors.
- Recordings stored in `.lumora-browser-recordings/` (gitignored).
