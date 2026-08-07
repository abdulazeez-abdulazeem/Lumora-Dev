"""
Lumora Dev – Database Router
Supports SQLite, with PostgreSQL/MySQL/MariaDB/Supabase connection framework.
"""
import sqlite3
import re
import json
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import logging

router = APIRouter()
logger = logging.getLogger("lumora.db")
ROOT = Path(__file__).resolve().parent.parent

def _safe_ident(name: str) -> str:
    """Allow only safe SQL identifiers (alphanumeric + underscore)."""
    if not name or not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name):
        raise HTTPException(status_code=400, detail=f"Invalid identifier: {name}")
    return name


# ── Connection store ────────────────────────────────────────────────────────
_CONNECTIONS = {}


def _get_db_path() -> Path:
    return ROOT / ".lumora-db.sqlite"


def _connect_sqlite(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _get_sqlite(conn_id: str = "default") -> sqlite3.Connection:
    if conn_id in _CONNECTIONS:
        return _CONNECTIONS[conn_id]
    path = _get_db_path()
    conn = _connect_sqlite(path)
    _CONNECTIONS[conn_id] = conn
    return conn


# ── Connection management ───────────────────────────────────────────────────
class ConnectionInfo(BaseModel):
    id: str = "default"
    type: str = "sqlite"
    name: str = "Local Database"
    host: str = ""
    port: int = 0
    database: str = ""
    username: str = ""
    password: str = ""
    url: str = ""


@router.get("/db/connections")
def list_connections():
    return {"connections": [{"id": "default", "type": "sqlite", "name": "Local SQLite"}]}


@router.post("/db/test")
def test_connection(req: ConnectionInfo):
    if req.type == "sqlite":
        try:
            path = ROOT / (req.database or ".lumora-db.sqlite")
            conn = sqlite3.connect(str(path))
            conn.execute("SELECT 1")
            conn.close()
            return {"ok": True}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    raise HTTPException(status_code=400, detail=f"Unsupported: {req.type}")


# ── Schema / Explorer ───────────────────────────────────────────────────────
@router.get("/db/tables")
def list_tables():
    conn = _get_sqlite()
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return {"tables": [r["name"] for r in rows]}


@router.get("/db/table/{table}")
def describe_table(table: str):
    table = _safe_ident(table)
    conn = _get_sqlite()
    try:
        info = conn.execute(f"PRAGMA table_info(\"{table}\")").fetchall()
    except sqlite3.OperationalError as e:
        raise HTTPException(status_code=404, detail=str(e))
    # Foreign keys
    fks = conn.execute(f"PRAGMA foreign_key_list(\"{table}\")").fetchall()
    # Indexes
    idxs = conn.execute(f"PRAGMA index_list(\"{table}\")").fetchall()
    # Count
    count = conn.execute(f"SELECT COUNT(*) as cnt FROM \"{table}\"").fetchone()

    columns = []
    for c in info:
        col = {
            "name": c["name"], "type": c["type"], "notnull": bool(c["notnull"]),
            "pk": bool(c["pk"]), "default": c["dflt_value"],
        }
        columns.append(col)

    return {
        "table": table,
        "columns": columns,
        "foreign_keys": [dict(f) for f in fks],
        "indexes": [dict(i) for i in idxs],
        "row_count": count["cnt"] if count else 0,
    }


# ── Query execution ─────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    sql: str
    conn_id: str = "default"


@router.post("/db/query")
def execute_query(req: QueryRequest):
    conn = _get_sqlite(req.conn_id)
    start = time.time()
    sql = req.sql.strip().rstrip(";")
    statements = [s.strip() for s in sql.split(";") if s.strip()]

    results = []
    for stmt in statements:
        try:
            cur = conn.execute(stmt)
            if stmt.upper().startswith(("SELECT", "PRAGMA", "EXPLAIN")):
                rows = [dict(r) for r in cur.fetchall()]
                cols = [d[0] for d in cur.description] if cur.description else []
                results.append({"type": "select", "columns": cols, "rows": rows, "count": len(rows)})
            else:
                conn.commit()
                results.append({"type": "write", "affected": cur.rowcount})
        except sqlite3.Error as e:
            results.append({"type": "error", "message": str(e)})

    elapsed = round((time.time() - start) * 1000, 1)
    return {"results": results, "elapsed_ms": elapsed, "statements": len(statements)}


# ── Sample data helper ──────────────────────────────────────────────────────
@router.get("/db/rows/{table}")
def get_rows(table: str, limit: int = 50, offset: int = 0, order: str = ""):
    table = _safe_ident(table)
    if order:
        order = _safe_ident(order)
    conn = _get_sqlite()
    try:
        order_clause = " ORDER BY " + order if order else ""
        rows = conn.execute(f"SELECT * FROM \"{table}\"{order_clause} LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        cols = [d[0] for d in conn.execute(f"PRAGMA table_info(\"{table}\")").fetchall()]
        total = conn.execute(f"SELECT COUNT(*) FROM \"{table}\"").fetchone()["COUNT(*)"]
        return {"columns": cols, "rows": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}
    except sqlite3.Error as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Saved queries / history ────────────────────────────────────────────────
_QUERY_HISTORY: list[dict] = []


@router.get("/db/history")
def query_history():
    return {"history": _QUERY_HISTORY[-50:]}


@router.post("/db/history")
def save_query(sql: QueryRequest):
    _QUERY_HISTORY.append({"sql": sql.sql, "time": time.strftime("%H:%M:%S")})
    if len(_QUERY_HISTORY) > 200:
        _QUERY_HISTORY.pop(0)
    return {"ok": True}
