from __future__ import annotations

import copy
from hashlib import sha256
from pathlib import Path
import sys
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

import e57_authority.core as core
from e57_authority.core import AuthoritySession, RecordKind, SourceRecord, stable_digest


def clone_record(record: SourceRecord, **changes: object) -> SourceRecord:
    clone = object.__new__(type(record))
    for field in ("kind", "record_id", "issuer_id", "payload_json", "attestation"):
        object.__setattr__(clone, field, changes.get(field, getattr(record, field)))
    return clone


class IssuerAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = AuthoritySession()
        self.source = self.session.issue_source(
            source_id="fixture/source.json",
            source_sha256=sha256(b'{"ok":true}').hexdigest(),
            format_name="json",
            byte_length=11,
        )

    def tearDown(self) -> None:
        self.session.close()

    def test_issued_source_verifies(self) -> None:
        self.assertTrue(self.session.verify(self.source))

    def test_direct_source_constructor_is_not_issued(self) -> None:
        forged = SourceRecord(**dict(self.source.wire()))
        self.assertFalse(self.session.verify(forged))

    def test_object_new_same_wire_is_not_an_issued_presentation(self) -> None:
        self.assertFalse(self.session.verify(clone_record(self.source)))

    def test_copy_is_not_an_issued_presentation(self) -> None:
        self.assertFalse(self.session.verify(copy.copy(self.source)))

    def test_same_id_payload_substitution_is_rejected(self) -> None:
        forged = clone_record(self.source, payload_json='{"byte_length":0}')
        self.assertFalse(self.session.verify(forged))

    def test_local_presentation_permit_tampering_does_not_bypass_remote_ledger(self) -> None:
        forged = clone_record(self.source, payload_json='{"byte_length":0}')
        self.session._permits[id(forged)] = stable_digest(forged.wire())
        self.assertFalse(self.session.verify(forged))

    def test_foreign_issuer_record_is_rejected(self) -> None:
        with AuthoritySession(issuer_id="e57.foreign") as foreign:
            foreign_record = foreign.issue_source(
                source_id="fixture/source.json",
                source_sha256=sha256(b'{"ok":true}').hexdigest(),
                format_name="json",
                byte_length=11,
            )
            self.assertFalse(self.session.verify(foreign_record))

    def test_module_global_enumeration_exposes_no_mutable_issued_registry(self) -> None:
        dangerous = {
            name: value
            for name, value in vars(core).items()
            if any(word in name.lower() for word in ("issued", "registry", "admission_state", "signing_key"))
        }
        self.assertEqual(dangerous, {})

    def test_replacing_non_authoritative_type_map_does_not_admit_forgery(self) -> None:
        original = core._RECORD_CLASSES
        try:
            core._RECORD_CLASSES = {}
            self.assertTrue(self.session.verify(self.source))
            self.assertFalse(self.session.verify(clone_record(self.source)))
        finally:
            core._RECORD_CLASSES = original

    def test_verifier_channel_refuses_issue_command(self) -> None:
        self.session._verifier_connection.send({"action": "issue", "kind": RecordKind.SOURCE.value, "payload": {}})
        response = self.session._verifier_connection.recv()
        self.assertFalse(response["ok"])
        self.assertIn("not available", response["error"])

    def test_closed_session_fails_closed(self) -> None:
        self.session.close()
        self.assertFalse(self.session.verify(self.source))

    def test_public_module_import_does_not_hold_live_session(self) -> None:
        live_sessions = [value for value in vars(core).values() if isinstance(value, AuthoritySession)]
        self.assertEqual(live_sessions, [])
