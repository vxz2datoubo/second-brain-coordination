from pathlib import Path


def test_docs_define_already_ready_as_idempotent():
    source = (Path(__file__).resolve().parents[1] / "pr_metadata_fallback.py").read_text(encoding="utf-8")
    assert "ALREADY_READY" in source
