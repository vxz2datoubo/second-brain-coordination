from pathlib import Path


def test_v1_scope_is_only_ready_transition():
    doc = (Path(__file__).resolve().parents[1] / "PR-METADATA-FALLBACK-V1.md").read_text(encoding="utf-8")
    assert "Only:" in doc
    assert "`mark_ready_for_review`" in doc
    assert "No merge, close, reopen, retarget" in doc
