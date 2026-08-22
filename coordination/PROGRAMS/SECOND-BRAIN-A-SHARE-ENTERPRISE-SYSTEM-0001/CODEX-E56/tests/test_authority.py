from __future__ import annotations

import unittest

from e56_authority.authority import (
    AdmissionPolicy,
    AtomFactory,
    AuthorityError,
    EvidenceFactory,
    PacketFactory,
    RelationFactory,
    RecordKind,
    SourceAdmission,
    SourceEvidence,
    SpanOwner,
    build_ledger,
)


class AuthorityBase(unittest.TestCase):
    def source(self, data: bytes = b'{"one":"alpha","two":"beta"}', format_name: str = "json"):
        admission = SourceAdmission(AdmissionPolicy())
        return admission, admission.admit(data, source_id="fixture/source", format_name=format_name)


class AdmissionTests(AuthorityBase):
    def test_forged_source_is_rejected(self):
        admission, source = self.source()
        forged = SourceEvidence(source.data, source.source_id, source.format_name, source.source_sha256, source.policy_identity)
        self.assertFalse(admission.verify(forged))
        with self.assertRaises(AuthorityError):
            build_ledger(admission, forged)

    def test_mutated_source_fields_fail_revalidation(self):
        admission, source = self.source()
        object.__setattr__(source, "policy_identity", "forged-policy")
        self.assertFalse(admission.verify(source))

    def test_authority_exposes_no_mutable_policy_or_registry(self):
        admission, _source = self.source()
        self.assertEqual(SourceAdmission.__slots__, ())
        self.assertFalse(hasattr(admission, "policy"))
        self.assertFalse(hasattr(admission, "_issued"))
        self.assertFalse(hasattr(admission, "_seal"))
        with self.assertRaises(AttributeError):
            object.__setattr__(admission, "policy", AdmissionPolicy(version="forged"))

    def test_duplicate_json_key_fails_closed(self):
        admission = SourceAdmission()
        with self.assertRaises(AuthorityError):
            admission.admit(b'{"one":"a","one":"b"}', source_id="fixture/duplicate", format_name="json")

    def test_blocked_marker_fails_closed(self):
        admission = SourceAdmission()
        with self.assertRaises(AuthorityError):
            admission.admit(b"ghp_example_token", source_id="fixture/marker", format_name="text")

    def test_invalid_source_id_fails_closed(self):
        with self.assertRaises(AuthorityError):
            SourceAdmission().admit(b"text", source_id="not allowed", format_name="text")


class OwnershipTests(AuthorityBase):
    def test_markdown_syntax_is_structural(self):
        admission, source = self.source(b"# Heading\n- item\n> quote\n```\ncode\n```\n| a | b |\n", "markdown")
        ledger = build_ledger(admission, source)
        semantic = "".join(span.decoded_text for span in ledger.semantic_spans)
        self.assertNotIn("#", semantic)
        self.assertNotIn("```", semantic)
        self.assertNotIn("|", semantic)
        self.assertIn("Heading", semantic)
        self.assertIn("item", semantic)
        self.assertTrue(any(span.owner is SpanOwner.STRUCTURAL for span in ledger.ownership))
        self.assertTrue(ledger.verify())

    def test_escaped_json_value_has_decoded_evidence_and_structural_escape(self):
        admission, source = self.source(b'{"text":"a\\nb"}')
        ledger = build_ledger(admission, source)
        target = next(span for span in ledger.semantic_spans if span.decoded_text == "a\nb")
        self.assertEqual(target.origin, "json_decoded_value_v1")
        self.assertGreaterEqual(len(target.raw_ranges), 3)
        slash_index = source.data.index(b"\\")
        slash_span = next(span for span in ledger.ownership if span.start <= slash_index < span.end)
        self.assertIs(slash_span.owner, SpanOwner.STRUCTURAL)

    def test_json_keys_are_not_semantic_atoms(self):
        admission, source = self.source(b'{"secret_key":"value"}')
        ledger = build_ledger(admission, source)
        self.assertEqual([span.decoded_text for span in ledger.semantic_spans], ["value"])

    def test_total_partition_is_contiguous(self):
        admission, source = self.source(b"first\n[REDACTED]\nsecond\n", "text")
        ledger = build_ledger(admission, source)
        self.assertEqual(ledger.ownership[0].start, 0)
        self.assertEqual(ledger.ownership[-1].end, len(source.data))
        self.assertTrue(all(left.end == right.start for left, right in zip(ledger.ownership, ledger.ownership[1:])))

    def test_jsonl_has_one_decoded_value_per_record(self):
        admission, source = self.source(b'{"a":"one"}\n{"b":"two"}\n', "jsonl")
        ledger = build_ledger(admission, source)
        self.assertEqual({item.decoded_text for item in ledger.semantic_spans}, {"one", "two"})

    def test_redacted_text_is_not_semantic(self):
        admission, source = self.source(b"visible\n[REDACTED]\n", "text")
        ledger = build_ledger(admission, source)
        self.assertEqual([item.decoded_text for item in ledger.semantic_spans], ["visible"])


class RecordTests(AuthorityBase):
    def records(self):
        admission, source = self.source()
        ledger = build_ledger(admission, source)
        evidence = EvidenceFactory(ledger)
        first, second = (evidence.issue(span.span_id) for span in ledger.semantic_spans)
        return evidence, PacketFactory(evidence), first, second

    def test_evidence_statement_must_be_derived(self):
        evidence, _packets, first, _second = self.records()
        with self.assertRaises(AuthorityError):
            evidence.issue(first.span_id, statement="unrelated prose")

    def test_packet_kind_specific_schema(self):
        _evidence, packets, first, _second = self.records()
        with self.assertRaises(AuthorityError):
            packets._issue(RecordKind.VALIDATION, first, {"value": "forged"})

    def test_packet_records_verify_only_when_issued(self):
        _evidence, packets, first, second = self.records()
        unknown = packets.unknown(first, reason="unresolved")
        conflict = packets.conflict(second, conflicting_evidence_id=first.record_id)
        validation = packets.validation(first, rule_id="fixture.rule", outcome="PASS")
        self.assertTrue(all(packets.verify(value) for value in (unknown, conflict, validation)))

    def test_atoms_require_verified_ledger(self):
        admission, source = self.source()
        ledger = build_ledger(admission, source)
        atoms = AtomFactory(ledger)
        atom = atoms.issue(ledger.semantic_spans[0].span_id)
        self.assertTrue(atoms.verify(atom))
        object.__setattr__(source, "source_id", "tampered")
        self.assertFalse(atoms.verify(atom))

    def test_relation_binds_verified_endpoints_and_evidence(self):
        admission, source = self.source()
        ledger = build_ledger(admission, source)
        atoms = AtomFactory(ledger)
        evidence = EvidenceFactory(ledger)
        left, right = (atoms.issue(span.span_id) for span in ledger.semantic_spans)
        record = evidence.issue(ledger.semantic_spans[0].span_id)
        relations = RelationFactory(atoms, evidence)
        relation = relations.issue(left, right, relation_type="supports", evidence=record)
        self.assertTrue(relations.verify(relation))


if __name__ == "__main__":
    unittest.main()
