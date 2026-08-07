from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e58_runtime import (  # noqa: E402
    EvidenceStatement,
    ExecutionReceipt,
    JsonlOwnershipError,
    PolicyRef,
    Polarity,
    Proposition,
    SemanticExecutionError,
    bootstrap_trusted_runtime,
    parse_jsonl_whole_source,
)


class SemanticExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = bootstrap_trusted_runtime()

    @staticmethod
    def evidence(
        source: str,
        polarity: Polarity = Polarity.AFFIRM,
        *,
        subject: str = "issuer-A",
        predicate: str = "reported",
        object_value: str = "fact-X",
        scope: str = "public",
        time_window: str = "2026-Q3",
    ) -> EvidenceStatement:
        return EvidenceStatement(
            source_id=source,
            proposition=Proposition(subject, predicate, object_value, polarity, scope, time_window),
            excerpt=f"{source}:{polarity.value}:{subject}:{predicate}:{object_value}:{scope}:{time_window}",
        )

    def validated(self, *args: object, **kwargs: object):
        return self.engine.validate_evidence(self.evidence(*args, **kwargs))

    def test_execution_receipt_is_accepted_only_by_issuing_verifier(self) -> None:
        _, receipt, packet = self.validated("source-one")
        self.assertTrue(self.engine.verifier.verify_execution(receipt))
        self.assertTrue(self.engine.verifier.verify_packet(packet))
        self.assertEqual(packet.payload()["receipt_id"], receipt.receipt_id)

    def test_caller_constructed_receipt_is_rejected(self) -> None:
        forged = ExecutionReceipt(
            capability_id=self.engine.verifier.capability_id,
            evaluator_id="caller",
            rule_id="caller.rule",
            rule_version="1",
            input_digest="0" * 64,
            run_id="1" * 64,
            outcome="PASS",
            output_digest="2" * 64,
            transcript_digest="3" * 64,
            attestation="4" * 64,
        )
        self.assertFalse(self.engine.verifier.verify_execution(forged))

    def test_tampered_issued_receipt_is_rejected(self) -> None:
        _, receipt, _ = self.validated("source-one")
        self.assertFalse(self.engine.verifier.verify_execution(replace(receipt, outcome="FAIL")))

    def test_verifier_capability_has_no_issue_method(self) -> None:
        self.assertFalse(hasattr(self.engine.verifier, "issue"))
        self.assertFalse(hasattr(self.engine.verifier, "register_evaluator"))

    def test_foreign_runtime_cannot_substitute_for_pinned_verifier(self) -> None:
        _, receipt, _ = self.validated("source-one")
        foreign = bootstrap_trusted_runtime()
        self.assertFalse(foreign.verifier.verify_execution(receipt))

    def test_deterministic_claim_is_distinct_from_ephemeral_attestation(self) -> None:
        _, first, _ = self.validated("source-one")
        other = bootstrap_trusted_runtime()
        _, second, _ = other.validate_evidence(self.evidence("source-one"))
        self.assertEqual(dict(first.claim()), dict(second.claim()))
        self.assertNotEqual(first.attestation, second.attestation)

    def test_opposed_independent_propositions_issue_conflict(self) -> None:
        left, _, _ = self.validated("source-one", Polarity.AFFIRM)
        right, _, _ = self.validated("source-two", Polarity.DENY)
        conflict = self.engine.issue_conflict(left, right)
        self.assertTrue(self.engine.verifier.verify_packet(conflict))
        self.assertEqual(conflict.payload()["packet_type"] if "packet_type" in conflict.payload() else conflict.packet_type, "CONFLICT")

    def test_unrelated_sources_are_not_a_conflict(self) -> None:
        left, _, _ = self.validated("source-one", Polarity.AFFIRM, object_value="fact-X")
        right, _, _ = self.validated("source-two", Polarity.DENY, object_value="fact-Y")
        with self.assertRaisesRegex(SemanticExecutionError, "identical proposition identity"):
            self.engine.issue_conflict(left, right)

    def test_same_polarity_is_not_a_conflict(self) -> None:
        left, _, _ = self.validated("source-one", Polarity.AFFIRM)
        right, _, _ = self.validated("source-two", Polarity.AFFIRM)
        with self.assertRaises(SemanticExecutionError):
            self.engine.issue_conflict(left, right)

    def test_scope_mismatch_is_not_a_conflict(self) -> None:
        left, _, _ = self.validated("source-one", Polarity.AFFIRM, scope="public")
        right, _, _ = self.validated("source-two", Polarity.DENY, scope="private")
        with self.assertRaises(SemanticExecutionError):
            self.engine.issue_conflict(left, right)

    def test_time_mismatch_is_not_a_conflict(self) -> None:
        left, _, _ = self.validated("source-one", Polarity.AFFIRM, time_window="2026-Q3")
        right, _, _ = self.validated("source-two", Polarity.DENY, time_window="2026-Q4")
        with self.assertRaises(SemanticExecutionError):
            self.engine.issue_conflict(left, right)

    def test_same_source_is_not_independent_conflict_evidence(self) -> None:
        left, _, _ = self.validated("source-one", Polarity.AFFIRM)
        right, _, _ = self.validated("source-one", Polarity.DENY)
        with self.assertRaisesRegex(SemanticExecutionError, "independently"):
            self.engine.issue_conflict(left, right)

    def test_relation_relevance_is_derived_from_validated_subject(self) -> None:
        left, _, _ = self.validated("source-one", subject="issuer-A", predicate="reported")
        right, _, _ = self.validated("source-two", subject="issuer-A", predicate="corrected")
        relation = self.engine.issue_relation(left, right, relation_type="SAME_SUBJECT_CONTEXT")
        self.assertTrue(self.engine.verifier.verify_packet(relation))
        self.assertEqual(relation.payload()["derived_basis"], "validated_shared_subject")
        self.assertNotIn("endpoint_ids", relation.payload())

    def test_relation_rejects_unrelated_validated_subjects(self) -> None:
        left, _, _ = self.validated("source-one", subject="issuer-A")
        right, _, _ = self.validated("source-two", subject="issuer-B")
        with self.assertRaisesRegex(SemanticExecutionError, "not derivable"):
            self.engine.issue_relation(left, right, relation_type="SAME_SUBJECT_CONTEXT")

    def test_relation_has_no_caller_endpoint_evidence_argument(self) -> None:
        left, _, _ = self.validated("source-one")
        right, _, _ = self.validated("source-two")
        with self.assertRaises(TypeError):
            self.engine.issue_relation(left, right, relation_type="SAME", endpoint_ids=(left.atom_id, right.atom_id))

    def test_forged_atom_is_rejected_before_relation(self) -> None:
        atom, receipt, _ = self.validated("source-one")
        forged = replace(atom, validation_receipt=replace(receipt, outcome="FAIL"))
        other, _, _ = self.validated("source-two")
        with self.assertRaisesRegex(SemanticExecutionError, "not issued"):
            self.engine.issue_relation(forged, other, relation_type="SAME")

    def test_registered_redaction_policy_emits_lineage_and_execution_receipt(self) -> None:
        packet = self.engine.issue_redaction(b"person alice@example.com", PolicyRef("e58.public-safe.email-redaction", "1.0.0"))
        payload = packet.payload()
        self.assertTrue(self.engine.verifier.verify_packet(packet))
        self.assertEqual(payload["policy_id"], "e58.public-safe.email-redaction")
        self.assertEqual(payload["policy_version"], "1.0.0")
        self.assertTrue(payload["classification_receipt_id"])
        self.assertEqual(payload["lineage"]["source_sha256"], payload["source_sha256"])

    def test_redaction_rejects_unknown_policy(self) -> None:
        with self.assertRaisesRegex(SemanticExecutionError, "not registered"):
            self.engine.issue_redaction(b"alice@example.com", PolicyRef("caller.policy", "1"))

    def test_redaction_rejects_unknown_policy_version(self) -> None:
        with self.assertRaisesRegex(SemanticExecutionError, "not registered"):
            self.engine.issue_redaction(b"alice@example.com", PolicyRef("e58.public-safe.email-redaction", "9.9.9"))

    def test_redaction_ranges_use_utf8_byte_offsets(self) -> None:
        packet = self.engine.issue_redaction("人 alice@example.com".encode("utf-8"), PolicyRef("e58.public-safe.email-redaction", "1.0.0"))
        self.assertEqual(packet.payload()["raw_ranges"], [[4, 21]])

    def test_redaction_rejects_non_utf8_source(self) -> None:
        with self.assertRaisesRegex(SemanticExecutionError, "strict UTF-8"):
            self.engine.issue_redaction(b"\xff", PolicyRef("e58.public-safe.email-redaction", "1.0.0"))


