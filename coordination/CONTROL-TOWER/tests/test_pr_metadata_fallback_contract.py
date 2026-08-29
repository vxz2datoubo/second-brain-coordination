from pathlib import Path


def test_contract_names_are_versioned():
    source = (Path(__file__).resolve().parents[1] / "pr_metadata_fallback.py").read_text(encoding="utf-8")
    assert "PR_METADATA_FALLBACK_RECEIPT/v1" in source
    assert "GH_OFFICIAL_GRAPHQL" in source
