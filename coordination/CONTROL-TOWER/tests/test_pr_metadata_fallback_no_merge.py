from pathlib import Path


def test_tool_does_not_expose_merge_operation():
    source = (Path(__file__).resolve().parents[1] / "pr_metadata_fallback.py").read_text(encoding="utf-8")
    assert "grants_merge" in source
    assert "merge_pull_request" not in source