class JsonlWholeSourceOwnershipTests(unittest.TestCase):
    def assert_partition(self, ownership, source: bytes) -> None:
        ownership.assert_complete_partition()
        self.assertEqual(ownership.byte_length, len(source))
        self.assertEqual(ownership.source_sha256, __import__("hashlib").sha256(source).hexdigest())

    def test_empty_source_is_explicit_and_complete(self) -> None:
        ownership = parse_jsonl_whole_source(b"")
        self.assertEqual(ownership.status, "EMPTY_SOURCE")
        self.assertEqual(ownership.segments, ())
        self.assert_partition(ownership, b"")

    def test_blank_lines_and_crlf_are_owned(self) -> None:
        source = b"\r\n \t\r\n{\"a\":1}\r\n\n"
        ownership = parse_jsonl_whole_source(source)
        self.assertEqual(ownership.record_count, 1)
        self.assertEqual([(item.kind.value, item.raw.start, item.raw.end) for item in ownership.segments], [
            ("LINE_TERMINATOR", 0, 2),
            ("BLANK_LINE", 2, 4),
            ("LINE_TERMINATOR", 4, 6),
            ("JSON_RECORD", 6, 13),
            ("LINE_TERMINATOR", 13, 15),
            ("LINE_TERMINATOR", 15, 16),
        ])
        self.assert_partition(ownership, source)

    def test_cr_and_lf_records_have_global_offsets(self) -> None:
        source = b"{\"a\":1}\r{\"b\":2}\n"
        ownership = parse_jsonl_whole_source(source)
        records = [segment for segment in ownership.segments if segment.kind.value == "JSON_RECORD"]
        self.assertEqual([(item.raw.start, item.raw.end) for item in records], [(0, 7), (8, 15)])
        self.assert_partition(ownership, source)

    def test_whitespace_only_lines_are_not_silently_dropped(self) -> None:
        source = b" \t\n\r"
        ownership = parse_jsonl_whole_source(source)
        self.assertEqual(ownership.status, "NO_JSON_RECORDS")
        self.assertEqual([segment.kind.value for segment in ownership.segments], ["BLANK_LINE", "LINE_TERMINATOR", "LINE_TERMINATOR"])
        self.assert_partition(ownership, source)

    def test_final_record_without_terminator_is_owned(self) -> None:
        source = b"{\"a\":1}"
        ownership = parse_jsonl_whole_source(source)
        self.assertEqual(ownership.record_count, 1)
        self.assertEqual(ownership.segments[0].raw.end, len(source))
        self.assert_partition(ownership, source)

    def test_invalid_json_fails_closed_with_global_offset(self) -> None:
        with self.assertRaisesRegex(JsonlOwnershipError, "INVALID_JSONL_RECORD at byte offset 5"):
            parse_jsonl_whole_source(b"{\"a\":}\n")

    def test_non_utf8_record_fails_closed(self) -> None:
        with self.assertRaisesRegex(JsonlOwnershipError, "NON_UTF8_JSONL_RECORD at byte offset 5"):
            parse_jsonl_whole_source(b"{\"a\":\xff}\n")

    def test_isolated_high_surrogate_is_stable_error(self) -> None:
        with self.assertRaisesRegex(JsonlOwnershipError, "ISOLATED_HIGH_SURROGATE at byte offset 6"):
            parse_jsonl_whole_source(b"{\"a\":\"\\uD800\"}\n")

    def test_isolated_low_surrogate_is_stable_error(self) -> None:
        with self.assertRaisesRegex(JsonlOwnershipError, "ISOLATED_LOW_SURROGATE at byte offset 6"):
            parse_jsonl_whole_source(b"{\"a\":\"\\uDC00\"}\n")

    def test_valid_surrogate_pair_is_owned_without_unicode_encode_error(self) -> None:
        source = b"{\"a\":\"\\uD83D\\uDE00\"}\n"
        ownership = parse_jsonl_whole_source(source)
        self.assertEqual(ownership.record_count, 1)
        self.assert_partition(ownership, source)

    def test_literal_backslash_u_sequence_is_not_a_surrogate_escape(self) -> None:
        source = b"{\"a\":\"\\\\uD800\"}\n"
        ownership = parse_jsonl_whole_source(source)
        self.assertEqual(ownership.record_count, 1)
        self.assert_partition(ownership, source)

    def test_ownership_digest_changes_when_terminator_changes(self) -> None:
        lf = parse_jsonl_whole_source(b"{\"a\":1}\n")
        crlf = parse_jsonl_whole_source(b"{\"a\":1}\r\n")
        self.assertNotEqual(lf.digest, crlf.digest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
