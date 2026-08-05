from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from e54_authority import (
    AtomFactory,
    AuthorityError,
    CanonicalPacketFactory,
    FieldRule,
    RelationFactory,
    SourceEvidence,
    SpanOwner,
    VerifiedAtomRegistry,
    build_ledger,
    scan_commit_range,
    validate_receipt_fields,
    validate_environment_evidence,
    validate_matrix,
    verify_final_receipt,
    build_canonical_evidence,
)


def owner_at(ledger, offset: int) -> SpanOwner:
    for span in ledger.spans:
        if span.start <= offset < span.end:
            return span.owner
    raise AssertionError(f"no ownership at {offset}")


def graph(payload: bytes = b'{"left":"alpha","right":"beta"}'):
    evidence = SourceEvidence.from_bytes(payload, source_id="synthetic:graph", format_name="json")
    ledger = build_ledger(evidence)
    factory = AtomFactory(evidence, ledger)
    atoms = [factory.issue(span.start, span.end) for span in ledger.spans if span.owner is SpanOwner.ATOM_CANDIDATE]
    registry = VerifiedAtomRegistry(factory)
    for atom in atoms:
        registry.register(atom)
    relations = RelationFactory(registry)
    relation = relations.issue(atoms[0].atom_id, atoms[1].atom_id, start=0, end=1)
    packets = CanonicalPacketFactory(evidence, ledger, registry, relations)
    return evidence, ledger, factory, registry, relations, atoms, relation, packets


