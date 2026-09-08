import importlib.util
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
GOV = ROOT / "coordination" / "GOVERNANCE"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CanonicalizationGovernanceIntegrationTests(unittest.TestCase):
    def test_canonical_validator_exports_effect_contracts(self):
        mod = load_module(
            "unified_execution_validation_canonicalization_test",
            GOV / "unified_execution_validation.py",
        )
        for name in (
            "build_contributor_conflict_set",
            "admit_canonicalizer",
            "validate_pre_merge_effect_gate",
            "reconcile_merge_effect",
            "validate_pr615_prospective_adjudication",
        ):
            self.assertTrue(callable(getattr(mod, name)))
        self.assertFalse(mod.CANONICALIZATION_EFFECT_CORE_HAS_GITHUB_SIDE_EFFECTS)
        self.assertFalse(mod.CANONICALIZATION_EFFECT_CORE_CAN_MINT_MERGE_AUTHORITY)

    def test_fresh_trust_gate_reexports_same_validator_types(self):
        gate = load_module(
            "unified_execution_trust_gate_canonicalization_test",
            GOV / "unified_execution_trust_gate.py",
        )
        self.assertIs(gate.CanonicalizerAdmission, gate.base.CanonicalizerAdmission)
        self.assertIs(gate.VerifiedCanonicalizerEvidence, gate.base.VerifiedCanonicalizerEvidence)
        self.assertIs(gate.validate_pre_merge_effect_gate, gate.base.validate_pre_merge_effect_gate)
        self.assertIs(gate.reconcile_merge_effect, gate.base.reconcile_merge_effect)

    def test_uef_requires_effect_provenance_and_forbids_author_fallback(self):
        text = (GOV / "UNIFIED-AGENT-EXECUTION-FABRIC-v1.0.yaml").read_text(encoding="utf-8")
        required = (
            "CANONICALIZATION_EFFECT_PROVENANCE",
            "no_author_or_orchestrator_merge_fallback_on_canonicalizer_failure: true",
            "canonicalization_effect_provenance_required: true",
            "HEAD_LOCK_ONLY_NOT_ATOMIC_BASE_AND_HEAD_CAS",
            "SELECT_ELIGIBLE_CANONICALIZER",
            "REMOTE_EFFECT_RECONCILED",
        )
        for marker in required:
            self.assertIn(marker, text)

    def test_interface_schema_separates_verifier_request_actor_and_github_actor(self):
        text = (GOV / "UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml").read_text(encoding="utf-8")
        for marker in (
            "CANONICALIZER_ROLE_AND_CAPABILITY_ADMISSION_v1",
            "CANONICALIZATION_EFFECT_REQUEST_v1",
            "CANONICALIZATION_EFFECT_RECEIPT_v1",
            "gate_verifier_merge_request_actor_github_actor_and_publisher_are_distinct_fields",
            "author_or_orchestrator_fallback_merge_is_forbidden",
        ):
            self.assertIn(marker, text)

    def test_fresh_trust_contract_preserves_operational_unknown(self):
        text = (GOV / "UNIFIED-EXECUTION-FRESH-TRUST-GATE-v1.0.yaml").read_text(encoding="utf-8")
        for marker in (
            "NO_AUTHOR_OR_ORCHESTRATOR_CANONICAL_MERGE_FALLBACK",
            "NO_CALLER_MINTED_CANONICALIZER_INDEPENDENCE_OR_WRITE_CAPABILITY",
            "OPERATIONAL_ENFORCEMENT_UNPROVEN",
            "HEAD_ONLY_NOT_BASE_AND_HEAD_ATOMIC_CAS",
        ):
            self.assertIn(marker, text)

    def test_pr615_decision_file_is_prospective_not_retroactive(self):
        path = GOV / "DECISIONS" / "PR615-POST-MERGE-ADJUDICATION-v1.yaml"
        text = path.read_text(encoding="utf-8")
        exact = {
            "accepted_exact_head": "61ff56f1f1ad9c84e40bb68b3860a10bd1d6befb",
            "pre_merge_main": "e6c5c1e019e652650e9e55c9b4fad2431ffcd8ac",
            "original_merge_commit": "5967215d1efb2831bcb60e13f483fed88ecbb226",
            "accepted_candidate_tree": "26256afce26dbedcccd4cca7b8214347f3ee21fc",
            "merged_tree": "26256afce26dbedcccd4cca7b8214347f3ee21fc",
        }
        for key, value in exact.items():
            self.assertRegex(text, rf"(?m)^{re.escape(key)}:\s+{value}$")
        self.assertRegex(
            text,
            r"(?m)^historical_merge_procedure:\s+GOVERNANCE_DEFECT_SELF_MERGE$",
        )
        self.assertRegex(
            text,
            r"(?m)^original_merge_authorization_retroactively_granted:\s+false$",
        )
        self.assertRegex(text, r"(?m)^r187_reactivation_authorized:\s+false$")
        self.assertRegex(text, r"(?m)^rollback_default:\s+false$")


if __name__ == "__main__":
    unittest.main()
