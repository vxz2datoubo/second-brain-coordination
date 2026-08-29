from pathlib import Path


def test_transport_uses_official_gh_api_and_not_git_or_curl():
    source = (Path(__file__).resolve().parents[1] / "pr_metadata_fallback.py").read_text(encoding="utf-8")
    assert '["gh", *args]' in source
    assert 'markPullRequestReadyForReview' in source
    assert 'curl ' not in source
    assert 'git push' not in source
    assert 'git commit' not in source
