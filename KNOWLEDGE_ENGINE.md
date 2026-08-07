# Lumora Dev Knowledge Engine (v3 Phase 3A)

## Purpose

Give Lumora long-term engineering knowledge: project docs, API references,
design decisions, READMEs, changelogs, and manuals — searchable by meaning,
with citations, and wired into Agent, Planner, and Execution.

## Module layout

```
backend/knowledge/
  knowledge_manager.py   # ingest, search, reindex, context_for_execution
  document_loader.py     # MD, TXT, PDF, HTML, JSON, Python, OpenAPI
  chunker.py             # heading-aware + code-block preserving chunks
  embeddings.py          # local hashing embeddings (offline-first)
  vector_store.py        # JSON-backed store
  retrieval.py           # semantic search + citations
  summarizer.py          # extractive summaries
  citations.py           # context blocks & inline cites
  knowledge_router.py    # /knowledge/* API
```

## API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/knowledge/import` | POST | Import file by path |
| `/knowledge/import-text` | POST | Import raw text |
| `/knowledge/import-dir` | POST | Import directory |
| `/knowledge/search` | POST | Semantic + keyword search |
| `/knowledge/list` | GET | List documents |
| `/knowledge/delete` | POST | Delete by doc_id |
| `/knowledge/reindex` | POST | Auto-index project docs |
| `/knowledge/status` | GET | Stats |

## Agent tools

- `search_knowledge` – ask the KB before answering / coding
- `import_documents` – add files or directories
- `summarize_document` – summarize by id or text
- `cite_sources` – formatted citations
- `search_project_docs` – README / CHANGELOG / ROADMAP / API focus

## Execution integration

Before code changes the loop can call:

```python
from backend.execution.ui_loop import knowledge_context_for_goal
ctx = knowledge_context_for_goal("implement JWT auth refresh")
# inject ctx into planner / agent prompt
```

## Auto project index

`import_project_docs()` / `POST /knowledge/reindex` indexes:

- README*, CHANGELOG*, ROADMAP*, ARCHITECTURE*
- `docs/**/*.md`
- Project memory notes (when Memory is available)

## Design notes

- Offline-first local embeddings (no mandatory vector DB or API key)
- Reuses Memory, Planner, Codebase Indexer, Browser, Vision, Execution, Agent
- Does not replace Codebase Indexer (code symbols) — complements it with prose docs
- Storage: `.lumora-knowledge/store.json`

## Optional

- `pypdf` for PDF text extraction
- API embeddings via providers if `use_api=True`
