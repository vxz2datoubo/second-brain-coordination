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
from integrated_offline_memory.canonical import content_hash
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


def correction_package(*, candidate_id: str, replaces_candidate_id: str, episode_id: str) -> dict:
    package = daily_v2_fixture()
    package["CONVERSATION_EPISODES"].append({
        "episode_id": episode_id, "observed_at": "2026-08-12T02:00:00+08:00",
        "valid_time": "2026-08-12T02:00:00+08:00", "speaker": "USER",
        "source_scope": {"user_scope": "opaque-user-a", "project_scope": "opaque-project-a"},
        "source_ref": "local-private://opaque-fixture/" + episode_id,
        "provenance": {"kind": "private-local", "opaque_ref": episode_id},
        "provenance_quality": "DIRECT", "summary": "synthetic correction",
    })
    package["MEMORY_CANDIDATES"] = [{
        "candidate_id": candidate_id, "candidate_type": "USER_CORRECTION",
        "statement": "synthetic corrected preference " + candidate_id,
        "supporting_episode_ids": [episode_id], "valid_from": "2026-08-12T02:00:00+08:00",
        "valid_to": None, "recorded_at": "2026-08-12T02:00:00+08:00",
        "sensitivity_class": "PRIVATE_OR_SENSITIVE",
        "correction_target": {"replaces_candidate_id": replaces_candidate_id, "relation_provenance": "daily-v2-user-correction"},
    }]
    package["DERIVED_DAILY_PROJECTION"]["supporting_episode_ids"] = [episode_id]
    package["DERIVED_DAILY_PROJECTION"]["supporting_candidate_ids"] = [candidate_id]
    package["VALIDATION"]["candidate_dispositions"] = {candidate_id: "ACCEPTED"}
    package["VALIDATION"]["sensitivity_by_candidate"] = {candidate_id: "PRIVATE_OR_SENSITIVE"}
    return package


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
            # Read only for the final historic assertion; the producer-side
            # correction payload below uses its own known candidate identity.
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
                "correction_target": {"replaces_candidate_id": "opaque-user-memory-001", "relation_provenance": "daily-v2-user-correction"}
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

    def test_report_variants_confidence_and_episode_evidence_survive(self) -> None:
        package = daily_v2_fixture()
        package.pop("schema_version")
        package["COVERAGE"]["coverage"] = "partial"
        episode = package["CONVERSATION_EPISODES"][0]
        episode["actor"] = episode.pop("speaker")
        episode.pop("source_ref")
        episode["provenance"] = {"opaque_ref": "provenance-only"}
        package["MEMORY_CANDIDATES"][0]["confidence"] = "HIGH"
        package["VALIDATION"].pop("candidate_dispositions")
        package["VALIDATION"]["accepted_candidate_ids"] = ["opaque-user-memory-001", "opaque-project-state-002"]
        package["VALIDATION"]["rejected_candidates"] = []
        package["VALIDATION"].pop("sensitivity_by_candidate")
        transport = serialize_daily_memory_candidate_v2_report(package)
        self.assertEqual(transport["coverage"]["coverage"], "PARTIAL")
        self.assertEqual(transport["candidates"][0]["confidence"], 0.9)
        store = MemoryStore().connect()
        try:
            result = ingest_daily_memory_candidate_v2(package, store)
            bundle = ContextAssembler(store).assemble(QueryPlan(
                query_text="preference", scopes=("opaque-project-a",), user_scope="opaque-user-a",
                valid_at="2026-08-12T01:00:00+08:00", truth_states=("candidate",),
            ))
            self.assertEqual(bundle.atoms[0]["confidence"], 0.9)
            evidence = bundle.provenance[0]["source_episodes"]
            self.assertTrue(all(item["valid_time"].endswith("Z") for item in evidence))
            self.assertTrue(all(item["provenance_quality"] for item in evidence))
            self.assertEqual(result.packets[0]["atoms"][0]["memory_metadata"]["conversation"]["candidate_confidence"], 0.9)
        finally:
            store.close()

    def test_preflight_invalid_correction_leaves_no_partial_mutation(self) -> None:
        package = daily_v2_fixture()
        package["MEMORY_CANDIDATES"].append({
            "candidate_id": "opaque-invalid-correction", "candidate_type": "USER_CORRECTION",
            "statement": "synthetic invalid correction", "supporting_episode_ids": ["opaque-user-episode-002"],
            "valid_from": "2026-08-12T02:00:00+08:00", "valid_to": None,
            "recorded_at": "2026-08-12T02:00:00+08:00", "sensitivity_class": "PRIVATE_OR_SENSITIVE",
            "correction_target": {"replaces_candidate_id": "missing-producer-id", "relation_provenance": "synthetic"},
        })
        package["DERIVED_DAILY_PROJECTION"]["supporting_candidate_ids"].append("opaque-invalid-correction")
        package["VALIDATION"]["candidate_dispositions"]["opaque-invalid-correction"] = "ACCEPTED"
        package["VALIDATION"]["sensitivity_by_candidate"]["opaque-invalid-correction"] = "PRIVATE_OR_SENSITIVE"
        store = MemoryStore().connect()
        try:
            with self.assertRaisesRegex(ValueError, "correction_target_unresolved"):
                ingest_daily_memory_candidate_v2(package, store)
            self.assertEqual(store.stats()["atoms"], 0)
            self.assertEqual(store.stats()["packets"], 0)
        finally:
            store.close()

    def test_candidate_missing_times_use_only_its_supporting_episode_or_fail_closed(self) -> None:
        package = daily_v2_fixture()
        candidate = package["MEMORY_CANDIDATES"][0]
        candidate["supporting_episode_ids"] = ["opaque-user-episode-002"]
        candidate.pop("valid_from")
        candidate.pop("recorded_at")
        transport = serialize_daily_memory_candidate_v2_report(package)
        normalized = transport["candidates"][0]
        self.assertEqual(normalized["valid_from"], "2026-08-11T16:02:00Z")
        self.assertEqual(normalized["recorded_at"], "2026-08-11T16:02:00Z")
        ambiguous = daily_v2_fixture()
        ambiguous["MEMORY_CANDIDATES"][0].pop("valid_from")
        ambiguous["MEMORY_CANDIDATES"][0].pop("recorded_at")
        with self.assertRaisesRegex(ValueError, "candidate_time_ambiguous"):
            serialize_daily_memory_candidate_v2_report(ambiguous)

    def test_correction_lifecycle_conflicts_leave_daily_package_store_unchanged(self) -> None:
        store = MemoryStore().connect()
        try:
            ingest_daily_memory_candidate_v2(daily_v2_fixture(), store)
            ingest_daily_memory_candidate_v2(correction_package(
                candidate_id="opaque-first-correction", replaces_candidate_id="opaque-user-memory-001",
                episode_id="opaque-first-correction-episode",
            ), store)
            before_closed = store.stats()
            package = daily_v2_fixture()
            package["MEMORY_CANDIDATES"].append({
                "candidate_id": "opaque-ordinary-after-closed", "candidate_type": "USER_DECISION",
                "statement": "synthetic ordinary must not persist", "supporting_episode_ids": ["opaque-user-episode-002"],
                "valid_from": "2026-08-12T03:00:00+08:00", "valid_to": None,
                "recorded_at": "2026-08-12T03:00:00+08:00", "sensitivity_class": "PRIVATE_OR_SENSITIVE",
                "correction_target": None,
            })
            closed = correction_package(
                candidate_id="opaque-closed-target-correction", replaces_candidate_id="opaque-user-memory-001",
                episode_id="opaque-closed-target-episode",
            )
            package["CONVERSATION_EPISODES"].append(closed["CONVERSATION_EPISODES"][-1])
            package["MEMORY_CANDIDATES"].append(closed["MEMORY_CANDIDATES"][0])
            package["DERIVED_DAILY_PROJECTION"]["supporting_episode_ids"].append("opaque-closed-target-episode")
            package["DERIVED_DAILY_PROJECTION"]["supporting_candidate_ids"].extend([
                "opaque-ordinary-after-closed", "opaque-closed-target-correction",
            ])
            package["VALIDATION"]["candidate_dispositions"].update({
                "opaque-ordinary-after-closed": "ACCEPTED", "opaque-closed-target-correction": "ACCEPTED",
            })
            package["VALIDATION"]["sensitivity_by_candidate"].update({
                "opaque-ordinary-after-closed": "PRIVATE_OR_SENSITIVE", "opaque-closed-target-correction": "PRIVATE_OR_SENSITIVE",
            })
            with self.assertRaisesRegex(ValueError, "target_already_closed"):
                ingest_daily_memory_candidate_v2(package, store)
            self.assertEqual(store.stats(), before_closed)
        finally:
            store.close()

        store = MemoryStore().connect()
        try:
            ingest_daily_memory_candidate_v2(daily_v2_fixture(), store)
            package = correction_package(
                candidate_id="opaque-batch-correction-one", replaces_candidate_id="opaque-user-memory-001",
                episode_id="opaque-batch-correction-episode-one",
            )
            duplicate = correction_package(
                candidate_id="opaque-batch-correction-two", replaces_candidate_id="opaque-user-memory-001",
                episode_id="opaque-batch-correction-episode-two",
            )
            package["CONVERSATION_EPISODES"].append(duplicate["CONVERSATION_EPISODES"][-1])
            package["MEMORY_CANDIDATES"].append(duplicate["MEMORY_CANDIDATES"][0])
            package["DERIVED_DAILY_PROJECTION"]["supporting_episode_ids"].append("opaque-batch-correction-episode-two")
            package["DERIVED_DAILY_PROJECTION"]["supporting_candidate_ids"].append("opaque-batch-correction-two")
            package["VALIDATION"]["candidate_dispositions"]["opaque-batch-correction-two"] = "ACCEPTED"
            package["VALIDATION"]["sensitivity_by_candidate"]["opaque-batch-correction-two"] = "PRIVATE_OR_SENSITIVE"
            before_duplicate = store.stats()
            with self.assertRaisesRegex(ValueError, "target_duplicate_in_batch"):
                ingest_daily_memory_candidate_v2(package, store)
            self.assertEqual(store.stats(), before_duplicate)
        finally:
            store.close()

    def test_external_candidate_aliases_remain_auditable_and_resolve_corrections(self) -> None:
        first_id, alias_id = "opaque-user-memory-001", "opaque-user-memory-alias-002"
        store = MemoryStore().connect()
        try:
            first = ingest_daily_memory_candidate_v2(daily_v2_fixture(), store)
            alias = daily_v2_fixture()
            alias["MEMORY_CANDIDATES"][0]["candidate_id"] = alias_id
            alias["DERIVED_DAILY_PROJECTION"]["supporting_candidate_ids"][0] = alias_id
            alias["VALIDATION"]["candidate_dispositions"] = {alias_id: "ACCEPTED", "opaque-project-state-002": "ACCEPTED"}
            alias["VALIDATION"]["sensitivity_by_candidate"] = {alias_id: "PRIVATE_OR_SENSITIVE", "opaque-project-state-002": "PRIVATE_OR_SENSITIVE"}
            second = ingest_daily_memory_candidate_v2(alias, store)
            atom_id = first.packets[0]["atoms"][0]["id"]
            self.assertEqual(second.packets[0]["atoms"][0]["id"], atom_id)
            aliases = store.get_atom(atom_id)["memory_metadata"]["conversation"]["daily_candidate_id_hashes"]
            self.assertEqual(aliases, sorted([content_hash(first_id), content_hash(alias_id)]))
            self.assertEqual(store.provenance_for_atom(atom_id)[0]["daily_candidate_id_hashes"], aliases)
            correction = ingest_daily_memory_candidate_v2(correction_package(
                candidate_id="opaque-alias-correction", replaces_candidate_id=alias_id,
                episode_id="opaque-alias-correction-episode",
            ), store)
            self.assertEqual(correction.packets[0]["relations"][0]["target_atom_id"], atom_id)
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
