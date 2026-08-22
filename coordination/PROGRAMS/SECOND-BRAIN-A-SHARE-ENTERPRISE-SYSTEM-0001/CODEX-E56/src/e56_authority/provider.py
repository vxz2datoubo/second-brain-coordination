"""Deterministic E56 evaluation result and independent Provider contract checks."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .authority import (
    AdmissionPolicy,
    AtomFactory,
    AuthorityError,
    EvidenceFactory,
    PacketFactory,
    RelationFactory,
    SourceAdmission,
    build_ledger,
    canonical_bytes,
    stable_digest,
)


@dataclass(frozen=True, slots=True)
class ProviderContract:
    schema: str
    workflow: str
    branch: str
    python_versions: tuple[str, ...]
    seeds: tuple[str, ...]
    matrix_job_prefix: str
    compare_job_name: str
    artifact_count: int

    @property
    def matrix_job_names(self) -> tuple[str, ...]:
        return tuple(f"{self.matrix_job_prefix} / py{version} / seed={seed}" for version in self.python_versions for seed in self.seeds)

    @property
    def matrix_artifact_bindings(self) -> tuple[tuple[str, str], ...]:
        """Expected artifact name to logical job name bindings, in matrix order."""

        bindings: list[tuple[str, str]] = []
        for version in self.python_versions:
            for seed in self.seeds:
                job_name = f"{self.matrix_job_prefix} / py{version} / seed={seed}"
                suffix = f"py{version}-seed{seed}"
                bindings.extend(((f"canonical-{suffix}", job_name), (f"environment-{suffix}", job_name)))
        bindings.append(("provider-compare", self.compare_job_name))
        return tuple(bindings)


_TASK_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = _TASK_ROOT / "PROVIDER-CONTRACT.json"


def load_provider_contract(path: Path = CONTRACT_PATH) -> ProviderContract:
    """Load the independently versioned, public-safe Provider contract strictly."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        matrix = payload["matrix"]
        contract = ProviderContract(
            schema=str(payload["schema"]),
            workflow=str(payload["workflow"]),
            branch=str(payload["branch"]),
            python_versions=tuple(str(item) for item in matrix["python_versions"]),
            seeds=tuple(str(item) for item in matrix["seeds"]),
            matrix_job_prefix=str(payload["matrix_job_prefix"]),
            compare_job_name=str(payload["compare_job_name"]),
            artifact_count=int(payload["artifact_count"]),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AuthorityError("Provider contract is malformed") from exc
    if (
        contract.schema != "e56-provider-contract-v1"
        or contract.workflow != ".github/workflows/codex-e56-canonical-authority-closure.yml"
        or contract.python_versions != ("3.11", "3.13")
        or contract.seeds != ("0", "1", "777")
        or contract.matrix_job_prefix != "authority"
        or contract.compare_job_name != "provider-compare"
        or contract.artifact_count != 13
        or len(contract.matrix_artifact_bindings) != contract.artifact_count
    ):
        raise AuthorityError("Provider contract differs from the E56 fixed authority shape")
    return contract


DEFAULT_PROVIDER_CONTRACT = load_provider_contract()


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def source_hashes(package_root: Path) -> tuple[tuple[str, str], ...]:
    return tuple((path.relative_to(package_root).as_posix(), digest(path.read_bytes())) for path in sorted(package_root.glob("*.py")))


def _fixture_outcomes() -> tuple[Mapping[str, object], ...]:
    """Execute ground-truth E56 authority paths, not declarations about them."""

    admission = SourceAdmission(AdmissionPolicy())
    source = admission.admit(b'{"first":"alpha\\nbeta","second":"gamma"}', source_id="fixture/e56.json", format_name="json")
    ledger = build_ledger(admission, source)
    atoms = AtomFactory(ledger)
    evidence = EvidenceFactory(ledger)
    packet = PacketFactory(evidence)
    spans = ledger.semantic_spans
    first_atom, second_atom = atoms.issue(spans[0].span_id), atoms.issue(spans[1].span_id)
    first_evidence, second_evidence = evidence.issue(spans[0].span_id), evidence.issue(spans[1].span_id)
    relations = RelationFactory(atoms, evidence)
    relation = relations.issue(first_atom, second_atom, relation_type="supports", evidence=first_evidence)
    validation = packet.validation(first_evidence, rule_id="fixture.span_bound", outcome="PASS")
    unknown = packet.unknown(second_evidence, reason="fixture_has_no_external_resolution")
    negatives: list[Mapping[str, object]] = []
    for fixture_id, operation in (
        ("direct_source_constructor", lambda: build_ledger(admission, type(source)(b"text", "fake", "text", digest(b"text"), admission.policy_identity))),
        ("caller_authored_evidence", lambda: evidence.issue(first_evidence.span_id, statement="unrelated prose")),
        ("generic_packet_payload", lambda: packet._issue(validation.kind, first_evidence, {"value": "forged"})),
    ):
        try:
            operation()
        except AuthorityError:
            negatives.append({"fixture_id": fixture_id, "expected": "REJECT", "observed": "REJECT"})
        else:
            negatives.append({"fixture_id": fixture_id, "expected": "REJECT", "observed": "ACCEPT"})
    graph = {
        "atoms": [first_atom.atom_id, second_atom.atom_id],
        "evidence": [first_evidence.record_id, second_evidence.record_id],
        "packet": [validation.record_id, unknown.record_id],
        "relation": relation.relation_id,
        "ownership_digest": ledger.manifest_sha256,
    }
    return (
        {
            "fixture_id": "json_escaped_value_and_graph",
            "expected": "ACCEPT",
            "observed": "ACCEPT" if all((ledger.verify(), atoms.verify(first_atom), atoms.verify(second_atom), evidence.verify(first_evidence), packet.verify(validation), packet.verify(unknown), relations.verify(relation))) else "REJECT",
            "graph_digest": stable_digest(graph),
            "semantic_span_count": len(spans),
        },
        *negatives,
    )


def _canonical_test_result(value: Mapping[str, object]) -> Mapping[str, object]:
    """Keep executable outcome in canonical evidence; keep executor details outside it."""

    test_count = value.get("test_count")
    exit_code = value.get("exit_code")
    if not isinstance(test_count, int) or isinstance(test_count, bool) or test_count < 0:
        raise AuthorityError("canonical test count is invalid")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        raise AuthorityError("canonical test exit code is invalid")
    return {"suite_id": "e56-product-suite-v1", "test_count": test_count, "exit_code": exit_code}


def build_canonical_evaluation(
    package_root: Path,
    *,
    test_result: Mapping[str, object],
    mutation_summary: Sequence[Mapping[str, object]],
) -> Mapping[str, object]:
    """Build the canonical payload from executed fixtures and actual results."""

    fixture_outcomes = _fixture_outcomes()
    normalized_test_result = _canonical_test_result(test_result)
    if any(item["observed"] != item["expected"] for item in fixture_outcomes):
        raise AuthorityError("an adversarial fixture did not produce its expected authority outcome")
    ordered_mutations = tuple(sorted((dict(item) for item in mutation_summary), key=lambda item: str(item["mutation_id"])))
    result = {
        "schema": "e56-canonical-evaluation-v1",
        "policy_identity": AdmissionPolicy().identity,
        "production_source_hashes": [{"path": path, "sha256": value} for path, value in source_hashes(package_root)],
        "fixture_outcomes": fixture_outcomes,
        "fixture_digest": stable_digest(fixture_outcomes),
        "test_result_digest": stable_digest(normalized_test_result),
        "mutation_summary": ordered_mutations,
        "mutation_summary_digest": stable_digest(ordered_mutations),
        "graph_evaluation_digest": stable_digest([item.get("graph_digest", "") for item in fixture_outcomes]),
    }
    return result


def canonical_artifact_bytes(payload: Mapping[str, object]) -> bytes:
    return canonical_bytes(payload)


def verify_provider_snapshot(snapshot: Mapping[str, object], contract: ProviderContract, *, expected_head: str) -> Mapping[str, object]:
    """Validate a caller-supplied public Provider snapshot against fixed contract."""

    if snapshot.get("workflow") != contract.workflow or snapshot.get("branch") != contract.branch or snapshot.get("head_sha") != expected_head:
        raise AuthorityError("Provider snapshot route identity differs from the fixed contract")
    if not isinstance(snapshot.get("run_id"), int) or snapshot["run_id"] <= 0:
        raise AuthorityError("Provider snapshot lacks a positive workflow run identifier")
    jobs = snapshot.get("jobs")
    artifacts = snapshot.get("artifacts")
    if not isinstance(jobs, list) or not isinstance(artifacts, list):
        raise AuthorityError("Provider snapshot lacks jobs or artifacts")
    expected_jobs = set(contract.matrix_job_names) | {contract.compare_job_name}
    observed_jobs = {str(item.get("name")) for item in jobs if isinstance(item, Mapping)}
    job_ids = [item.get("id") for item in jobs if isinstance(item, Mapping)]
    if observed_jobs != expected_jobs or len(jobs) != 7 or len(job_ids) != 7 or len(set(job_ids)) != 7:
        raise AuthorityError("Provider snapshot must contain exactly six matrix jobs and one compare job")
    if any(item.get("conclusion") != "success" or item.get("head_sha") != expected_head or item.get("run_id") != snapshot["run_id"] for item in jobs if isinstance(item, Mapping)):
        raise AuthorityError("Provider job conclusion or checkout head is invalid")
    names = [str(item.get("name")) for item in artifacts if isinstance(item, Mapping)]
    ids = [item.get("id") for item in artifacts if isinstance(item, Mapping)]
    if len(artifacts) != contract.artifact_count or len(set(names)) != contract.artifact_count or len(set(ids)) != contract.artifact_count:
        raise AuthorityError("Provider artifact count or identity is invalid")
    canonical = [item for item in artifacts if str(item.get("name")).startswith("canonical-")]
    environment = [item for item in artifacts if str(item.get("name")).startswith("environment-")]
    compare = [item for item in artifacts if item.get("name") == "provider-compare"]
    if len(canonical) != 6 or len(environment) != 6 or len(compare) != 1:
        raise AuthorityError("Provider artifact kinds must be 6 canonical, 6 environment and 1 compare")
    jobs_by_name = {str(item["name"]): item for item in jobs if isinstance(item, Mapping)}
    observed_bindings = {str(item.get("name")): item for item in artifacts if isinstance(item, Mapping)}
    expected_bindings = dict(contract.matrix_artifact_bindings)
    if set(observed_bindings) != set(expected_bindings):
        raise AuthorityError("Provider artifact names differ from the fixed contract")
    for artifact_name, expected_job_name in expected_bindings.items():
        item = observed_bindings[artifact_name]
        job = jobs_by_name[expected_job_name]
        if item.get("job_name") != expected_job_name or item.get("job_id") != job["id"] or item.get("run_id") != snapshot["run_id"]:
            raise AuthorityError("Provider artifact does not bind to its exact run and logical job")
    return {"job_count": len(jobs), "artifact_count": len(artifacts), "canonical_artifact_ids": tuple(sorted(int(item["id"]) for item in canonical))}
