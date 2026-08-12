from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch


PHASE_ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ROOT = PHASE_ROOT.parent
for source_root in (
    PHASE_ROOT / "src",
    PROGRAM_ROOT / "PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION" / "src",
    PROGRAM_ROOT / "PHASE-2-OFFLINE-VERTICAL-SLICE" / "src",
):
    sys.path.insert(0, str(source_root))

from integrated_offline_memory.cli import main
from integrated_offline_memory.memory_store import MemoryStore
from integrated_offline_memory.private_candidate_ingestion import (
    DAILY_MEMORY_CANDIDATE_TRANSPORT_V1,
    NO_ELIGIBLE_USER_MEMORY_CANDIDATES,
    PRIVATE_SOURCE_BINDING_CONFIGURED,
    PRIVATE_SOURCE_BINDING_REJECTED,
    PRIVATE_SOURCE_BINDING_WAITING,
    daily_memory_candidate_transport_to_w3_private_envelopes,
    daily_v2_package_to_w3_private_envelopes,
    ingest_daily_memory_candidate_v2,
    private_source_binding_status,
    serialize_daily_memory_candidate_v2_report,
    validate_private_data_paths,
)
from integrated_offline_memory.retrieval import ContextAssembler, QueryPlan


FIXTURE = PHASE_ROOT / "tests" / "fixtures" / "daily_memory_candidate_v2_enabled_contract.json"


