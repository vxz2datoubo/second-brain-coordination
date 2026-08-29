from pathlib import Path


def test_cli_operation_enumeration_is_singleton():
    source = (Path(__file__).resolve().parents[1] / "pr_metadata_fallback.py").read_text(encoding="utf-8")
    assert source.count('choices=["mark_ready_for_review"]') == 1
