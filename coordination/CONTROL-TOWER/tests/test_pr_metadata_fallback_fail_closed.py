from pathlib import Path


def test_fail_closed_surface_is_explicit():
    source = (Path(__file__).resolve().parents[1] / "pr_metadata_fallback.py").read_text(encoding="utf-8")
    assert '"status": "FAIL_CLOSED"' in source
