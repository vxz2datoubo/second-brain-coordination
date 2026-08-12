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
    DAILY_MEMORY_CANDIDATE_V2,
    PRIVATE_SOURCE_BINDING_CONFIGURED,
    PRIVATE_SOURCE_BINDING_REJECTED,
    PRIVATE_SOURCE_BINDING_WAITING,
    W3_PRIVATE_CANDIDATE_ENVELOPE_V1,
    build_private_w3_candidate_envelope,
    daily_v2_package_to_w3_private_envelopes,
    ingest_daily_memory_candidate_v2,
    private_source_binding_status,
    validate_private_data_paths,
)


def daily_v2_fixture() -> dict:
    """Representative synthetic package; it contains no real private values."""

    episodes = [
        {
            "episode_id": "opaque-episode-user-001",
            "source_pointer": "local-private://opaque-fixture/user-001",
            "source_hash": "1" * 64,
            "actor_type": "USER",
            "recorded_at": "2026-08-12T00:01:00+08:00",
        },
        {
            "episode_id": "opaque-episode-assistant-002",
            "source_pointer": "local-private://opaque-fixture/assistant-002",
            "source_hash": "2" * 64,
            "actor_type": "ASSISTANT",
            "recorded_at": "2026-08-12T00:02:00+08:00",
        },
        {
            "episode_id": "opaque-episode-user-003",
            "source_pointer": "local-private://opaque-fixture/user-003",
            "source_hash": "3" * 64,
            "actor_type": "USER",
            "recorded_at": "2026-08-12T00:03:00+08:00",
        },
    ]
    candidates = [
        {
            "candidate_id": "opaque-user-memory-001",
            "candidate_type": "USER_PREFERENCE",
            "statement": "synthetic local preference marker",
            "source_episode_ids": ["opaque-episode-user-001", "opaque-episode-user-003"],
            "valid_from": "2026-08-12T00:00:00+08:00",
            "valid_to": None,
            "recorded_at": "2026-08-12T00:03:00+08:00",
            "sensitivity_class": "PRIVATE_OR_SENSITIVE",
        },
        {
            "candidate_id": "opaque-assistant-analysis-002",
            "candidate_type": "ASSISTANT_ANALYSIS",
            "statement": "synthetic assistant-only marker",
            "source_episode_ids": ["opaque-episode-assistant-002"],
            "valid_from": "2026-08-12T00:00:00+08:00",
            "valid_to": None,
            "recorded_at": "2026-08-12T00:03:00+08:00",
            "sensitivity_class": "PRIVATE_OR_SENSITIVE",
        },
    ]
    return {
        "schema_version": DAILY_MEMORY_CANDIDATE_V2,
        "COVERAGE": {
            "coverage_id": "opaque-coverage-001",
            "user_scope": "opaque-user-a",
            "project_scope": "opaque-project-a",
            "covered_episode_ids": [item["episode_id"] for item in episodes],
        },
        "CONVERSATION_EPISODES": episodes,
        "MEMORY_CANDIDATES": candidates,
        "DERIVED_DAILY_PROJECTION": {
            "projection_id": "opaque-projection-001",
            "candidate_ids": [item["candidate_id"] for item in candidates],
        },
        "VALIDATION": {
            "status": "VALIDATED",
            "accepted_candidate_ids": ["opaque-user-memory-001"],
            "rejected_candidates": [{
                "candidate_id": "opaque-assistant-analysis-002",
                "reason": "non_user_candidate_type",
            }],
            "sensitivity_by_candidate": {
                "opaque-user-memory-001": "PRIVATE_OR_SENSITIVE",
                "opaque-assistant-analysis-002": "PRIVATE_OR_SENSITIVE",
            },
        },
    }


