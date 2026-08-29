from pathlib import Path


def test_primary_path_is_preferred_in_plan():
    plan = (Path(__file__).resolve().parents[1] / "PR-METADATA-FALLBACK-PLAN.md").read_text(encoding="utf-8")
    assert "best/fastest/highest-value path" in plan
    assert "fallback only when the primary native path is concretely unavailable" in plan
