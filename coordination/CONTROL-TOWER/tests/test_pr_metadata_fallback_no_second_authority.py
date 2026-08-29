from pathlib import Path


def test_docs_explicitly_forbid_second_governance_system():
    doc = (Path(__file__).resolve().parents[1] / "PR-METADATA-FALLBACK-V1.md").read_text(encoding="utf-8")
    assert "not a second governance system" in doc
    assert "cannot authorize merge or review acceptance" in doc
