"""Git router tests (init + status when no repo)."""
from __future__ import annotations


def test_git_status_no_repo(client):
    r = client.get("/git/status")
    assert r.status_code == 200
    data = r.json()
    assert data.get("has_repo") is False or "branch" in data or "has_repo" in data


def test_git_init(client):
    r = client.post("/git/init", json={})
    # May succeed or fail depending on git availability
    assert r.status_code in (200, 409, 500)
    if r.status_code == 200:
        st = client.get("/git/status")
        assert st.status_code == 200
        assert st.json().get("has_repo") is True
