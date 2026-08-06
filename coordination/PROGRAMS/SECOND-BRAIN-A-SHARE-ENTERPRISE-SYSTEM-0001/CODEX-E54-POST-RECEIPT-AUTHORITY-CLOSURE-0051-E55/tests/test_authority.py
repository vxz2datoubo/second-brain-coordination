from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from e55_authority.authority import (  # noqa: E402
    AdmissionPolicy,
    AtomFactory,
    AuthorityError,
    CanonicalAtom,
    EvidenceRecord,
    EvidenceRecordFactory,
    PacketFactory,
    PacketRecordKind,
    PacketSubrecord,
    PacketSubrecordFactory,
    RelationFactory,
    SourceAdmissionFactory,
    SourceEvidence,
    _json_tokens,
    build_ledger,
)


class SourceAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = SourceAdmissionFactory()

    def test_admitted_source_revalidates_all_invariants(self) -> None:
        source = self.factory.admit(b'{"claim":"alpha"}', source_id="fixture:one", format_name="json")
        self.assertTrue(self.factory.verify(source))
        object.__setattr__(source, "source_id", "bad space")
        self.assertFalse(self.factory.verify(source))

    def test_direct_constructor_cannot_pass_factory_verification(self) -> None:
        raw = b'{"claim":"alpha"}'
        direct = SourceEvidence(raw, "fixture:one", "json", __import__("hashlib").sha256(raw).hexdigest(), "e55-admission-policy-v1", object())
        self.assertFalse(self.factory.verify(direct))
        sealed_but_unissued = SourceEvidence(raw, "fixture:one", "json", __import__("hashlib").sha256(raw).hexdigest(), self.factory.policy.version, self.factory._seal)
        self.assertFalse(self.factory.verify(sealed_but_unissued))
        with self.assertRaises(AuthorityError):
            build_ledger(self.factory, direct)

    def test_object_new_forgery_cannot_pass_factory_verification(self) -> None:
        forged = object.__new__(SourceEvidence)
        object.__setattr__(forged, "_data", b'{"claim":"alpha"}')
        object.__setattr__(forged, "source_id", "fixture:one")
        object.__setattr__(forged, "format_name", "json")
        object.__setattr__(forged, "source_sha256", "0" * 64)
        object.__setattr__(forged, "policy_version", "e55-admission-policy-v1")
        object.__setattr__(forged, "_seal", object())
        self.assertFalse(self.factory.verify(forged))

    def test_invalid_utf8_and_unsupported_format_fail_closed(self) -> None:
        with self.assertRaises(AuthorityError):
            self.factory.admit(b"\xff", source_id="fixture:one", format_name="text")
        with self.assertRaises(AuthorityError):
            self.factory.admit(b"safe", source_id="fixture:one", format_name="xml")

    def test_private_boundary_variants_are_rejected(self) -> None:
        for value in ("-----BEGIN", "-----BEGIN RSA PRIVATE KEY-----", "-----BEGIN OPENSSH PRIVATE", "-----BEGIN ENCRYPTED"):
            with self.subTest(value=value), self.assertRaises(AuthorityError):
                self.factory.admit(value.encode("utf-8"), source_id="fixture:one", format_name="text")

    def test_token_prefix_percent_and_base64_variants_are_rejected(self) -> None:
        for value in ("ghp_", "%67%68%70%5F", "Z2hwXw=="):
            with self.subTest(value=value), self.assertRaises(AuthorityError):
                self.factory.admit(value.encode("utf-8"), source_id="fixture:one", format_name="text")

    def test_decoded_json_escape_marker_is_rejected_before_atomization(self) -> None:
        with self.assertRaises(AuthorityError):
            self.factory.admit(b'{"claim":"\\u0067hp_"}', source_id="fixture:one", format_name="json")

    def test_duplicate_json_key_is_rejected(self) -> None:
        with self.assertRaises(AuthorityError):
            self.factory.admit(b'{"claim":"alpha","claim":"beta"}', source_id="fixture:one", format_name="json")

    def test_jsonl_malformed_second_line_is_rejected(self) -> None:
        with self.assertRaises(AuthorityError):
            self.factory.admit(b'{"claim":"alpha"}\n{"broken":', source_id="fixture:one", format_name="jsonl")


