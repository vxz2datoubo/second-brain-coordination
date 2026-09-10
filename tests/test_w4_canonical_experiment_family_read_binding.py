from __future__ import annotations

import copy
import inspect
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE_ROOT = (Path(__file__).parents[1] / "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
                "W4-STRATEGY-EXPERIMENT-FAMILY-P0/src")
sys.path.insert(0, str(PACKAGE_ROOT))

from w4_experiment_family.registry import _validate_schema, digest
from w4_experiment_family import read_binding
from w4_experiment_family.read_binding import (GOVERNED_AUTH_WITNESS_REF, GOVERNED_TASK_ID,
    GOVERNED_WORK_CLAIM_REF, GOVERNED_ROUTE_EPOCH, GOVERNED_EXECUTOR_ROLE, ReadAuthorization,
    ReadError, read_canonical_family, resolve_canonical_w4_store_v1,
    verify_canonical_family_receipt)


class CanonicalReadBindingTests(unittest.TestCase):
    @staticmethod
    def authorization() -> ReadAuthorization:
        return ReadAuthorization(GOVERNED_TASK_ID, GOVERNED_ROUTE_EPOCH, GOVERNED_EXECUTOR_ROLE,
                                 GOVERNED_WORK_CLAIM_REF, GOVERNED_AUTH_WITNESS_REF)

    def read(self):
        return read_canonical_family("W4-CANONICAL-GOLDEN-001", "rev-1",
                                     authorization=self.authorization(),
                                     observed_at="2026-09-10T00:00:00Z")

    @staticmethod
    def resign(receipt):
        receipt["receipt_digest"] = digest({key: value for key, value in receipt.items()
                                             if key != "receipt_digest"})
        return receipt

    def test_positive_schema_and_fixed_observation_digest(self):
        snapshot, receipt = self.read()
        schema_path = PACKAGE_ROOT.parents[0] / "CANONICAL-EXPERIMENT-FAMILY-READ-RECEIPT.schema.json"
        _validate_schema(receipt, json.loads(schema_path.read_text(encoding="utf-8")))
        self.assertEqual("COMPLETE", snapshot["completeness_state"])
        self.assertEqual("CANONICAL_W4_READ_VERIFIED",
                         verify_canonical_family_receipt(receipt, snapshot=snapshot)["primary"])
        self.assertEqual(receipt["receipt_digest"], self.read()[1]["receipt_digest"])

    def test_caller_minted_digest_and_invented_sha_are_rejected(self):
        _, receipt = self.read()
        forged = copy.deepcopy(receipt)
        forged["family_content_digest"] = "0" * 64
        self.resign(forged)
        self.assertNotEqual("CANONICAL_W4_READ_VERIFIED",
                            verify_canonical_family_receipt(forged)["primary"])
        forged = copy.deepcopy(receipt)
        forged["canonical_main_sha"] = "a" * 40
        self.resign(forged)
        self.assertEqual("W4_STORE_IDENTITY_MISMATCH",
                         verify_canonical_family_receipt(forged)["primary"])

    def test_foreign_claim_and_noncanonical_arguments_fail_closed(self):
        foreign = ReadAuthorization(GOVERNED_TASK_ID, GOVERNED_ROUTE_EPOCH, GOVERNED_EXECUTOR_ROLE,
                                    "coordination/foreign/WORK-CLAIM.yaml", GOVERNED_AUTH_WITNESS_REF)
        with self.assertRaisesRegex(ReadError, "W4_READ_AUTHORIZATION_INVALID"):
            read_canonical_family("W4-CANONICAL-GOLDEN-001", "rev-1", authorization=foreign)
        with self.assertRaisesRegex(ReadError, "W4_NONCANONICAL_SOURCE"):
            read_canonical_family("caller-family", "rev-1", authorization=self.authorization())
        _, receipt = self.read()
        receipt["canonical_ref"] = "refs/heads/not-main"
        self.resign(receipt)
        self.assertEqual("W4_NONCANONICAL_SOURCE", verify_canonical_family_receipt(receipt)["primary"])

    def test_no_caller_store_and_self_consistent_foreign_descriptor_do_not_authorize(self):
        self.assertEqual([], list(inspect.signature(resolve_canonical_w4_store_v1).parameters))
        with tempfile.TemporaryDirectory() as directory:
            foreign = Path(directory) / "self-consistent.yaml"
            foreign.write_text('{"schema":"CanonicalW4StoreDescriptor/v1","events":[]}', encoding="utf-8")
            self.assertTrue(foreign.exists())
            with self.assertRaisesRegex(ReadError, "W4_NONCANONICAL_SOURCE"):
                read_canonical_family("foreign", "rev-9", authorization=self.authorization())

    def test_cross_revision_manifest_and_receipt_reuse_are_rejected(self):
        _, receipt = self.read()
        forged = copy.deepcopy(receipt)
        forged["expected_trial_manifest_digest"] = "b" * 64
        self.resign(forged)
        self.assertEqual("W4_TRIAL_MANIFEST_DIGEST_MISMATCH",
                         verify_canonical_family_receipt(forged)["primary"])
        reused = copy.deepcopy(receipt)
        reused["family_revision_id"] = "rev-2"
        reused["experiment_family_ref"] = "W4-CANONICAL-GOLDEN-001@rev-2"
        self.resign(reused)
        self.assertEqual("W4_STORE_IDENTITY_MISMATCH",
                         verify_canonical_family_receipt(reused)["primary"])

    def test_descriptor_drift_is_source_content_mismatch(self):
        _, receipt = self.read()
        root = Path(__file__).parents[1]
        descriptor = root / read_binding.GOVERNED_DESCRIPTOR_REF
        original = descriptor.read_bytes()
        try:
            descriptor.write_bytes(original + b"\n")
            result = verify_canonical_family_receipt(receipt)
        finally:
            descriptor.write_bytes(original)
        self.assertEqual("W4_SOURCE_CONTENT_MISMATCH", result["primary"])

    def test_read_binding_has_no_write_adapter_and_store_is_read_only(self):
        exported = {name.lower() for name in vars(read_binding)}
        self.assertFalse({"append", "update", "delete"} & exported)
        handle = resolve_canonical_w4_store_v1()
        before = Path(handle.db_path).read_bytes()
        connection = sqlite3.connect(Path(handle.db_path).as_uri() + "?mode=ro", uri=True)
        try:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("DELETE FROM experiment_events")
        finally:
            connection.close()
        self.read()
        self.assertEqual(before, Path(handle.db_path).read_bytes())

    def test_snapshot_alias_is_schema_covered(self):
        handle = resolve_canonical_w4_store_v1()
        from w4_experiment_family.registry import Registry
        reg = Registry(sqlite3.connect(handle.db_path))
        try:
            snapshot = reg.read_experiment_family(f"{handle.family_id}@{handle.family_revision_id}")
        finally:
            reg.db.close()
        self.assertIn("family_snapshot_digest", snapshot)
        self.assertEqual(snapshot["family_snapshot_digest"], snapshot["snapshot_digest"])
        schema = json.loads((PACKAGE_ROOT.parents[0] / "EXPERIMENT-FAMILY-SNAPSHOT.schema.json").read_text(encoding="utf-8"))
        _validate_schema(snapshot, schema)

    def test_read_experiment_family_call_contract_is_pinned(self):
        from w4_experiment_family.registry import Registry, RegistryError
        signature = inspect.signature(Registry.read_experiment_family)
        self.assertEqual(["self", "exact_family_revision"], list(signature.parameters))
        handle = resolve_canonical_w4_store_v1()
        reg = Registry(sqlite3.connect(handle.db_path))
        try:
            core = reg.read_experiment_family(f"{handle.family_id}@{handle.family_revision_id}")
            self.assertEqual("ExperimentFamilySnapshot/v1", core["schema"])
            with self.assertRaisesRegex(RegistryError, "INVALID_EXACT_FAMILY_REVISION"):
                reg.read_experiment_family("no-separator")
        finally:
            reg.db.close()
        _, receipt = self.read()
        self.assertEqual(receipt["family_content_digest"], core["snapshot_digest"])

    def test_authority_flags_cannot_be_forged(self):
        _, receipt = self.read()
        scheme = json.loads((PACKAGE_ROOT.parents[0] / "CANONICAL-EXPERIMENT-FAMILY-READ-RECEIPT.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["authority"]["trade_authority"], False)
        self.assertEqual(receipt["authority"]["read_evidence_authority"], True)
        forged = copy.deepcopy(receipt)
        forged["authority"]["trade_authority"] = True
        self.resign(forged)
        with self.assertRaises(Exception):
            _validate_schema(forged, scheme)

    def test_canonical_state_unavailable_fails_closed(self):
        _, receipt = self.read()
        root = Path(__file__).parents[1]
        descriptor = root / read_binding.GOVERNED_DESCRIPTOR_REF
        original = descriptor.read_bytes()
        try:
            descriptor.write_bytes(b"{}")
            result = verify_canonical_family_receipt(receipt)
        finally:
            descriptor.write_bytes(original)
        self.assertNotEqual("CANONICAL_W4_READ_VERIFIED", result["primary"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main(verbosity=2)
