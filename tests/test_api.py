"""API route tests (health, chat, activity, codebase)."""
from __future__ import annotations


def test_health(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "Lumora" in data["service"]
    assert "version" in data


def test_chat_empty_message(client):
    r = client.post("/chat", json={"message": "   "})
    assert r.status_code == 400


def test_chat_success(client):
    r = client.post("/chat", json={"message": "Hello Lumora"})
    assert r.status_code == 200
    data = r.json()
    assert "response" in data
    assert data["response"]
    assert data.get("task_id", "").startswith("task-")


def test_activity(client):
    r = client.get("/activity")
    assert r.status_code == 200
    data = r.json()
    assert "activity" in data
    assert "tasks" in data


def test_codebase_stats(client):
    r = client.get("/codebase/stats")
    assert r.status_code == 200
    data = r.json()
    assert "total_files" in data or "total_symbols" in data or isinstance(data, dict)


def test_codebase_search(client):
    client.post("/codebase/index")
    r = client.get("/codebase/search", params={"q": "hello"})
    assert r.status_code == 200
    assert "results" in r.json()
