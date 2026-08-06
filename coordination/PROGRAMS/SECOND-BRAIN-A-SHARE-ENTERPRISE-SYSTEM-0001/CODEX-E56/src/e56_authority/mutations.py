"""Execute real E56 production/tool mutations with exact restoration proof."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Sequence


@dataclass(frozen=True, slots=True)
class MutationSpec:
    mutation_id: str
    target: str
    old: str
    new: str
    test: str
    counterexample_id: str
    purpose: str


@dataclass(frozen=True, slots=True)
class MutationResult:
    mutation_id: str
    target: str
    counterexample_id: str
    purpose: str
    anchor_offset: int
    replacement_count: int
    pristine_sha256: str
    mutated_sha256: str
    restored_sha256: str
    command: tuple[str, ...]
    command_sha256: str
    mutated_exit_code: int
    restored_exit_code: int
    mutated_duration_ns: int
    restored_duration_ns: int
    mutated_stdout_sha256: str
    mutated_stderr_sha256: str
    restored_stdout_sha256: str
    restored_stderr_sha256: str

    def canonical_summary(self) -> dict[str, object]:
        return {
            "mutation_id": self.mutation_id,
            "target": self.target,
            "counterexample_id": self.counterexample_id,
            "anchor_offset": self.anchor_offset,
            "replacement_count": self.replacement_count,
            "pristine_sha256": self.pristine_sha256,
            "mutated_sha256": self.mutated_sha256,
            "restored_sha256": self.restored_sha256,
            "killed": self.mutated_exit_code != 0 and self.restored_exit_code == 0,
        }


MUTATION_SPECS: tuple[MutationSpec, ...] = (
    MutationSpec("MUT-ADMISSION-NO-INSTANCE-STATE", "src/e56_authority/authority.py", "__slots__ = ()", "__slots__ = (\"policy\",)", "test_authority.AdmissionTests.test_authority_exposes_no_mutable_policy_or_registry", "CE-INSTANCE-POLICY", "a caller can attach a mutable policy slot to an admission authority"),
    MutationSpec("MUT-ADMISSION-SELF-REGISTRATION", "src/e56_authority/authority.py", "if record is None or record.source is not value:\n                return False", "if record is None or record.source is not value:\n                return True", "test_authority.AdmissionTests.test_forged_source_is_rejected", "CE-FORGED-SOURCE", "an ordinary caller-minted source bypasses the closure-held registry"),
    MutationSpec("MUT-ADMISSION-POLICY-IDENTITY", "src/e56_authority/authority.py", "or value.policy_identity != record.policy_identity", "or False", "test_authority.AdmissionTests.test_mutated_source_fields_fail_revalidation", "CE-POLICY-IDENTITY", "a source can retain a forged issued policy identity"),
    MutationSpec("MUT-MARKDOWN-STRUCTURE", "src/e56_authority/authority.py", "_MD_PUNCTUATION = frozenset(b\"|`[]()_*#\")", "_MD_PUNCTUATION = frozenset()", "test_authority.OwnershipTests.test_markdown_syntax_is_structural", "CE-MARKDOWN-STRUCTURE", "Markdown punctuation becomes semantic evidence"),
    MutationSpec("MUT-ESCAPED-RAW-OWNERSHIP", "src/e56_authority/authority.py", "for item in token.characters if not item.escaped", "for item in token.characters", "test_authority.OwnershipTests.test_escaped_json_value_has_decoded_evidence_and_structural_escape", "CE-ESCAPED-VALUE", "JSON escape syntax becomes raw semantic ownership"),
    MutationSpec("MUT-EVIDENCE-STATEMENT", "src/e56_authority/authority.py", "if statement is not None and statement != derived:", "if False:", "test_authority.RecordTests.test_evidence_statement_must_be_derived", "CE-STATEMENT-MISMATCH", "caller-authored prose is accepted as source evidence"),
    MutationSpec("MUT-PACKET-KIND-SCHEMA", "src/e56_authority/authority.py", "if {key for key, _value in canonical} != allowed:", "if False:", "test_authority.RecordTests.test_packet_kind_specific_schema", "CE-PACKET-KIND", "a generic value/status payload bypasses kind-specific requirements"),
    MutationSpec("MUT-TOPOLOGY-PLAN-PARENT", "src/e56_authority/topology.py", "if _one_parent(repo, route.plan_sha) != route.base_sha:", "if False:", "test_topology_hygiene.TopologyTests.test_plan_parent_and_path_are_strict", "CE-PLAN-PARENT", "a plan commit from a non-base parent is accepted"),
    MutationSpec("MUT-TOPOLOGY-LINEAR", "src/e56_authority/topology.py", "if _one_parent(repo, commit) != previous:", "if False:", "test_topology_hygiene.TopologyTests.test_linear_chain_rejects_unexpected_parent", "CE-LINEAR-CHAIN", "an unexpected parent inside the route chain is accepted"),
    MutationSpec("MUT-HYGIENE-TASK-PATTERN", "src/e56_authority/hygiene.py", "return any(fnmatchcase(normalized, pattern) or fnmatchcase(\"/\" + normalized, pattern) for pattern in policy.forbidden_globs)", "return False", "test_topology_hygiene.HygieneTests.test_task_defined_pattern_is_enforced", "CE-HYGIENE-PATTERN", "versioned task-defined forbidden paths are ignored"),
    MutationSpec("MUT-CANONICAL-FIXTURE-RESULT", "src/e56_authority/provider.py", '"fixture_outcomes": fixture_outcomes,', '"fixture_outcomes": (),', "test_provider_tools.ProviderTests.test_canonical_contains_executed_fixture_outcomes", "CE-CANONICAL-FIXTURE", "canonical evidence omits actual fixture outcomes"),
    MutationSpec("MUT-PROVIDER-JOB-COUNT", "src/e56_authority/provider.py", "if observed_jobs != expected_jobs or len(jobs) != 7 or len(job_ids) != 7 or len(set(job_ids)) != 7:", "if False:", "test_provider_tools.ProviderTests.test_provider_snapshot_rejects_extra_job", "CE-PROVIDER-EXTRA-JOB", "unexpected Provider jobs are accepted"),
    MutationSpec("MUT-COMPARE-CANONICAL-EQUALITY", "tools/compare_provider_artifacts.py", "if len(set(canonical_bytes)) != 1:", "if False:", "test_provider_tools.ToolTests.test_compare_rejects_divergent_canonical_payloads", "CE-COMPARE-DIVERGENCE", "compare job accepts divergent canonical inner bytes"),
    MutationSpec("MUT-COMPARE-JOB-EVIDENCE", "tools/compare_provider_artifacts.py", "or evidence.get(\"job_name\") != expected_job_name", "or False", "test_provider_tools.ToolTests.test_compare_rejects_wrong_job_evidence", "CE-COMPARE-JOB-EVIDENCE", "compare job accepts an environment payload from the wrong matrix slot"),
    MutationSpec("MUT-COMPARE-RUNTIME-IDENTITY", "tools/compare_provider_artifacts.py", "or payload.get(\"python_version\") != expected_version", "or False", "test_provider_tools.ToolTests.test_compare_rejects_wrong_runtime_identity", "CE-COMPARE-RUNTIME", "compare job accepts an environment produced by the wrong interpreter"),
    MutationSpec("MUT-VERIFY-MUTATION-PAYLOAD", "tools/verify_provider_run.py", "if digest(mutation_payload) != environment[\"mutation_result_sha256\"]:", "if False:", "test_provider_tools.ToolTests.test_verifier_rejects_tampered_mutation_payload", "CE-MUTATION-PAYLOAD", "independent verifier accepts a tampered mutation-results payload"),
    MutationSpec("MUT-PROVIDER-ARTIFACT-IDENTITY", "src/e56_authority/provider.py", "if len(artifacts) != contract.artifact_count or len(set(names)) != contract.artifact_count or len(set(ids)) != contract.artifact_count:", "if False:", "test_provider_tools.ProviderTests.test_provider_snapshot_rejects_duplicate_artifact_id", "CE-DUPLICATE-ARTIFACT-ID", "Provider snapshot accepts duplicate artifact identities"),
    MutationSpec("MUT-PROVIDER-JOB-BINDING", "src/e56_authority/provider.py", "if item.get(\"job_name\") != expected_job_name or item.get(\"job_id\") != job[\"id\"] or item.get(\"run_id\") != snapshot[\"run_id\"]:", "if False:", "test_provider_tools.ProviderTests.test_provider_snapshot_rejects_compare_artifact_job_collision", "CE-COMPARE-JOB-BINDING", "compare artifact is bound to a matrix job instead of the compare job"),
)


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def _run(command: tuple[str, ...], environment: dict[str, str]) -> tuple[subprocess.CompletedProcess[bytes], int]:
    started = time.perf_counter_ns()
    result = subprocess.run(command, capture_output=True, env=environment, check=False, timeout=120)
    return result, time.perf_counter_ns() - started


def run_mutation_matrix(project_root: Path, specs: Sequence[MutationSpec] = MUTATION_SPECS) -> tuple[MutationResult, ...]:
    """Mutate actual task-local source/tool bytes one at a time and restore."""

    project_root = project_root.resolve()
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join((str(project_root / "src"), str(project_root / "tests"))), "PYTHONDONTWRITEBYTECODE": "1"}
    results: list[MutationResult] = []
    for spec in specs:
        target = project_root / spec.target
        pristine = target.read_bytes()
        source = pristine.decode("utf-8", "strict")
        count = source.count(spec.old)
        if count != 1:
            raise RuntimeError(f"mutation anchor mismatch for {spec.mutation_id}: {count}")
        mutated = source.replace(spec.old, spec.new, 1).encode("utf-8")
        anchor_offset = source.index(spec.old)
        command = (sys.executable, "-m", "unittest", spec.test, "-v")
        changed: subprocess.CompletedProcess[bytes] | None = None
        changed_duration = 0
        try:
            target.write_bytes(mutated)
            changed, changed_duration = _run(command, environment)
        finally:
            target.write_bytes(pristine)
        restored, restored_duration = _run(command, environment)
        if changed is None or target.read_bytes() != pristine:
            raise RuntimeError(f"mutation restoration failed for {spec.mutation_id}")
        if changed.returncode == 0:
            raise RuntimeError(f"surviving mutation: {spec.mutation_id}")
        if restored.returncode != 0:
            raise RuntimeError(f"restored regression suite failed for {spec.mutation_id}")
        results.append(MutationResult(
            spec.mutation_id, spec.target, spec.counterexample_id, spec.purpose, anchor_offset, count, _sha(pristine), _sha(mutated), _sha(target.read_bytes()),
            command, _sha("\0".join(command).encode("utf-8")), changed.returncode, restored.returncode, changed_duration, restored_duration,
            _sha(changed.stdout), _sha(changed.stderr), _sha(restored.stdout), _sha(restored.stderr),
        ))
    return tuple(results)


def mutation_payload(results: Sequence[MutationResult]) -> bytes:
    import json
    return json.dumps({"schema": "e56-mutation-results-v1", "results": [asdict(item) for item in results]}, sort_keys=True, separators=(",", ":")).encode("utf-8")
