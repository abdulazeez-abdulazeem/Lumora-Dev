"""Database router tests."""
from __future__ import annotations


def test_list_tables(client):
    r = client.get("/db/tables")
    assert r.status_code == 200
    assert "tables" in r.json()


def test_query_select(client):
    r = client.post("/db/query", json={"sql": "SELECT 1 AS n"})
    assert r.status_code == 200
    data = r.json()
    assert "results" in data


def test_invalid_table_ident(client):
    r = client.get("/db/table/bad;drop")
    assert r.status_code == 400


def test_history(client):
    r = client.get("/db/history")
    assert r.status_code == 200
    assert "history" in r.json()
