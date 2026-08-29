from pathlib import Path


def test_runtime_has_no_contents_or_ref_write_commands():
    source = (Path(__file__).resolve().parents[1] / "pr_metadata_fallback.py").read_text(encoding="utf-8")
    forbidden = ["repos/{repository}/contents", "git/refs", "merge", "update_ref", "create_file"]
    for token in forbidden:
        assert token not in source