def daily_v2_fixture() -> dict:
    """Public-safe compatibility fixture using enabled Daily-v2 report fields."""

    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class PrivateCandidateIngestionTestCase(unittest.TestCase):
    def test_enabled_daily_v2_contract_serializes_to_versioned_transport(self) -> None:
        transport = serialize_daily_memory_candidate_v2_report(daily_v2_fixture())
        self.assertEqual(transport["schema_version"], DAILY_MEMORY_CANDIDATE_TRANSPORT_V1)
        self.assertEqual(transport["coverage"]["coverage"], "PARTIAL")
        self.assertEqual(len(transport["coverage"]["excluded_or_unknown_sources"]), 1)
        envelopes, no_ops = daily_memory_candidate_transport_to_w3_private_envelopes(transport)
        self.assertEqual(len(envelopes), 1)
        self.assertEqual(len(envelopes[0]["source_episodes"]), 2)
        self.assertEqual(no_ops[0]["reason"], "OUT_OF_SCOPE_CANDIDATE_TYPE")
        self.assertEqual(len(daily_v2_package_to_w3_private_envelopes(daily_v2_fixture())), 1)

    def test_exact_recall_and_aggregate_duplicate_receipt(self) -> None:
        store = MemoryStore().connect()
        try:
            first = ingest_daily_memory_candidate_v2(daily_v2_fixture(), store)
            receipt = first.public_receipt()
            self.assertEqual(receipt["status"], "IMPORTED")
            self.assertEqual(receipt["imported_count"], 1)
            self.assertEqual(receipt["duplicate_count"], 0)
            self.assertTrue(receipt["exact_imported_atom_recalled"])
            self.assertNotIn("statement", receipt)
            second = ingest_daily_memory_candidate_v2(daily_v2_fixture(), store)
            replay = second.public_receipt()
            self.assertEqual(replay["status"], "IDEMPOTENT_DUPLICATE")
            self.assertEqual(replay["imported_count"], 0)
            self.assertEqual(replay["duplicate_count"], 1)
            decoy_only = Mock()
            decoy_only.assemble.return_value = type("Bundle", (), {"atoms": ({"id": "preexisting-decoy"},)})()
            with self.assertRaisesRegex(ValueError, "exact_recall_not_proven"):
                ingest_daily_memory_candidate_v2(daily_v2_fixture(), store, context_assembler=decoy_only)
        finally:
            store.close()

    def test_multi_candidate_receipt_aggregates_actual_results(self) -> None:
        package = daily_v2_fixture()
        package["MEMORY_CANDIDATES"].append({
            "candidate_id": "opaque-user-decision-003", "candidate_type": "USER_DECISION",
            "statement": "synthetic local decision marker",
            "supporting_episode_ids": ["opaque-user-episode-002"],
            "valid_from": "2026-08-12T00:00:00+08:00", "valid_to": None,
            "recorded_at": "2026-08-12T00:03:00+08:00", "sensitivity_class": "PRIVATE_OR_SENSITIVE",
            "correction_target": None,
        })
        package["DERIVED_DAILY_PROJECTION"]["supporting_candidate_ids"].append("opaque-user-decision-003")
        package["VALIDATION"]["candidate_dispositions"]["opaque-user-decision-003"] = "ACCEPTED"
        package["VALIDATION"]["sensitivity_by_candidate"]["opaque-user-decision-003"] = "PRIVATE_OR_SENSITIVE"
        store = MemoryStore().connect()
        try:
            receipt = ingest_daily_memory_candidate_v2(package, store).public_receipt()
            self.assertEqual(receipt["status"], "IMPORTED")
            self.assertEqual(receipt["candidate_count"], 2)
            self.assertEqual(receipt["imported_count"], 2)
            self.assertEqual(receipt["duplicate_count"], 0)
        finally:
            store.close()

    def test_non_user_or_zero_eligible_report_is_safe_noop_not_invalid(self) -> None:
        package = daily_v2_fixture()
        package["VALIDATION"]["candidate_dispositions"]["opaque-user-memory-001"] = "NON_DURABLE"
        store = MemoryStore().connect()
        try:
            result = ingest_daily_memory_candidate_v2(package, store)
            self.assertEqual(result.packets, ())
            receipt = result.public_receipt()
            self.assertEqual(receipt["status"], NO_ELIGIBLE_USER_MEMORY_CANDIDATES)
            self.assertEqual(receipt["candidate_count"], 0)
            self.assertEqual(receipt["non_imported_count"], 2)
            self.assertEqual(store.stats()["atoms"], 0)
        finally:
            store.close()

    def test_user_correction_uses_canonical_supersession_current_historical(self) -> None:
        store = MemoryStore().connect()
        try:
            original = ingest_daily_memory_candidate_v2(daily_v2_fixture(), store)
            old_id = original.packets[0]["atoms"][0]["id"]
            correction = daily_v2_fixture()
            correction["CONVERSATION_EPISODES"].append({
                "episode_id": "opaque-user-correction-004", "observed_at": "2026-08-12T02:00:00+08:00",
                "valid_time": "2026-08-12T02:00:00+08:00", "speaker": "USER",
                "source_scope": {"user_scope": "opaque-user-a", "project_scope": "opaque-project-a"},
                "source_ref": "local-private://opaque-fixture/user-004",
                "provenance": {"kind": "private-local", "opaque_ref": "source-d"},
                "provenance_quality": "DIRECT", "summary": "synthetic correction"
            })
            correction["MEMORY_CANDIDATES"] = [{
                "candidate_id": "opaque-user-correction-001", "candidate_type": "USER_CORRECTION",
                "statement": "synthetic corrected preference marker",
                "supporting_episode_ids": ["opaque-user-correction-004"],
                "valid_from": "2026-08-12T02:00:00+08:00", "valid_to": None,
                "recorded_at": "2026-08-12T02:00:00+08:00", "sensitivity_class": "PRIVATE_OR_SENSITIVE",
                "correction_target": {"replaces_atom_id": old_id, "relation_provenance": "daily-v2-user-correction"}
            }]
            correction["DERIVED_DAILY_PROJECTION"]["supporting_episode_ids"] = ["opaque-user-correction-004"]
            correction["DERIVED_DAILY_PROJECTION"]["supporting_candidate_ids"] = ["opaque-user-correction-001"]
            correction["VALIDATION"]["candidate_dispositions"] = {"opaque-user-correction-001": "ACCEPTED"}
            correction["VALIDATION"]["sensitivity_by_candidate"] = {"opaque-user-correction-001": "PRIVATE_OR_SENSITIVE"}
            result = ingest_daily_memory_candidate_v2(correction, store)
            correction_id = result.packets[0]["atoms"][0]["id"]
            self.assertEqual(result.packets[0]["relations"][0]["context"], "daily-v2-user-correction")
            current = ContextAssembler(store).assemble(QueryPlan(
                query_text="synthetic", scopes=("opaque-project-a",), user_scope="opaque-user-a",
                valid_at="2026-08-12T03:00:00+08:00", truth_states=("candidate",), intent="CURRENT",
            ))
            self.assertEqual({atom["id"] for atom in current.atoms}, {correction_id})
            historical = ContextAssembler(store).assemble(QueryPlan(
                query_text="preference", scopes=("opaque-project-a",), user_scope="opaque-user-a",
                valid_at="2026-08-12T01:00:00+08:00", truth_states=("candidate", "superseded"), intent="HISTORICAL",
            ))
            self.assertIn(old_id, {atom["id"] for atom in historical.atoms})
        finally:
            store.close()

    def test_multi_episode_provenance_is_visible_in_context_bundle(self) -> None:
        store = MemoryStore().connect()
        try:
            result = ingest_daily_memory_candidate_v2(daily_v2_fixture(), store)
            bundle = ContextAssembler(store).assemble(QueryPlan(
                query_text="preference", scopes=("opaque-project-a",), user_scope="opaque-user-a",
                valid_at="2026-08-12T01:00:00+08:00", truth_states=("candidate",),
            ))
            self.assertEqual(len(bundle.provenance), 1)
            provenance = bundle.provenance[0]["source_episodes"]
            expected = result.packets[0]["atoms"][0]["memory_metadata"]["conversation"]["source_episodes"]
            self.assertEqual(provenance, expected)
            self.assertEqual({item["episode_id"] for item in provenance}, {"opaque-user-episode-001", "opaque-user-episode-002"})
            self.assertTrue(all("source_pointer" not in item for item in provenance))
        finally:
            store.close()

    def test_validation_sensitivity_and_actor_gate_fail_closed(self) -> None:
        for sensitivity in ("PASSWORD", "API_KEY", "TOKEN", "COOKIE", "SESSION_CREDENTIAL", "MFA_OTP", "RECOVERY_CODE", "PAYMENT_CREDENTIAL", "BANK_CREDENTIAL", "BROKER_CREDENTIAL", "SECRET_CREDENTIAL"):
            package = daily_v2_fixture()
            package["MEMORY_CANDIDATES"][0]["sensitivity_class"] = sensitivity
            package["VALIDATION"]["sensitivity_by_candidate"]["opaque-user-memory-001"] = sensitivity
            with self.assertRaisesRegex(ValueError, "secret_or_sensitive_candidate_denied"):
                daily_v2_package_to_w3_private_envelopes(package)
        actor = daily_v2_fixture()
        actor["CONVERSATION_EPISODES"][0]["speaker"] = "ASSISTANT"
        with self.assertRaisesRegex(ValueError, "candidate_actor_denied"):
            daily_v2_package_to_w3_private_envelopes(actor)

    def test_private_data_root_cli_and_source_state_are_path_redacted(self) -> None:
        public_input, public_store = PHASE_ROOT / "public-fixture.json", PHASE_ROOT / "public-fixture.db"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, store = root / "candidate.json", root / "candidate.db"
            self.assertEqual(validate_private_data_paths(source, store, root)[:2], (source.resolve(), store.resolve()))
            with self.assertRaisesRegex(ValueError, "path_policy_denied"):
                validate_private_data_paths(public_input, store, root)
            source.write_text(json.dumps(daily_v2_fixture()), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["private-ingest", "--input", str(source), "--store", str(store), "--private-root", str(root)]), 0)
            self.assertNotIn(str(root), output.getvalue())
            self.assertEqual(private_source_binding_status({})["status"], PRIVATE_SOURCE_BINDING_WAITING)
            missing = root / "missing.json"
            waiting = private_source_binding_status({"CLTM_PRIVATE_DATA_ROOT": str(root), "CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH": str(missing)})
            self.assertEqual(waiting["status"], PRIVATE_SOURCE_BINDING_WAITING)
            invalid = root / "invalid.json"
            invalid.write_text("{not-json", encoding="utf-8")
            rejected = private_source_binding_status({"CLTM_PRIVATE_DATA_ROOT": str(root), "CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH": str(invalid)})
            self.assertEqual(rejected["status"], PRIVATE_SOURCE_BINDING_REJECTED)
            configured = private_source_binding_status({"CLTM_PRIVATE_DATA_ROOT": str(root), "CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH": str(source)})
            self.assertEqual(configured["status"], PRIVATE_SOURCE_BINDING_CONFIGURED)
            self.assertNotIn(str(source), json.dumps(configured))


if __name__ == "__main__":
    unittest.main()
