"""Tests for Deployment & DevOps (v4.0)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def mgr(tmp_path):
    from backend.deployment.deployment_manager import DeploymentManager
    return DeploymentManager(storage_dir=str(tmp_path / "deploy"))


def test_platforms(mgr):
    plats = mgr.platforms()
    names = {p["name"] for p in plats}
    assert "static" in names
    assert "docker" in names
    assert "vercel" in names
    assert "netlify" in names
    assert "railway" in names
    assert "render" in names


def test_build(mgr, tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi\n")
    result = mgr.build(str(tmp_path))
    assert result["build_id"]
    assert result["status"] in ("success", "failed")
    assert result["duration_ms"] >= 0


def test_static_deploy(mgr, tmp_path):
    (tmp_path / "index.html").write_text("<html><body>Hi</body></html>")
    result = mgr.deploy(platform="static", project_dir=str(tmp_path), build_first=True)
    assert result["deployment_id"]
    assert result["status"] in ("success", "dry_run", "failed")
    assert result["platform"] == "static"


def test_cloud_dry_run(mgr, tmp_path):
    result = mgr.deploy(platform="vercel", project_dir=str(tmp_path), build_first=False)
    assert result["status"] in ("dry_run", "queued", "success")
    assert result["platform"] == "vercel"


def test_history_and_status(mgr, tmp_path):
    mgr.deploy(platform="static", project_dir=str(tmp_path), build_first=False)
    hist = mgr.history()
    assert len(hist) >= 1
    st = mgr.status()
    assert st["total"] >= 1


def test_rollback(mgr, tmp_path):
    dep = mgr.deploy(platform="static", project_dir=str(tmp_path), build_first=False)
    snaps = mgr.snapshots()
    assert len(snaps) >= 1
    sid = snaps[-1]["snapshot_id"]
    rb = mgr.rollback(sid)
    assert rb["success"] is True


def test_environments(mgr):
    profiles = mgr.envs.list_profiles()
    assert "development" in profiles
    assert "production" in profiles
    mgr.envs.set("staging", {"API_URL": "https://staging.example"})
    assert mgr.envs.get("staging")["API_URL"] == "https://staging.example"


def test_secrets(mgr):
    mgr.secrets.set("VERCEL_TOKEN", "test-token")
    assert mgr.secrets.get("VERCEL_TOKEN") == "test-token"
    assert "VERCEL_TOKEN" in mgr.secrets.list_keys()


def test_logs(mgr, tmp_path):
    b = mgr.build(str(tmp_path))
    logs = mgr.logs(build_id=b["build_id"])
    assert "logs" in logs


def test_monitor_health(mgr):
    h = mgr.monitor.health_check("file:///tmp")
    assert h["ok"] is True


def test_router_routes():
    from backend.deployment.deployment_router import router
    paths = [getattr(r, "path", "") for r in router.routes]
    for need in ("build", "deploy", "status", "history", "logs", "rollback", "platforms"):
        assert any(need in p for p in paths), need


def test_agent_tools_in_source():
    src = (ROOT / "agent.py").read_text()
    assert "deploy_app" in src
    assert "build_project" in src
    assert "rollback_deployment" in src


def test_multiagent_workflow(mgr, tmp_path):
    (tmp_path / "index.html").write_text("<html>ok</html>")
    wf = mgr.multiagent_deploy_workflow("ship static site", platform="static", project_dir=str(tmp_path))
    assert "steps" in wf
    assert wf.get("success") is True or any("deploy" in str(s) for s in wf["steps"])
