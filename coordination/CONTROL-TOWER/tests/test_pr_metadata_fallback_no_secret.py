from pathlib import Path


def test_fallback_has_no_embedded_token_or_secret_material():
    root = Path(__file__).resolve().parents[1]
    text = (root / "pr_metadata_fallback.py").read_text(encoding="utf-8")
    assert "GITHUB_TOKEN=" not in text
    assert "ghp_" not in text
    assert "github_pat_" not in text
    assert "Authorization: Bearer" not in text
    assert "Authorization: token" not in text
