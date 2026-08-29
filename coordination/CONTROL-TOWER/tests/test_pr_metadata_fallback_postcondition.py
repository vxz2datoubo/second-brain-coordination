from pathlib import Path


def test_postcondition_requires_draft_false():
    source = (Path(__file__).resolve().parents[1] / "pr_metadata_fallback.py").read_text(encoding="utf-8")
    assert 'if after.get("draft"):' in source
    assert 'postcondition failed: PR remains draft' in source
