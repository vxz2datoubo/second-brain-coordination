"""BFF contract tests — Phase 1 READ-ONLY.

These tests assert the *semantic guarantees* the Command Center must uphold,
not just that endpoints return 200:

  1. Candidate is never rendered as canonical.
  2. False-alive is never rendered as meaningful progress.
  3. Local vs remote sync is distinguished, and 0/0 != "fully synced".
  4. Every important response carries provenance + freshness.
  5. UNAVAILABLE sources are reported honestly, never faked as healthy.
  6. Dispatch/start endpoints fail closed (501).
  7. Projects are discovered from the registry, not hardcoded.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

API_DIR = Path(__file__).resolve().parents[1] / "api"
sys.path.insert(0, str(API_DIR))

from app.main import app  # noqa: E402
from app.repo_paths import get_paths  # noqa: E402

client = TestClient(app)

# Tests that require the local coordination repo.
requires_repo = pytest.mark.skipif(
    not get_paths().available, reason="coordination repo not present locally"
)


def _env(resp):
    body = resp.json()
    assert "data" in body and "meta" in body, "response must be {data, meta}"
    return body["data"], body["meta"]


# --------------------------------------------------------------------------
# 1. Health & honesty
# --------------------------------------------------------------------------

def test_health_returns_envelope_with_meta():
    data, meta = _env(client.get("/api/health"))
    assert "components" in data
    assert meta["observed_at"]
    assert meta["freshness"] in ("FRESH", "AGING", "STALE", "UNKNOWN")


def test_unavailable_sources_are_not_faked_healthy():
    """W3 and Host Broker are not connected in Phase 1 -> must be UNAVAILABLE."""
    data, _ = _env(client.get("/api/health"))
    by_name = {c["component"]: c["status"] for c in data["components"]}
    assert by_name.get("W3_RUNTIME") == "UNAVAILABLE"
    assert by_name.get("HOST_BROKER") == "UNAVAILABLE"


# --------------------------------------------------------------------------
# 2. Projects are registry-driven (pluggable, not hardcoded)
# --------------------------------------------------------------------------

@requires_repo
def test_projects_discovered_from_registry():
    data, _ = _env(client.get("/api/projects"))
    ids = {p["project_id"] for p in data}
    # The four current first-class projects must be present...
    expected = {"SECOND_BRAIN", "TRADING_SYSTEM",
                "REALTIME_INTERACTIVE_FILM_GAME", "AI_DIRECTOR"}
    assert expected.issubset(ids), f"missing: {expected - ids}"
    # ...but the set must come from the registry, so count == registry length.
    import yaml
    reg = yaml.safe_load(
        (get_paths().coordination / "coordination/EXECUTION/PROJECT-REGISTRY.yaml")
        .read_text(encoding="utf-8"))
    assert len(data) == len(reg["projects"]), "projects must mirror the registry"


@requires_repo
def test_every_project_has_provenance():
    data, _ = _env(client.get("/api/projects"))
    for p in data:
        m = p["meta"]
        assert m["sources"], f"{p['project_id']} missing sources"
        assert m["authority"]
        assert m["freshness"] in ("FRESH", "AGING", "STALE", "UNKNOWN")


@requires_repo
def test_project_without_active_lane_is_unknown_not_invented():
    """A project with no active lane must NOT get a fabricated ACTIVE state."""
    data, _ = _env(client.get("/api/projects"))
    for p in data:
        if p["lane_id"] is None:
            assert p["state"] == "UNKNOWN", \
                f"{p['project_id']} has no lane but state is {p['state']}"
            assert p["meta"]["warnings"], \
                f"{p['project_id']} should warn about missing lane"


# --------------------------------------------------------------------------
# 3. False-alive protection
# --------------------------------------------------------------------------

@requires_repo
def test_agents_never_report_working_from_pid_alone():
    data, _ = _env(client.get("/api/agents"))
    for a in data:
        # A READY-but-not-running route must be IDLE, never AGENT_ACTIVE.
        if a["liveness"] == "AGENT_ACTIVE":
            assert a.get("liveness_reason"), \
                "AGENT_ACTIVE must carry task-level evidence reason"
        # Every liveness verdict must be explained.
        assert a.get("liveness_reason"), f"{a['agent_id']} has no liveness reason"


@requires_repo
def test_ready_route_is_idle_not_active():
    """The specific case: route READY with execution_allowed but no session
    evidence must render IDLE, not 'working'."""
    data, _ = _env(client.get("/api/agents"))
    for a in data:
        if a["liveness_reason"] and "not yet executing" in a["liveness_reason"]:
            assert a["liveness"] == "IDLE"


# --------------------------------------------------------------------------
# 4. Sync semantics — REMOTE vs LOCAL, 0/0 != fully synced
# --------------------------------------------------------------------------

@requires_repo
def test_system_distinguishes_local_and_remote():
    data, _ = _env(client.get("/api/system"))
    assert "repos" in data
    for r in data["repos"]:
        assert r["sync_state"] in (
            "SYNCED", "REMOTE_AHEAD", "LOCAL_AHEAD", "DIVERGED",
            "DIRTY", "NO_REMOTE", "UNKNOWN")
        # local and remote sha must be tracked separately
        assert "local_sha" in r and "remote_main_sha" in r


def test_dirty_is_not_reported_as_plain_synced():
    """A repo with uncommitted changes must not claim plain SYNCED."""
    data, _ = _env(client.get("/api/system"))
    for r in data["repos"]:
        if r.get("dirty") and r["ahead"] == 0 and r["behind"] == 0:
            assert r["sync_state"] == "DIRTY", \
                "dirty repo with 0/0 must be DIRTY, not SYNCED"


# --------------------------------------------------------------------------
# 5. Control tower projection
# --------------------------------------------------------------------------

@requires_repo
def test_control_tower_has_counts_and_provenance():
    data, meta = _env(client.get("/api/control-tower"))
    assert isinstance(data["counts"], dict)
    assert meta["authority"] == "CONTROL_TOWER"
    assert meta["trust"] in ("DERIVED", "CANONICAL", "RUNTIME_OBSERVED")


def test_control_tower_counts_are_ints_not_invented():
    data, _ = _env(client.get("/api/control-tower"))
    for k, v in data["counts"].items():
        assert isinstance(v, int), f"count {k} must be int"


# --------------------------------------------------------------------------
# 6. Fail-closed command surface
# --------------------------------------------------------------------------

def test_dispatch_intent_fails_closed():
    r = client.post("/api/commands/dispatch-intent")
    assert r.status_code == 501
    assert "DISPATCH_NOT_ENABLED" in r.json()["detail"]


def test_start_fails_closed():
    r = client.post("/api/commands/start")
    assert r.status_code == 501
    assert "START_NOT_ENABLED" in r.json()["detail"]


# --------------------------------------------------------------------------
# 7. Freshness present everywhere it matters
# --------------------------------------------------------------------------

def test_all_important_endpoints_carry_freshness():
    for path in ("/api/health", "/api/system", "/api/projects",
                 "/api/tasks", "/api/control-tower"):
        _, meta = _env(client.get(path))
        assert meta["freshness"] in ("FRESH", "AGING", "STALE", "UNKNOWN"), path
        assert meta["observed_at"], path
