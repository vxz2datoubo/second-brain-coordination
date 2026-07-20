from __future__ import annotations

import json
from pathlib import Path
import unittest

from contract_validation import ContractViolation, compatible_version, validate_approval, validate_capability, validate_replay_envelope, validate_temporal


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "FIXTURES"
SCHEMAS = [
    "FOUNDATION-SHARED-ENVELOPE.schema.json",
    "TEMPORAL-SEMANTICS-CONTRACT.schema.json",
    "LINEAGE-EVIDENCE-QUALITY-CONTRACT.schema.json",
    "CAPABILITY-ENTITLEMENT-CONTRACT.schema.json",
    "APPROVAL-ABSTENTION-ROLLBACK-CONTRACT.schema.json",
]


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FoundationContractTests(unittest.TestCase):
    def test_all_schemas_are_parseable_and_declare_ids(self):
        for name in SCHEMAS:
            schema = json.loads((ROOT / name).read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertTrue(schema["$id"].endswith("/1.0.0"))
            self.assertTrue(schema["required"])

    def test_valid_offline_replay_envelope_passes_all_gates(self):
        validate_replay_envelope(load_fixture("valid-offline-replay-envelope.json"))

    def test_available_at_blocks_future_data_leakage(self):
        with self.assertRaisesRegex(ContractViolation, "future data leakage"):
            validate_temporal(load_fixture("future-available-at.json"))

    def test_unknown_entitlement_cannot_be_allowed(self):
        with self.assertRaisesRegex(ContractViolation, "confirmed entitlement"):
            validate_capability(load_fixture("missing-capability.json"))

    def test_candidate_cannot_write_authority(self):
        with self.assertRaisesRegex(ContractViolation, "candidate cannot write authority"):
            validate_approval(load_fixture("candidate-authority-write.json"))

    def test_no_trade_gate_is_machine_enforced(self):
        with self.assertRaisesRegex(ContractViolation, "no_trade_gate"):
            validate_approval(load_fixture("invalid-no-trade.json"))

    def test_irreversible_change_requires_approval(self):
        with self.assertRaisesRegex(ContractViolation, "human_approval_ref"):
            validate_approval(load_fixture("irreversible-without-approval.json"))

    def test_rollback_pointer_is_required(self):
        with self.assertRaisesRegex(ContractViolation, "rollback_pointer"):
            validate_approval(load_fixture("missing-rollback-pointer.json"))

    def test_execution_action_is_prohibited(self):
        with self.assertRaisesRegex(ContractViolation, "execution is prohibited"):
            validate_approval(load_fixture("prohibited-execution-action.json"))

    def test_major_version_is_not_silently_accepted(self):
        self.assertTrue(compatible_version("1.0.0"))
        self.assertTrue(compatible_version("1.4.9"))
        self.assertFalse(compatible_version("2.0.0"))
        self.assertFalse(compatible_version("not-a-version"))

    def test_compatibility_matrix_records_explicit_decisions(self):
        matrix = (ROOT / "EXISTING-TYPE-COMPATIBILITY-MATRIX.yaml").read_text(encoding="utf-8")
        for type_name in ("MarketDataRecord", "DataLineageRecord", "CapabilityDescriptor", "RawMarketPayload"):
            self.assertIn(type_name, matrix)
        self.assertIn("no_dual_authority_rule", matrix)
        self.assertIn("action: UNKNOWN", matrix)

    def test_schema_files_declare_the_machine_gates(self):
        temporal = json.loads((ROOT / "TEMPORAL-SEMANTICS-CONTRACT.schema.json").read_text(encoding="utf-8"))
        capability = json.loads((ROOT / "CAPABILITY-ENTITLEMENT-CONTRACT.schema.json").read_text(encoding="utf-8"))
        approval = json.loads((ROOT / "APPROVAL-ABSTENTION-ROLLBACK-CONTRACT.schema.json").read_text(encoding="utf-8"))
        self.assertIn("available_at", temporal["required"])
        self.assertIn("entitlement_status", capability["required"])
        self.assertEqual(approval["properties"]["no_trade_gate"], {"const": True})


if __name__ == "__main__":
    unittest.main()