class SemanticEvidenceTests(unittest.TestCase):
    def _graph(self, payload: bytes = b'{"one":"alpha","two":"beta"}'):
        admission = SourceAdmissionFactory()
        source = admission.admit(payload, source_id="fixture:graph", format_name="json")
        ledger = build_ledger(admission, source)
        atoms = AtomFactory(ledger)
        evidence = EvidenceRecordFactory(ledger)
        relations = RelationFactory(atoms, evidence)
        records = PacketSubrecordFactory(evidence)
        return admission, source, ledger, atoms, evidence, relations, records

    def test_literal_json_value_is_semantic_but_key_and_punctuation_are_not(self) -> None:
        _, source, ledger, *_ = self._graph()
        self.assertEqual([span.decoded_text for span in ledger.semantic_spans], ["alpha", "beta"])
        self.assertFalse(any(span.start == 0 for span in ledger.semantic_spans))
        self.assertTrue(ledger.verify())
        self.assertEqual(source.bytes_slice(0, 1), b"{")

    def test_json_escape_bytes_are_structural_and_not_atom_candidate(self) -> None:
        admission = SourceAdmissionFactory()
        source = admission.admit(b'{"claim":"al\\u0070ha"}', source_id="fixture:escape", format_name="json")
        tokens = _json_tokens(source.bytes_slice(0, source.byte_length))
        value_token = [item for item in tokens if not item.is_key][0]
        self.assertEqual(value_token.decoded_text, "alpha")
        self.assertTrue(value_token.has_escape_syntax)
        self.assertTrue(any(not item.is_literal_source for item in value_token.decoded_characters))
        self.assertEqual(build_ledger(admission, source).semantic_spans, ())

    def test_relation_requires_issued_semantic_evidence_not_structural_punctuation(self) -> None:
        _, source, ledger, atoms, evidence, relations, _ = self._graph()
        first, second = (atoms.issue(span.span_id) for span in ledger.semantic_spans)
        with self.assertRaises(AuthorityError):
            evidence.issue("not-a-span", purpose="relation", statement="punctuation")
        record = evidence.issue(ledger.semantic_spans[0].span_id, purpose="relation", statement="alpha supports beta")
        relation = relations.issue(first.atom_id, second.atom_id, relation_type="supports", evidence=record)
        self.assertTrue(relations.verify(relation))
        self.assertEqual(source.bytes_slice(0, 1), b"{")

    def test_relation_with_forged_evidence_record_is_rejected(self) -> None:
        _, _, ledger, atoms, evidence, relations, _ = self._graph()
        first, second = (atoms.issue(span.span_id) for span in ledger.semantic_spans)
        forged = EvidenceRecord("evidence:forged", "relation", ledger.semantic_spans[0].span_id, "0" * 64, "0" * 64, "fake")
        with self.assertRaises(AuthorityError):
            relations.issue(first.atom_id, second.atom_id, relation_type="supports", evidence=forged)

    def test_atom_identity_forgery_is_rejected(self) -> None:
        _, _, ledger, atoms, _, _, _ = self._graph()
        atom = atoms.issue(ledger.semantic_spans[0].span_id)
        forged = CanonicalAtom(atom.atom_id, atom.span_id, atom.atom_type, atom.source_sha256, "changed", atom.evidence_sha256)
        self.assertFalse(atoms.verify(forged))

    def test_packet_requires_typed_evidence_bound_subrecords(self) -> None:
        _, _, ledger, atoms, evidence, relations, records = self._graph()
        first, second = (atoms.issue(span.span_id) for span in ledger.semantic_spans)
        record = evidence.issue(ledger.semantic_spans[0].span_id, purpose="relation", statement="alpha supports beta")
        relation = relations.issue(first.atom_id, second.atom_id, relation_type="supports", evidence=record)
        unknown = records.issue(PacketRecordKind.UNKNOWN, record, value="scope remains unknown", status="UNKNOWN")
        validation = records.issue(PacketRecordKind.VALIDATION, record, value="checked candidate", status="PASS")
        packet_factory = PacketFactory(ledger, atoms, relations, records)
        packet = packet_factory.issue(atoms=[first, second], relations=[relation], records=[unknown, validation])
        self.assertTrue(packet_factory.verify(packet))
        forged = PacketSubrecord(unknown.record_id, unknown.kind, unknown.evidence_record_id, "changed", unknown.status)
        self.assertFalse(records.verify(forged))

    def test_packet_rejects_duplicate_or_foreign_records(self) -> None:
        _, _, ledger, atoms, evidence, relations, records = self._graph()
        first, second = (atoms.issue(span.span_id) for span in ledger.semantic_spans)
        record = evidence.issue(ledger.semantic_spans[0].span_id, purpose="relation", statement="alpha supports beta")
        relation = relations.issue(first.atom_id, second.atom_id, relation_type="supports", evidence=record)
        unknown = records.issue(PacketRecordKind.UNKNOWN, record, value="scope remains unknown", status="UNKNOWN")
        packet_factory = PacketFactory(ledger, atoms, relations, records)
        with self.assertRaises(AuthorityError):
            packet_factory.issue(atoms=[first, first], relations=[relation], records=[unknown])
        foreign = PacketSubrecord("packet-record:foreign", PacketRecordKind.UNKNOWN, record.record_id, "foreign", "UNKNOWN")
        with self.assertRaises(AuthorityError):
            packet_factory.issue(atoms=[first, second], relations=[relation], records=[foreign])

    def test_text_and_markdown_line_evidence_remain_deterministic(self) -> None:
        for format_name, payload in (("text", b"alpha\nbeta\n"), ("markdown", b"alpha\nbeta\n")):
            admission = SourceAdmissionFactory(AdmissionPolicy())
            source = admission.admit(payload, source_id=f"fixture:{format_name}", format_name=format_name)
            ledger = build_ledger(admission, source)
            self.assertTrue(ledger.verify())
            self.assertEqual([item.decoded_text for item in ledger.semantic_spans], ["alpha", "beta"])


if __name__ == "__main__":
    unittest.main()