class PrivateCandidateIngestionTestCase(unittest.TestCase):
    def test_daily_v2_layered_package_maps_only_validated_user_candidate(self) -> None:
        package = daily_v2_fixture()
        envelopes = daily_v2_package_to_w3_private_envelopes(package)
        self.assertEqual(len(envelopes), 1)
        envelope = envelopes[0]
        self.assertEqual(envelope["schema_version"], W3_PRIVATE_CANDIDATE_ENVELOPE_V1)
        self.assertEqual(envelope["candidate_id"], "opaque-user-memory-001")
        self.assertEqual(envelope["claim_role"], "USER_PREFERENCE")
        self.assertEqual(envelope["source_episodes"][0]["episode_id"], "opaque-episode-user-001")
        self.assertEqual(envelope["source_episodes"][1]["episode_id"], "opaque-episode-user-003")
        packet = build_private_w3_candidate_envelope(envelope)
        self.assertFalse(packet["authority_write"])
        self.assertEqual(
            packet["atoms"][0]["memory_metadata"]["conversation"]["source_episode_manifest_ids"],
            packet["source_manifest_ids"],
        )
        self.assertEqual(len(packet["evidence_refs"]), 2)

    def test_daily_v2_rejects_unvalidated_non_user_or_invalid_provenance(self) -> None:
        unvalidated = daily_v2_fixture()
        unvalidated["VALIDATION"]["status"] = "PENDING"
        with self.assertRaisesRegex(ValueError, "validation_required"):
            daily_v2_package_to_w3_private_envelopes(unvalidated)
        non_user = daily_v2_fixture()
        non_user["VALIDATION"]["accepted_candidate_ids"] = ["opaque-assistant-analysis-002"]
        non_user["VALIDATION"]["rejected_candidates"] = [{
            "candidate_id": "opaque-user-memory-001", "reason": "fixture",
        }]
        with self.assertRaisesRegex(ValueError, "non_user_candidate_denied"):
            daily_v2_package_to_w3_private_envelopes(non_user)
        missing_episode = daily_v2_fixture()
        missing_episode["MEMORY_CANDIDATES"][0]["source_episode_ids"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "candidate_episode_missing"):
            daily_v2_package_to_w3_private_envelopes(missing_episode)
        assistant_source = daily_v2_fixture()
        assistant_source["MEMORY_CANDIDATES"][0]["source_episode_ids"] = ["opaque-episode-assistant-002"]
        with self.assertRaisesRegex(ValueError, "candidate_actor_denied"):
            daily_v2_package_to_w3_private_envelopes(assistant_source)

    def test_sensitivity_and_validation_gate_reject_plain_credential_classes(self) -> None:
        for sensitivity in (
            "PASSWORD", "API_KEY", "TOKEN", "COOKIE", "SESSION_CREDENTIAL",
            "MFA_OTP", "RECOVERY_CODE", "PAYMENT_CREDENTIAL", "BANK_CREDENTIAL",
            "BROKER_CREDENTIAL", "SECRET_CREDENTIAL",
        ):
            package = daily_v2_fixture()
            package["MEMORY_CANDIDATES"][0]["sensitivity_class"] = sensitivity
            package["VALIDATION"]["sensitivity_by_candidate"]["opaque-user-memory-001"] = sensitivity
            with self.assertRaisesRegex(ValueError, "secret_or_sensitive_candidate_denied"):
                daily_v2_package_to_w3_private_envelopes(package)
        rejected_sensitive = daily_v2_fixture()
        rejected_sensitive["MEMORY_CANDIDATES"][1]["sensitivity_class"] = "PASSWORD"
        rejected_sensitive["VALIDATION"]["sensitivity_by_candidate"]["opaque-assistant-analysis-002"] = "PASSWORD"
        self.assertEqual(len(daily_v2_package_to_w3_private_envelopes(rejected_sensitive)), 1)
        mismatch = daily_v2_fixture()
        mismatch["VALIDATION"]["sensitivity_by_candidate"]["opaque-user-memory-001"] = "PRIVATE_LOCAL_CANDIDATE"
        with self.assertRaisesRegex(ValueError, "sensitivity_mismatch"):
            daily_v2_package_to_w3_private_envelopes(mismatch)

    def test_import_requires_exact_imported_atom_recall_even_with_decoy(self) -> None:
        store = MemoryStore().connect()
        try:
            result = ingest_daily_memory_candidate_v2(daily_v2_fixture(), store)
            self.assertTrue(result.exact_imported_atom_recalled)
            self.assertIn(
                result.packets[0]["atoms"][0]["id"],
                result.recalled_atom_ids,
            )
            receipt = result.public_receipt()
            self.assertTrue(receipt["exact_imported_atom_recalled"])
            self.assertNotIn("statement", receipt)

            decoy_only = Mock()
            decoy_only.assemble.return_value = type(
                "Bundle", (), {"atoms": ({"id": "preexisting-decoy"},)}
            )()
            with self.assertRaisesRegex(ValueError, "exact_recall_not_proven"):
                ingest_daily_memory_candidate_v2(daily_v2_fixture(), store, context_assembler=decoy_only)
        finally:
            store.close()

    def test_private_data_root_policy_and_cli_fail_closed_without_path_echo(self) -> None:
        public_input = PHASE_ROOT / "public-fixture.json"
        public_store = PHASE_ROOT / "public-fixture.db"
        with tempfile.TemporaryDirectory() as temporary:
            private_root = Path(temporary)
            private_input = private_root / "candidate.json"
            private_store = private_root / "candidate.db"
            self.assertEqual(
                validate_private_data_paths(private_input, private_store, private_root)[:2],
                (private_input.resolve(), private_store.resolve()),
            )
            with self.assertRaisesRegex(ValueError, "path_policy_denied"):
                validate_private_data_paths(public_input, private_store, private_root)
            with self.assertRaisesRegex(ValueError, "path_policy_denied"):
                validate_private_data_paths(private_input, public_store, private_root)
            private_input.write_text(json.dumps(daily_v2_fixture()), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main([
                    "private-ingest", "--input", str(private_input), "--store", str(private_store),
                    "--private-root", str(private_root),
                ])
            self.assertEqual(exit_code, 0)
            receipt = json.loads(output.getvalue())
            self.assertNotIn(str(private_root), json.dumps(receipt))
            self.assertTrue(receipt["exact_imported_atom_recalled"])

    def test_source_binding_state_machine_never_echoes_configured_path(self) -> None:
        self.assertEqual(private_source_binding_status({})["status"], PRIVATE_SOURCE_BINDING_WAITING)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing = root / "missing.json"
            absent = private_source_binding_status({
                "CLTM_PRIVATE_DATA_ROOT": str(root),
                "CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH": str(missing),
            })
            self.assertEqual(absent["status"], PRIVATE_SOURCE_BINDING_WAITING)
            self.assertNotIn(str(missing), json.dumps(absent))

            inaccessible = root / "inaccessible.json"
            inaccessible.write_text(json.dumps(daily_v2_fixture()), encoding="utf-8")
            original_read = Path.read_text
            def denied_read(path: Path, *args, **kwargs):
                if path == inaccessible:
                    raise OSError("synthetic inaccessible source")
                return original_read(path, *args, **kwargs)
            with patch.object(Path, "read_text", denied_read):
                waiting = private_source_binding_status({
                    "CLTM_PRIVATE_DATA_ROOT": str(root),
                    "CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH": str(inaccessible),
                })
                self.assertEqual(waiting["status"], PRIVATE_SOURCE_BINDING_WAITING)
                self.assertNotIn(str(inaccessible), json.dumps(waiting))

            invalid = root / "invalid.json"
            invalid.write_text("{not-json", encoding="utf-8")
            rejected = private_source_binding_status({
                "CLTM_PRIVATE_DATA_ROOT": str(root),
                "CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH": str(invalid),
            })
            self.assertEqual(rejected["status"], PRIVATE_SOURCE_BINDING_REJECTED)
            self.assertNotIn(str(invalid), json.dumps(rejected))

            valid = root / "valid.json"
            valid.write_text(json.dumps(daily_v2_fixture()), encoding="utf-8")
            configured = private_source_binding_status({
                "CLTM_PRIVATE_DATA_ROOT": str(root),
                "CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH": str(valid),
            })
            self.assertEqual(configured["status"], PRIVATE_SOURCE_BINDING_CONFIGURED)
            self.assertNotIn(str(valid), json.dumps(configured))


if __name__ == "__main__":
    unittest.main()
