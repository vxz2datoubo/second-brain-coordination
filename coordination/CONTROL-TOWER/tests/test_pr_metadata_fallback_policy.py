from pathlib import Path


def test_policy_keeps_native_connector_primary():
    doc = (Path(__file__).resolve().parents[1] / "PR-METADATA-FALLBACK-V1.md").read_text(encoding="utf-8")
    assert "Primary lane" in doc
    assert "Fallback lane" in doc
    assert "only after the primary lane returns a concrete transport/schema failure" in doc