class ManifestAndPacketTests(unittest.TestCase):
    def test_json_value_content_is_candidate_but_key_and_punctuation_are_structural(self) -> None:
        evidence = SourceEvidence.from_bytes(b'{"key":"alpha"}', source_id="synthetic:json", format_name="json")
        ledger = build_ledger(evidence)
        self.assertTrue(ledger.verify())
        self.assertIs(owner_at(ledger, 2), SpanOwner.STRUCTURAL)  # key body
        self.assertIs(owner_at(ledger, 6), SpanOwner.STRUCTURAL)  # colon
        self.assertIs(owner_at(ledger, 8), SpanOwner.ATOM_CANDIDATE)  # value body
        self.assertEqual(sum(span.end - span.start for span in ledger.spans), evidence.byte_length)

    def test_json_invalid_fails_closed(self) -> None:
        evidence = SourceEvidence.from_bytes(b'{"key":', source_id="synthetic:bad", format_name="json")
        with self.assertRaises(AuthorityError):
            build_ledger(evidence)

    def test_json_escape_and_trailing_syntax_stay_structural(self) -> None:
        evidence = SourceEvidence.from_bytes(b'{"key":"a\\\"b"}', source_id="synthetic:escaped", format_name="json")
        ledger = build_ledger(evidence)
        self.assertIs(owner_at(ledger, 0), SpanOwner.STRUCTURAL)
        self.assertIs(owner_at(ledger, len(evidence._data) - 1), SpanOwner.STRUCTURAL)
        self.assertTrue(ledger.verify())

    def test_json_array_string_value_is_candidate_without_delimiters(self) -> None:
        data = b'["alpha","beta"]'
        ledger = build_ledger(SourceEvidence.from_bytes(data, source_id="synthetic:array", format_name="json"))
        self.assertIs(owner_at(ledger, 0), SpanOwner.STRUCTURAL)
        self.assertIs(owner_at(ledger, data.index(b"alpha")), SpanOwner.ATOM_CANDIDATE)
        self.assertIs(owner_at(ledger, data.index(b",")), SpanOwner.STRUCTURAL)

    def test_json_empty_string_does_not_create_empty_atom_span(self) -> None:
        ledger = build_ledger(SourceEvidence.from_bytes(b'{"claim":""}', source_id="synthetic:empty", format_name="json"))
        self.assertEqual([span for span in ledger.spans if span.owner is SpanOwner.ATOM_CANDIDATE], [])

    def test_jsonl_line_boundary_is_structural(self) -> None:
        data = b'{"key":"one"}\n{"key":"two"}\n'
        evidence = SourceEvidence.from_bytes(data, source_id="synthetic:jsonl", format_name="jsonl")
        ledger = build_ledger(evidence)
        self.assertIs(owner_at(ledger, data.index(b"\n")), SpanOwner.STRUCTURAL)
        self.assertEqual(len([span for span in ledger.spans if span.owner is SpanOwner.ATOM_CANDIDATE]), 2)

    def test_jsonl_malformed_second_record_fails_closed(self) -> None:
        evidence = SourceEvidence.from_bytes(b'{"key":"one"}\n{"key":', source_id="synthetic:jsonl-bad", format_name="jsonl")
        with self.assertRaises(AuthorityError):
            build_ledger(evidence)

    def test_jsonl_blank_line_is_structural_not_a_candidate(self) -> None:
        data = b'{"claim":"one"}\n\n{"claim":"two"}\n'
        ledger = build_ledger(SourceEvidence.from_bytes(data, source_id="synthetic:blank-jsonl", format_name="jsonl"))
        self.assertIs(owner_at(ledger, data.index(b"\n\n") + 1), SpanOwner.STRUCTURAL)

    def test_markdown_inline_table_row_is_structural(self) -> None:
        data = b"name | value\n"
        ledger = build_ledger(SourceEvidence.from_bytes(data, source_id="synthetic:table", format_name="markdown"))
        self.assertIs(owner_at(ledger, 0), SpanOwner.STRUCTURAL)

    def test_markdown_structural_categories(self) -> None:
        data = b"# H\n> quote\n- list\n| a | b |\n```\ncode\n```\nplain\n"
        evidence = SourceEvidence.from_bytes(data, source_id="synthetic:markdown", format_name="markdown")
        ledger = build_ledger(evidence)
        self.assertIs(owner_at(ledger, 0), SpanOwner.STRUCTURAL)  # heading
        self.assertIs(owner_at(ledger, data.index(b">") + 1), SpanOwner.STRUCTURAL)  # quote marker
        self.assertIs(owner_at(ledger, data.index(b"quote")), SpanOwner.ATOM_CANDIDATE)
        self.assertIs(owner_at(ledger, data.index(b"-")), SpanOwner.STRUCTURAL)  # list marker
        self.assertIs(owner_at(ledger, data.index(b"list")), SpanOwner.ATOM_CANDIDATE)
        self.assertIs(owner_at(ledger, data.index(b"|")), SpanOwner.STRUCTURAL)  # table
        self.assertIs(owner_at(ledger, data.index(b"code")), SpanOwner.STRUCTURAL)  # fenced body
        self.assertIs(owner_at(ledger, data.index(b"plain")), SpanOwner.ATOM_CANDIDATE)

    def test_markdown_unterminated_fence_fails_closed(self) -> None:
        evidence = SourceEvidence.from_bytes(b"```\ncode\n", source_id="synthetic:fence", format_name="markdown")
        with self.assertRaises(AuthorityError):
            build_ledger(evidence)

    def test_markdown_fence_terminator_and_code_body_are_structural(self) -> None:
        data = b"```python\nvalue = 1\n```\nbody\n"
        ledger = build_ledger(SourceEvidence.from_bytes(data, source_id="synthetic:fenced", format_name="markdown"))
        self.assertIs(owner_at(ledger, data.index(b"value")), SpanOwner.STRUCTURAL)
        self.assertIs(owner_at(ledger, data.rindex(b"```")), SpanOwner.STRUCTURAL)
        self.assertIs(owner_at(ledger, data.index(b"body")), SpanOwner.ATOM_CANDIDATE)

    def test_redacted_marker_is_not_atom_content(self) -> None:
        data = b"[REDACTED]\n"
        ledger = build_ledger(SourceEvidence.from_bytes(data, source_id="synthetic:redacted", format_name="markdown"))
        self.assertIs(owner_at(ledger, 0), SpanOwner.REDACTED)

    def test_manifest_nested_identity_is_deeply_immutable(self) -> None:
        _evidence, ledger, *_ = graph()
        manifest = ledger.coverage_manifest
        with self.assertRaises(TypeError):
            manifest["source_identity"]["source_id"] = "forged"  # type: ignore[index]
        self.assertTrue(ledger.verify())

    def test_manifest_recomputation_rejects_ordinary_bypass(self) -> None:
        _evidence, ledger, *_ = graph()
        object.__setattr__(ledger, "_manifest", {"coverage_sha256": "forged"})
        self.assertFalse(ledger.verify())

    def test_packet_verification_rebuilds_complete_graph(self) -> None:
        _evidence, _ledger, _factory, _registry, _relations, atoms, relation, packets = graph()
        packet = packets.issue(atoms=atoms, relations=[relation], unknowns=["unknown"], conflicts=["conflict"], redaction_lineage=["redacted"], validation={"result": "pass"})
        self.assertTrue(packets.verify(packet))
        object.__setattr__(packet, "canonical_json", b"{}")
        self.assertFalse(packets.verify(packet))

    def test_packet_projection_alias_divergence_is_rejected(self) -> None:
        _evidence, _ledger, _factory, _registry, _relations, atoms, relation, packets = graph()
        packet = packets.issue(atoms=atoms, relations=[relation])
        object.__setattr__(packet, "source_identity", {"source_id": "forged"})
        self.assertFalse(packets.verify(packet))

    def test_packet_rejects_foreign_atom(self) -> None:
        _evidence, _ledger, _factory, _registry, _relations, atoms, relation, packets = graph()
        with self.assertRaises(AuthorityError):
            packets.issue(atoms=[atoms[0], atoms[0]], relations=[relation])

    def test_field_evidence_is_recomputed_from_exact_value_span(self) -> None:
        _evidence, _ledger, factory, _registry, _relations, atoms, relation, packets = graph()
        field = factory.extract_field(atoms[0], name="word", start=atoms[0].start, end=atoms[0].end, rule=FieldRule.EXACT_UTF8_SLICE)
        packet = packets.issue(atoms=atoms, relations=[relation], fields=[field])
        self.assertTrue(packets.verify(packet))
        object.__setattr__(field, "value", "forged")
        self.assertFalse(packets.verify(packet))

    def test_partial_private_key_marker_is_blocked_before_atomization(self) -> None:
        with self.assertRaises(AuthorityError):
            marker = b"-----BEGIN " + b"PRIVATE" + b" KEY-----"
            SourceEvidence.from_bytes(marker + b"\\nSYNTHETIC\\n", source_id="synthetic:blocked", format_name="text")

    def test_field_verifier_rejects_changed_value(self) -> None:
        _evidence, _ledger, factory, _registry, _relations, atoms, _relation, _packets = graph()
        field = factory.extract_field(atoms[0], name="word", start=atoms[0].start, end=atoms[0].end, rule=FieldRule.EXACT_UTF8_SLICE)
        self.assertTrue(factory.verify_field(field))
        object.__setattr__(field, "value", "forged")
        self.assertFalse(factory.verify_field(field))

    def test_field_rejects_span_and_rule_mismatch(self) -> None:
        _evidence, _ledger, factory, _registry, _relations, atoms, _relation, _packets = graph()
        with self.assertRaises(AuthorityError):
            factory.extract_field(atoms[0], name="bad", start=atoms[0].start - 1, end=atoms[0].end, rule=FieldRule.EXACT_UTF8_SLICE)
        with self.assertRaises(AuthorityError):
            factory.extract_field(atoms[0], name="bad", start=atoms[0].start, end=atoms[0].end, rule=FieldRule.JSON_STRING)

    def test_relation_binds_exact_evidence_slice_not_source_digest(self) -> None:
        evidence, _ledger, _factory, _registry, relations, _atoms, relation, _packets = graph()
        self.assertNotEqual(relation.evidence_sha256, evidence.source_sha256)
        self.assertTrue(relations.verify(relation))

    def test_relation_substitution_of_source_digest_is_rejected(self) -> None:
        evidence, _ledger, _factory, _registry, relations, _atoms, relation, _packets = graph()
        object.__setattr__(relation, "evidence_sha256", evidence.source_sha256)
        self.assertFalse(relations.verify(relation))

    def test_relation_endpoint_forgery_is_rejected(self) -> None:
        _evidence, _ledger, _factory, _registry, relations, atoms, relation, _packets = graph()
        object.__setattr__(relation, "target_atom_id", atoms[0].atom_id)
        self.assertFalse(relations.verify(relation))

    def test_relation_foreign_source_digest_is_rejected(self) -> None:
        _evidence, _ledger, _factory, _registry, relations, _atoms, relation, _packets = graph()
        object.__setattr__(relation, "source_sha256", "f" * 64)
        self.assertFalse(relations.verify(relation))

    def test_packet_graph_exposes_unknown_conflict_and_redaction_lineage(self) -> None:
        _evidence, _ledger, _factory, _registry, _relations, atoms, relation, packets = graph()
        packet = packets.issue(atoms=atoms, relations=[relation], unknowns=["u"], conflicts=["c"], redaction_lineage=["r"], validation={"state": "ok"})
        body = json.loads(packet.canonical_json)
        self.assertEqual(body["unknowns"], ["u"])
        self.assertEqual(body["conflicts"], ["c"])
        self.assertEqual(body["redaction_lineage"], ["r"])
        self.assertEqual(body["validation"], {"state": "ok"})


