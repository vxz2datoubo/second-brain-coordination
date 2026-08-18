from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from global_signal_plane.fixtures import event, snapshot
from global_signal_plane.ledger import DurableSignalLedger
from global_signal_plane.models import RELATION_TYPES, SignalEvent, SignalLink, SignalPlaneError
from global_signal_plane.reconciliation import build_receipt, verify_receipt
from global_signal_plane.scenario_runner import execute_scenario


ROOT = Path(__file__).resolve().parents[1]


class SignalPlaneContractTest(unittest.TestCase):
    def test_event_contract_is_immutable_and_fail_closed_for_private_material(self) -> None:
        admitted = SignalEvent.from_dict(event("valid"))
        with self.assertRaises(SignalPlaneError) as private:
            SignalEvent.from_dict(event("private", raw_source_body="private"))
        self.assertEqual(private.exception.code, "UNRECOGNIZED_OR_PRIVATE_FIELD")
        with self.assertRaises(SignalPlaneError) as secret:
            SignalEvent.from_dict(event("secret", public_safe_metadata={"token": "ghp_synthetic"}))
        self.assertEqual(secret.exception.code, "PRIVATE_OR_SECRET_VALUE_FORBIDDEN")
        self.assertEqual(admitted.as_dict()["event_id"], "valid")
        with self.assertRaises(TypeError):
            admitted.data["event_id"] = "mutated"  # type: ignore[index]
        with self.assertRaises(SignalPlaneError) as hash_mismatch:
            SignalEvent.from_dict(event("hash", content_hash="not-the-semantic-hash"))
        self.assertEqual(hash_mismatch.exception.code, "SEMANTIC_CONTENT_HASH_MISMATCH")

    def test_all_canonical_relation_types_validate_and_preserve_duplicate_provenance(self) -> None:
        ledger = DurableSignalLedger()
        self.addCleanup(ledger.close)
        ledger.ingest_raw(event("a", signal_id="a")); ledger.ingest_raw(event("b", signal_id="b"))
        for index, relation in enumerate(sorted(RELATION_TYPES)):
            ledger.append_link(SignalLink.from_dict({"link_id": f"link-{index}", "from_signal_ref": "a", "to_signal_ref": "b", "relation_type": relation, "evidence_refs": ["opaque://a", "opaque://b"], "created_at": "2026-08-15T00:00:00+00:00", "created_by": "synthetic"}))
        projection = ledger.rebuild_projection()
        self.assertEqual(len(projection["links"]), len(RELATION_TYPES))
        self.assertEqual(projection["links"][0]["evidence_refs"], ["opaque://a", "opaque://b"])

    def test_idempotency_collision_and_event_identity_collision_are_fail_closed(self) -> None:
        ledger = DurableSignalLedger()
        self.addCleanup(ledger.close)
        self.assertEqual(ledger.ingest_raw(event("first", idempotency_key="same"))["status"], "ADMITTED")
        self.assertEqual(ledger.ingest_raw(event("first", idempotency_key="same"))["status"], "IDEMPOTENT_DUPLICATE")
        with self.assertRaises(SignalPlaneError) as collision:
            ledger.ingest(SignalEvent.from_dict(event("second", idempotency_key="same")))
        self.assertEqual(collision.exception.code, "IDEMPOTENCY_KEY_COLLISION")
        with self.assertRaises(SignalPlaneError) as identity:
            ledger.ingest(SignalEvent.from_dict(event("first", summary_ref="summary://changed", idempotency_key="changed")))
        self.assertEqual(identity.exception.code, "EVENT_ID_COLLISION")

    def test_sqlite_restart_recovery_rebuild_and_checksum_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "signals.sqlite"
            ledger = DurableSignalLedger(db_path)
            ledger.ingest_raw(event("one"), update_projection=False)
            self.assertIsNone(ledger.current_projection())
            ledger.close()
            recovered = DurableSignalLedger(db_path)
            first = recovered.rebuild_projection()
            recovered.discard_projection_for_recovery_test()
            second = recovered.rebuild_projection()
            self.assertEqual(first["checksum"], second["checksum"])
            self.assertEqual(recovered.ingest_raw(event("one"))["status"], "IDEMPOTENT_DUPLICATE")
            recovered.close()

    def test_stale_projection_writer_and_clock_only_regression_are_rejected(self) -> None:
        ledger = DurableSignalLedger()
        self.addCleanup(ledger.close)
        ledger.ingest_raw(event("done", signal_id="s", source_sequence=2, execution_state="DONE"))
        current = ledger.current_projection_version()
        with self.assertRaises(SignalPlaneError) as stale:
            ledger.rebuild_projection(expected_version=current - 1)
        self.assertEqual(stale.exception.code, "STALE_PROJECTION_VERSION")
        ledger.ingest_raw(event("old", signal_id="s", source_sequence=1, occurred_at="2027-01-01T00:00:00+00:00", execution_state="EXECUTING"))
        self.assertEqual(ledger.rebuild_projection()["signals"][0]["execution_state"], "DONE")

    def test_projection_cas_is_atomic_across_two_independent_connections(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "signals.sqlite"
            writer_a, writer_b = DurableSignalLedger(db_path), DurableSignalLedger(db_path)
            try:
                writer_a.ingest_raw(event("seed"))
                expected = writer_a.current_projection_version()
                winner = writer_a.rebuild_projection(expected_version=expected)
                with self.assertRaises(SignalPlaneError) as stale:
                    writer_b.rebuild_projection(expected_version=expected)
                self.assertEqual(stale.exception.code, "STALE_PROJECTION_VERSION")
                self.assertEqual(writer_b.current_projection_version(), winner["projection_version"])
            finally:
                writer_a.close(); writer_b.close()

    def test_link_revision_advances_and_pre_link_projection_writer_is_rejected(self) -> None:
        ledger = DurableSignalLedger()
        self.addCleanup(ledger.close)
        ledger.ingest_raw(event("a", signal_id="a")); ledger.ingest_raw(event("b", signal_id="b"))
        pre_link_version, pre_link_revision = ledger.current_projection_version(), ledger.input_revision()
        receipt = ledger.append_link(SignalLink.from_dict({"link_id": "revision-link", "from_signal_ref": "a", "to_signal_ref": "b", "relation_type": "DUPLICATE", "evidence_refs": ["opaque://a"], "created_at": "2026-08-15T00:00:00+00:00", "created_by": "synthetic"}))
        self.assertGreater(receipt["input_revision"], pre_link_revision)
        with self.assertRaises(SignalPlaneError) as stale:
            ledger.rebuild_projection(expected_version=pre_link_version)
        self.assertEqual(stale.exception.code, "STALE_PROJECTION_VERSION")

    def test_durable_idempotency_key_is_unique_across_reopened_connections(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "signals.sqlite"
            first, retry = DurableSignalLedger(db_path), DurableSignalLedger(db_path)
            try:
                self.assertEqual(first.ingest_raw(event("same-delivery"), update_projection=False)["status"], "ADMITTED")
                self.assertEqual(retry.ingest_raw(event("same-delivery"), update_projection=False)["status"], "IDEMPOTENT_DUPLICATE")
                self.assertEqual(len(retry.history()), 1)
                with self.assertRaises(SignalPlaneError) as collision:
                    retry.ingest_raw(event("other", idempotency_key="idem-same-delivery"), update_projection=False)
                self.assertEqual(collision.exception.code, "IDEMPOTENCY_KEY_COLLISION")
            finally:
                first.close(); retry.close()

    def test_bounded_backpressure_defers_low_materiality_and_preserves_priority(self) -> None:
        ledger = DurableSignalLedger()
        self.addCleanup(ledger.close)
        receipts = [ledger.ingest_raw(event(f"burst-{index}"), capacity_limit=2) for index in range(3)]
        priority = ledger.ingest_raw(event("priority", signal_kind="RISK"), capacity_limit=2)
        state = ledger.backpressure_state(2)
        self.assertEqual([item["status"] for item in receipts], ["ADMITTED", "ADMITTED", "DEFERRED_BACKPRESSURE"])
        self.assertEqual(priority["status"], "ADMITTED")
        self.assertEqual(state, {"capacity_limit": 2, "admitted": 3, "deferred": 1, "pressure_active": True})

    def test_semantic_signal_kind_is_projected_for_non_requirement_origins(self) -> None:
        ledger = DurableSignalLedger()
        self.addCleanup(ledger.close)
        for index, kind in enumerate(("RISK", "FINDING", "OPPORTUNITY", "CORRECTION"), start=1):
            ledger.ingest_raw(event(f"kind-{index}", signal_id=f"semantic-{index}", source_sequence=1, signal_kind=kind))
        projection = ledger.current_projection()
        self.assertIsNotNone(projection)
        self.assertEqual(projection["reducer_version"], "S0C-3")
        actual = {item["signal_id"]: item["signal_kind"] for item in projection["signals"]}
        self.assertEqual(actual, {"semantic-1": "RISK", "semantic-2": "FINDING", "semantic-3": "OPPORTUNITY", "semantic-4": "CORRECTION"})

    def test_lifecycle_status_and_revocation_do_not_overwrite_logical_kind(self) -> None:
        ledger = DurableSignalLedger()
        self.addCleanup(ledger.close)
        ledger.ingest_raw(event("risk-origin", signal_id="risk", source_sequence=1, signal_kind="RISK"))
        ledger.ingest_raw(event("risk-status", signal_id="risk", source_sequence=2, signal_kind="STATUS", event_type="SIGNAL_CLOSURE_ASSESSMENT", planning_state="CLOSED_NO_ACTION", execution_state="DONE"))
        closed = next(item for item in ledger.current_projection()["signals"] if item["signal_id"] == "risk")
        self.assertEqual((closed["signal_kind"], closed["planning_state"], closed["execution_state"]), ("RISK", "CLOSED_NO_ACTION", "DONE"))
        ledger.ingest_raw(event("risk-revoke", signal_id="risk", source_sequence=3, signal_kind="REVOCATION", event_type="EXPLICIT_SIGNAL_REVOKE", planning_state="SUPERSEDED", execution_state="CANCELLED", revokes_refs=["risk"]))
        revoked = next(item for item in ledger.current_projection()["signals"] if item["signal_id"] == "risk")
        self.assertEqual((revoked["signal_kind"], revoked["planning_state"], revoked["execution_state"]), ("RISK", "SUPERSEDED", "CANCELLED"))

    def test_out_of_order_lifecycle_event_cannot_replace_semantic_kind(self) -> None:
        ledger = DurableSignalLedger()
        self.addCleanup(ledger.close)
        ledger.ingest_raw(event("risk-origin-late-sequence", signal_id="risk-ooo", source_sequence=2, signal_kind="RISK"))
        ledger.ingest_raw(event("old-status-arrives-late", signal_id="risk-ooo", source_sequence=1, signal_kind="STATUS", event_type="SIGNAL_CLOSURE_ASSESSMENT", planning_state="CLOSED_NO_ACTION", execution_state="DONE"))
        projected = next(item for item in ledger.current_projection()["signals"] if item["signal_id"] == "risk-ooo")
        self.assertEqual(projected["signal_kind"], "RISK")

    def test_conflicting_semantic_origins_fail_closed_to_revalidation(self) -> None:
        ledger = DurableSignalLedger()
        self.addCleanup(ledger.close)
        ledger.ingest_raw(event("risk-origin-conflict", signal_id="semantic-conflict", source_sequence=1, signal_kind="RISK"))
        ledger.ingest_raw(event("finding-origin-conflict", signal_id="semantic-conflict", source_sequence=2, signal_kind="FINDING"))
        projected = next(item for item in ledger.current_projection()["signals"] if item["signal_id"] == "semantic-conflict")
        self.assertEqual(projected["signal_kind"], "RISK")
        self.assertEqual(projected["planning_state"], "CONFLICTED")
        self.assertEqual(projected["epistemic_state"], "NEEDS_REVALIDATION")
        self.assertIn("semantic-conflict", ledger.current_projection()["views"]["NEEDS_REVALIDATION"])

    def test_semantic_kind_restart_replay_and_checksum_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "semantic.sqlite"
            first = DurableSignalLedger(db_path)
            first.ingest_raw(event("risk-replay", signal_id="risk-replay", source_sequence=1, signal_kind="RISK"))
            before = first.current_projection()
            first.close()
            recovered = DurableSignalLedger(db_path)
            after = recovered.current_projection()
            self.assertEqual(before["reducer_version"], "S0C-3")
            self.assertEqual(after["reducer_version"], "S0C-3")
            self.assertEqual(before["checksum"], after["checksum"])
            self.assertEqual(after["signals"][0]["signal_kind"], "RISK")
            self.assertTrue(recovered.observe_replay())
            self.assertEqual(recovered.current_projection()["signals"][0]["signal_kind"], "RISK")
            recovered.close()

    def test_legacy_reducer_projection_is_rebuilt_into_new_checksum_domain(self) -> None:
        ledger = DurableSignalLedger()
        self.addCleanup(ledger.close)
        ledger.ingest_raw(event("legacy-risk", signal_id="legacy-risk", signal_kind="RISK"), update_projection=False)
        legacy = {"reducer_version": "S0C-2", "ledger_watermark": 1, "input_revision": ledger.input_revision(), "signals": [{"signal_id": "legacy-risk", "planning_state": "CAPTURED", "execution_state": "NOT_STARTED", "epistemic_state": "CONFIRMED_FACT", "source_order": 1, "provenance_event_refs": ["legacy-risk"]}], "links": [], "clusters": [], "views": {"OPEN": ["legacy-risk"], "BLOCKED": [], "SUPERSEDED": [], "CLOSED_NO_ACTION": [], "NEEDS_REVALIDATION": []}, "projection_version": 9, "generated_at": "legacy", "checksum": "legacy-checksum"}
        with ledger.connection:
            ledger.connection.execute("INSERT INTO projection_meta(singleton,projection_version,input_revision,checksum,projection_json) VALUES(1,?,?,?,?,?)".replace("?,?,?,?,?", "?,?,?,?"), (9, ledger.input_revision(), "legacy-checksum", json.dumps(legacy, sort_keys=True)))
        rebuilt = ledger.current_projection()
        self.assertEqual(rebuilt["reducer_version"], "S0C-3")
        self.assertEqual(rebuilt["signals"][0]["signal_kind"], "RISK")
        self.assertNotEqual(rebuilt["checksum"], "legacy-checksum")
        self.assertEqual(rebuilt["projection_version"], 10)

    def test_reconciliation_receipt_invalidates_material_change_and_never_authorizes(self) -> None:
        receipt = build_receipt(snapshot())
        self.assertFalse(receipt["execution_authorized"])
        self.assertEqual(verify_receipt(receipt, snapshot())["result"], "PASS")
        self.assertIn("STALE_REVIEW_HEAD", verify_receipt(receipt, snapshot(pr_head="new"))["codes"])
        self.assertIn("STALE_PR_STATE", verify_receipt(receipt, snapshot(pr_state="MERGED"))["codes"])
        self.assertIn("USER_REVOKE_INVALIDATES_PASS", verify_receipt(receipt, snapshot(user_approval_state="REVOKE"))["codes"])

    def test_gst_r001_to_r024_are_executable_table_driven_public_safe_fixtures(self) -> None:
        fixtures = json.loads((ROOT / "fixtures" / "gst_scenarios.json").read_text(encoding="utf-8"))
        self.assertTrue(fixtures["public_safe"])
        self.assertEqual(len(fixtures["scenarios"]), 24)
        r133 = next(spec for spec in fixtures["scenarios"] if spec["id"] == "GST-R001-CROSS-WINDOW-STATE-DRIFT-R133")
        self.assertEqual(r133["canonical_evidence_ref"], "coordination/CONTROL-TOWER/R133-CLOSURE-RECONCILIATION.yaml")
        ids = set()
        for spec in fixtures["scenarios"]:
            self.assertTrue({"setup", "input_events", "expected_signal_state", "expected_projection", "expected_reconciliation_result", "expected_error_or_alert_codes", "authority_assertions", "replay_assertion"}.issubset(spec))
            report = execute_scenario(spec)
            ids.add(report["id"])
            self.assertEqual(report["result"], spec["expected_reconciliation_result"], report)
            self.assertFalse(report["authority_assertions"]["execution_authorized"])
            self.assertFalse(report["authority_assertions"]["w3_mutated"])
            self.assertFalse(report["authority_assertions"]["domain_written"])
            if spec["replay_assertion"]:
                self.assertTrue(report["replay_observed"], report)
            else:
                self.assertIsNone(report["replay_observed"], report)
            for code in spec["expected_error_or_alert_codes"]:
                self.assertIn(code, report["codes"], report)
        self.assertEqual(r133["r133_public_binding"]["sha256"], "49A63DBB3598AC4E415380CB6A02F41A0501A49948744A0731B92EE81B93DF18")
        r133_report = execute_scenario(r133)
        self.assertEqual(r133_report["evidence_binding"]["sha256"], r133["r133_public_binding"]["sha256"])
        self.assertEqual(r133_report["evidence_binding"]["required_fragment_count"], len(r133["r133_public_binding"]["required_utf8_fragments"]))
        self.assertEqual(len(ids), 24)

    def test_repeated_run_is_deterministic(self) -> None:
        def result() -> tuple[str, str]:
            ledger = DurableSignalLedger()
            try:
                ledger.ingest_raw(event("a")); ledger.ingest_raw(event("b", source_sequence=2)); projection = ledger.rebuild_projection(); return projection["checksum"], json.dumps(projection["signals"], sort_keys=True)
            finally:
                ledger.close()
        self.assertEqual(result(), result())


if __name__ == "__main__":
    unittest.main()
