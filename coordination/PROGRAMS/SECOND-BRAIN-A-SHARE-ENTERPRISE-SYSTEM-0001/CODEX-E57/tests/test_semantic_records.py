from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sys
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e57_authority.core import AuthorityError, AuthoritySession, RecordKind
from e57_authority.semantic import (
    ByteRange,
    EvaluatorReceipt,
    OwnershipResult,
    TypedValue,
    ValueKind,
    issue_atom,
    issue_conflict,
    issue_evidence,
    issue_redaction,
    issue_relation,
    issue_validation,
    parse_json_ownership,
    parse_jsonl_ownership,
    parse_markdown_ownership,
)


class SemanticRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = b'{"word":"\\ud83d\\ude03","n":12.5,"b":true,"z":null}'
        self.ownership = parse_json_ownership(self.data)
        self.session = AuthoritySession()
        self.source = self.session.issue_source(
            source_id="fixture/semantic.json",
            source_sha256=sha256(self.data).hexdigest(),
            format_name="json",
            byte_length=len(self.data),
        )

    def tearDown(self) -> None:
        self.session.close()

    def _value(self, kind: ValueKind):
        return next(item for item in self.ownership.values if item.kind is kind)

    def test_json_partition_is_complete_and_non_overlapping(self) -> None:
        self.ownership.assert_complete_partition()
        self.assertEqual(self.ownership.coverage[0].start, 0)
        self.assertEqual(self.ownership.coverage[-1].end, len(self.data))

    def test_partition_gap_is_rejected(self) -> None:
        malformed = OwnershipResult(
            source_sha256="0" * 64,
            format_name="json",
            byte_length=4,
            values=(TypedValue(ValueKind.TEXT, ByteRange(0, 1), "x"),),
            coverage=(ByteRange(0, 1), ByteRange(2, 4)),
        )
        with self.assertRaises(AuthorityError):
            malformed.assert_complete_partition()

    def test_surrogate_pair_has_one_decoded_character_with_full_raw_range(self) -> None:
        smile = next(
            character
            for value in self.ownership.values
            if value.kind is ValueKind.STRING
            for character in value.characters
            if character.text == "\U0001f603"
        )
        self.assertTrue(smile.escaped)
        self.assertEqual(self.data[smile.raw.start : smile.raw.end], b"\\ud83d\\ude03")

    def test_json_number_boolean_and_null_are_typed(self) -> None:
        kinds = {item.kind for item in self.ownership.values}
        self.assertTrue({ValueKind.NUMBER, ValueKind.BOOLEAN, ValueKind.NULL}.issubset(kinds))

    def test_invalid_json_fails_closed(self) -> None:
        with self.assertRaises(AuthorityError):
            parse_json_ownership(b'{"x": }')

    def test_jsonl_retains_each_nonempty_record(self) -> None:
        records = parse_jsonl_ownership(b'{"a":1}\n\n{"b":false}\r\n')
        self.assertEqual(len(records), 2)
        self.assertTrue(all(record.format_name == "jsonl" for record in records))

    def test_markdown_complex_constructs_are_typed_unknown(self) -> None:
        ownership = parse_markdown_ownership(b"plain\n`code`\n[a](b)\n|table|\n<div>x</div>\n")
        self.assertIn(ValueKind.UNKNOWN, {value.kind for value in ownership.values})
        ownership.assert_complete_partition()

    def test_evidence_is_derived_from_verified_source_span(self) -> None:
        evidence = issue_evidence(self.session, self.source, self.ownership, self._value(ValueKind.NUMBER))
        self.assertTrue(self.session.verify(evidence))
        self.assertEqual(evidence.payload()["source_record_id"], self.source.record_id)

    def test_evidence_rejects_value_from_other_ownership(self) -> None:
        other = parse_json_ownership(b'{"x":"other"}')
        with self.assertRaises(AuthorityError):
            issue_evidence(self.session, self.source, self.ownership, next(item for item in other.values if item.kind is ValueKind.STRING))

    def test_validation_requires_bound_execution_receipt(self) -> None:
        evidence = issue_evidence(self.session, self.source, self.ownership, self._value(ValueKind.NUMBER))
        receipt = EvaluatorReceipt("fixture-evaluator", "range-check", "1", evidence.payload_digest, "run-001", "PASS")
        packet = issue_validation(self.session, evidence, receipt)
        self.assertTrue(self.session.verify(packet))
        with self.assertRaises(AuthorityError):
            issue_validation(self.session, evidence, EvaluatorReceipt("fixture-evaluator", "range-check", "1", "wrong", "run-001", "PASS"))

    def test_conflict_needs_two_independent_verified_sources(self) -> None:
        left = issue_evidence(self.session, self.source, self.ownership, self._value(ValueKind.NUMBER))
        with AuthoritySession() as foreign:
            foreign_source = foreign.issue_source(
                source_id="fixture/other.json",
                source_sha256=sha256(b'{"x":2}').hexdigest(),
                format_name="json",
                byte_length=7,
            )
            # A foreign source cannot be silently mixed into this issuer session.
            self.assertFalse(self.session.verify(foreign_source))
        with self.assertRaises(AuthorityError):
            issue_conflict(self.session, left, left)

    def test_conflict_rejects_distinct_evidence_from_the_same_source(self) -> None:
        left = issue_evidence(self.session, self.source, self.ownership, self._value(ValueKind.NUMBER))
        right = issue_evidence(self.session, self.source, self.ownership, self._value(ValueKind.BOOLEAN))
        with self.assertRaises(AuthorityError):
            issue_conflict(self.session, left, right)

    def test_redaction_requires_exact_in_source_range_and_policy(self) -> None:
        packet = issue_redaction(self.session, self.source, ByteRange(1, 5), reason_policy_id="public-safe-v1")
        self.assertTrue(self.session.verify(packet))
        with self.assertRaises(AuthorityError):
            issue_redaction(self.session, self.source, ByteRange(1, len(self.data) + 1), reason_policy_id="public-safe-v1")

    def test_relation_requires_endpoint_bound_evidence(self) -> None:
        left_seed = issue_evidence(self.session, self.source, self.ownership, self._value(ValueKind.NUMBER))
        right_seed = issue_evidence(self.session, self.source, self.ownership, self._value(ValueKind.BOOLEAN))
        left, right = issue_atom(self.session, left_seed), issue_atom(self.session, right_seed)
        bound = issue_evidence(
            self.session,
            self.source,
            self.ownership,
            self._value(ValueKind.BOOLEAN),
            endpoint_ids=(left.record_id, right.record_id),
        )
        relation = issue_relation(self.session, left, right, bound, relation_type="supports")
        self.assertTrue(self.session.verify(relation))
        with self.assertRaises(AuthorityError):
            issue_relation(self.session, left, right, left_seed, relation_type="supports")

    def test_direct_packet_construction_has_no_authority(self) -> None:
        evidence = issue_evidence(self.session, self.source, self.ownership, self._value(ValueKind.NUMBER))
        packet = issue_validation(
            self.session,
            evidence,
            EvaluatorReceipt("fixture-evaluator", "range-check", "1", evidence.payload_digest, "run-001", "FAIL"),
        )
        forged = type(packet)(**dict(packet.wire()))
        self.assertFalse(self.session.verify(forged))

    def test_record_kind_requirements_fail_closed(self) -> None:
        with self.assertRaises(AuthorityError):
            self.session.require(self.source, RecordKind.EVIDENCE)
