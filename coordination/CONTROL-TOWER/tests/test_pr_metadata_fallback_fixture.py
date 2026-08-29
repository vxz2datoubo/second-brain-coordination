import json
from pathlib import Path


def test_receipt_fixture_has_all_false_authority_and_exact_head_stability():
    path = Path(__file__).resolve().parent / "fixtures" / "pr_metadata_fallback_receipt_example.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema"] == "PR_METADATA_FALLBACK_RECEIPT/v1"
    assert data["operation"] == "mark_ready_for_review"
    assert data["before_head"] == data["expected_head"] == data["after_head"]
    assert data["before_draft"] is True
    assert data["after_draft"] is False
    assert all(value is False for value in data["authority"].values())
