from pathlib import Path


def test_documentation_requires_post_mutation_readback():
    doc = (Path(__file__).resolve().parents[1] / "PR-METADATA-FALLBACK-V1.md").read_text(encoding="utf-8")
    assert "fresh PR readback is mandatory" in doc
    assert "receipt is execution evidence only" in doc
