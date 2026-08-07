"""File CRUD and path security tests."""
from __future__ import annotations


def test_list_files(client):
    r = client.get("/files")
    assert r.status_code == 200
    data = r.json()
    assert "files" in data
    assert isinstance(data["files"], list)


def test_write_and_read_file(client):
    r = client.post("/file", json={"path": "hello.txt", "content": "hello world"})
    assert r.status_code == 200
    r = client.get("/file", params={"path": "hello.txt"})
    assert r.status_code == 200
    assert r.json()["content"] == "hello world"


def test_create_folder(client):
    r = client.post("/files/create", json={"path": "mydir", "type": "folder"})
    assert r.status_code == 200


def test_path_traversal_blocked(client):
    r = client.get("/file", params={"path": "../etc/passwd"})
    assert r.status_code in (403, 400, 404)


def test_delete_file(client):
    client.post("/file", json={"path": "todelete.txt", "content": "x"})
    r = client.request("DELETE", "/file", json={"path": "todelete.txt"})
    assert r.status_code == 200


def test_rename_file(client):
    client.post("/file", json={"path": "oldname.txt", "content": "data"})
    r = client.put("/file", json={"old_path": "oldname.txt", "new_path": "newname.txt"})
    assert r.status_code == 200
    r = client.get("/file", params={"path": "newname.txt"})
    assert r.status_code == 200
