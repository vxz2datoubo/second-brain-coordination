from pathlib import Path


def test_cli_requires_explicit_repo_pr_and_expected_head():
    source = (Path(__file__).resolve().parents[1] / "pr_metadata_fallback.py").read_text(encoding="utf-8")
    for arg in ('--repo', '--pr', '--expected-head', '--operation'):
        assert arg in source
