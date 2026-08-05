"""Build deterministic multi-format Provider evidence from synthetic fixtures."""

from __future__ import annotations

from hashlib import sha256
import platform
import sys
from typing import Mapping, Sequence

from .authority import AtomFactory, CanonicalPacketFactory, RelationFactory, SourceEvidence, SpanOwner, VerifiedAtomRegistry, build_ledger, canonical_bytes


FIXTURES: tuple[tuple[str, str, bytes], ...] = (
    ("json", "synthetic:e54:json", b'{"claim":"alpha","support":"beta"}'),
    ("jsonl", "synthetic:e54:jsonl", b'{"claim":"gamma"}\n{"support":"delta"}\n'),
    ("markdown", "synthetic:e54:markdown", b"# heading\n> epsilon\n- zeta\n`code` is prose\n"),
)


def _fixture_graph(format_name: str, source_id: str, payload: bytes) -> dict[str, object]:
    evidence = SourceEvidence.from_bytes(payload, source_id=source_id, format_name=format_name)
    ledger = build_ledger(evidence)
    factory = AtomFactory(evidence, ledger)
    atoms = [factory.issue(span.start, span.end) for span in ledger.spans if span.owner is SpanOwner.ATOM_CANDIDATE]
    registry = VerifiedAtomRegistry(factory)
    for atom in atoms:
        registry.register(atom)
    relations = RelationFactory(registry)
    issued_relations = []
    if len(atoms) >= 2:
        issued_relations.append(relations.issue(atoms[0].atom_id, atoms[1].atom_id, start=0, end=1))
    packets = CanonicalPacketFactory(evidence, ledger, registry, relations)
    packet = packets.issue(atoms=atoms, relations=issued_relations, unknowns=["synthetic_fixture_only"])
    if not packets.verify(packet):
        raise RuntimeError("synthetic fixture packet did not verify")
    return {
        "format": format_name,
        "source_sha256": evidence.source_sha256,
        "ledger_coverage_sha256": ledger.coverage_manifest["coverage_sha256"],
        "atom_ids": list(packet.atom_ids),
        "relation_ids": list(packet.relation_ids),
        "packet_id": packet.packet_id,
        "canonical_json_sha256": sha256(packet.canonical_json).hexdigest(),
    }


def build_canonical_evidence(*, head_sha: str, test_count: int, mutation_ids: Sequence[str]) -> bytes:
    """Return a seed/runtime-independent artifact for one exact code head."""
    body = {
        "schema_version": "e54.provider.canonical.1",
        "head_sha": head_sha,
        "test_count": test_count,
        "mutation_count": len(mutation_ids),
        "mutation_ids": sorted(mutation_ids),
        "fixtures": [_fixture_graph(*fixture) for fixture in FIXTURES],
    }
    return canonical_bytes(body)


def build_environment_evidence(*, head_sha: str, test_count: int, mutation_ids: Sequence[str], command: str, stdout: bytes, stderr: bytes, canonical_artifact: bytes, hash_seed: str) -> Mapping[str, object]:
    return {
        "schema_version": "e54.provider.environment.1",
        "head_sha": head_sha,
        "test_count": test_count,
        "mutation_count": len(mutation_ids),
        "mutation_ids": sorted(mutation_ids),
        "command_sha256": sha256(command.encode("utf-8")).hexdigest(),
        "stdout_sha256": sha256(stdout).hexdigest(),
        "stderr_sha256": sha256(stderr).hexdigest(),
        "canonical_artifact_sha256": sha256(canonical_artifact).hexdigest(),
        "python_version": ".".join(map(str, sys.version_info[:2])),
        "python_implementation": platform.python_implementation(),
        "hash_seed": hash_seed,
    }