class HygieneAndTopologyTests(unittest.TestCase):
    def _git(self, directory: Path, *args: str) -> None:
        subprocess.run(["git", "-C", str(directory), *args], check=True, capture_output=True, text=True)

    def test_hygiene_sees_generated_file_added_then_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            self._git(repo, "init")
            self._git(repo, "config", "user.email", "e54@example.invalid")
            self._git(repo, "config", "user.name", "E54")
            (repo / "keep.txt").write_text("base", encoding="utf-8")
            self._git(repo, "add", "keep.txt")
            self._git(repo, "commit", "-m", "base")
            base = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            (repo / "generated.db").write_text("not a real database", encoding="utf-8")
            self._git(repo, "add", "generated.db")
            self._git(repo, "commit", "-m", "add generated")
            (repo / "generated.db").unlink()
            self._git(repo, "add", "-u")
            self._git(repo, "commit", "-m", "delete generated")
            report = scan_commit_range(repo, base)
            self.assertFalse(report.clean)
            self.assertIn("generated.db", [item.path for item in report.forbidden_history_paths])
            self.assertNotIn("generated.db", report.final_tree_paths)

    def test_receipt_requires_real_identity_shapes_and_binding(self) -> None:
        sha = "a" * 40
        receipt = {
            "task_id": "task", "route_epoch": 56, "base_sha": sha, "plan_sha": sha,
            "tested_sha": sha, "receipt_sha": sha, "workflow": "workflow.yml",
            "tested_run_id": 1, "receipt_run_id": 2, "completion_signal": "signal",
            "external_receipt_binding": {"head_sha": sha, "canonical_artifact_ids": [1, 2, 3, 4, 5, 6], "compare_artifact_sha256": "b" * 64},
        }
        validate_receipt_fields(receipt, task_id="task", completion_signal="signal", workflow="workflow.yml")

    def test_receipt_rejects_placeholder_sha_and_wrong_artifact_count(self) -> None:
        receipt = {
            "task_id": "task", "route_epoch": 56, "base_sha": "x", "plan_sha": "a" * 40,
            "tested_sha": "a" * 40, "receipt_sha": "a" * 40, "workflow": "workflow.yml",
            "tested_run_id": 1, "receipt_run_id": 2, "completion_signal": "signal",
            "external_receipt_binding": {"head_sha": "a" * 40, "canonical_artifact_ids": [1], "compare_artifact_sha256": "b" * 64},
        }
        with self.assertRaises(AuthorityError):
            validate_receipt_fields(receipt, task_id="task", completion_signal="signal", workflow="workflow.yml")

    def test_receipt_rejects_short_sha_even_when_artifacts_are_valid(self) -> None:
        receipt = {
            "task_id": "task", "route_epoch": 56, "base_sha": "x", "plan_sha": "a" * 40,
            "tested_sha": "a" * 40, "receipt_sha": "a" * 40, "workflow": "workflow.yml",
            "tested_run_id": 1, "receipt_run_id": 2, "completion_signal": "signal",
            "external_receipt_binding": {"head_sha": "a" * 40, "canonical_artifact_ids": [1, 2, 3, 4, 5, 6], "compare_artifact_sha256": "b" * 64},
        }
        with self.assertRaises(AuthorityError):
            validate_receipt_fields(receipt, task_id="task", completion_signal="signal", workflow="workflow.yml")

    def test_provider_environment_rejects_changed_head(self) -> None:
        head = "a" * 40
        environment = {
            "head_sha": head, "test_count": 23, "mutation_count": 2, "mutation_ids": ["M1", "M2"],
            "command_sha256": "b" * 64, "stdout_sha256": "c" * 64, "stderr_sha256": "d" * 64,
            "canonical_artifact_sha256": "e" * 64, "python_version": "3.11", "hash_seed": "0",
        }
        validate_environment_evidence(environment, expected_head=head, expected_test_count=23, expected_mutation_ids=["M1", "M2"])
        environment["head_sha"] = "f" * 40
        with self.assertRaises(AuthorityError):
            validate_environment_evidence(environment, expected_head=head, expected_test_count=23, expected_mutation_ids=["M1", "M2"])

    def test_provider_environment_rejects_changed_canonical_artifact(self) -> None:
        head = "a" * 40
        artifact = "e" * 64
        environment = {
            "head_sha": head, "test_count": 23, "mutation_count": 2, "mutation_ids": ["M1", "M2"],
            "command_sha256": "b" * 64, "stdout_sha256": "c" * 64, "stderr_sha256": "d" * 64,
            "canonical_artifact_sha256": artifact, "python_version": "3.11", "hash_seed": "0",
        }
        validate_environment_evidence(environment, expected_head=head, expected_test_count=23, expected_mutation_ids=["M1", "M2"], expected_canonical_artifact_sha256=artifact)
        environment["canonical_artifact_sha256"] = "f" * 64
        with self.assertRaises(AuthorityError):
            validate_environment_evidence(environment, expected_head=head, expected_test_count=23, expected_mutation_ids=["M1", "M2"], expected_canonical_artifact_sha256=artifact)

    def test_provider_environment_rejects_missing_mutation_ids(self) -> None:
        head = "a" * 40
        environment = {
            "head_sha": head, "test_count": 23, "mutation_count": 2, "mutation_ids": [],
            "command_sha256": "b" * 64, "stdout_sha256": "c" * 64, "stderr_sha256": "d" * 64,
            "canonical_artifact_sha256": "e" * 64, "python_version": "3.11", "hash_seed": "0",
        }
        with self.assertRaises(AuthorityError):
            validate_environment_evidence(environment, expected_head=head, expected_test_count=23, expected_mutation_ids=["M1", "M2"])

    def test_provider_matrix_requires_exact_six_version_seed_pairs(self) -> None:
        head = "a" * 40
        base = {
            "head_sha": head, "test_count": 23, "mutation_count": 1, "mutation_ids": ["M1"],
            "command_sha256": "b" * 64, "stdout_sha256": "c" * 64, "stderr_sha256": "d" * 64,
            "canonical_artifact_sha256": "e" * 64,
        }
        environments = [{**base, "python_version": version, "hash_seed": seed} for version in ("3.11", "3.13") for seed in ("0", "1", "777")]
        validate_matrix(environments, expected_head=head, expected_test_count=23, expected_mutation_ids=["M1"], expected_canonical_artifact_sha256="e" * 64)
        with self.assertRaises(AuthorityError):
            validate_matrix(environments[:-1], expected_head=head, expected_test_count=23, expected_mutation_ids=["M1"], expected_canonical_artifact_sha256="e" * 64)

    def test_canonical_provider_evidence_covers_three_formats_deterministically(self) -> None:
        first = build_canonical_evidence(head_sha="a" * 40, test_count=28, mutation_ids=["M1", "M2"])
        second = build_canonical_evidence(head_sha="a" * 40, test_count=28, mutation_ids=["M2", "M1"])
        self.assertEqual(first, second)
        body = json.loads(first)
        self.assertEqual([item["format"] for item in body["fixtures"]], ["json", "jsonl", "markdown"])

    def test_receipt_rejects_signal_mismatch(self) -> None:
        sha = "a" * 40
        receipt = {
            "task_id": "task", "route_epoch": 56, "base_sha": sha, "plan_sha": sha,
            "tested_sha": sha, "receipt_sha": sha, "workflow": "workflow.yml",
            "tested_run_id": 1, "receipt_run_id": 2, "completion_signal": "wrong",
            "external_receipt_binding": {"head_sha": sha, "canonical_artifact_ids": [1, 2, 3, 4, 5, 6], "compare_artifact_sha256": "b" * 64},
        }
        with self.assertRaises(AuthorityError):
            validate_receipt_fields(receipt, task_id="task", completion_signal="signal", workflow="workflow.yml")

    def test_final_receipt_rejects_post_receipt_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            self._git(repo, "init")
            self._git(repo, "config", "user.email", "e54@example.invalid")
            self._git(repo, "config", "user.name", "E54")
            (repo / "base.txt").write_text("base", encoding="utf-8")
            self._git(repo, "add", "base.txt")
            self._git(repo, "commit", "-m", "base")
            (repo / "receipt.md").write_text("receipt", encoding="utf-8")
            self._git(repo, "add", "receipt.md")
            self._git(repo, "commit", "-m", "receipt")
            receipt = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            (repo / "later.txt").write_text("later", encoding="utf-8")
            self._git(repo, "add", "later.txt")
            self._git(repo, "commit", "-m", "post receipt")
            with self.assertRaises(AuthorityError):
                verify_final_receipt(repo, receipt, ["receipt.md"])


if __name__ == "__main__":
    unittest.main()
