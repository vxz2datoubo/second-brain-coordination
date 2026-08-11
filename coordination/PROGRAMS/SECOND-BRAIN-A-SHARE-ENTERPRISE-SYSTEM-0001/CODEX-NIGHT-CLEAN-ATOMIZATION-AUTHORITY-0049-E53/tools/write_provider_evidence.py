"""Write deterministic canonical evidence and separate environment evidence for E53 CI."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess
import sys


PROGRAM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAM / "src"))

from e53_authority import AtomFactory, CanonicalPacketFactory, RelationFactory, SourceEvidence, VerifiedAtomRegistry, build_ledger  # noqa: E402
from e53_authority.corpus import corpus_digest  # noqa: E402


def canonical_fixture() -> dict[str, object]:
    data = b"alpha\nbeta\n[[0:6->6:11]]\n"
    evidence = SourceEvidence.from_bytes(data, source_id="fixture:provider", format_name="text")
    ledger = build_ledger(evidence)
    factory = AtomFactory(evidence, ledger)
    alpha, beta = factory.issue(0, 6), factory.issue(6, 11)
    registry = VerifiedAtomRegistry(factory)
    registry.register(alpha)
    registry.register(beta)
    relations = RelationFactory(registry)
    relation = relations.issue_explicit(11, len(data))
    packet = CanonicalPacketFactory(evidence, ledger, registry, relations).issue(
        atoms=[alpha, beta], relations=[relation], unknowns=["fixture_only"], validation={"source_bound": True}
    )
    return {
        "schema_version": "e53-provider-canonical.1",
        "task_id": "CODEX-NIGHT-CLEAN-SOURCE-BOUND-ATOMIZATION-AUTHORITY-ADVERSARIAL-PROVIDER-AND-RECEIPT-CLOSURE-0049-E53",
        "corpus_sha256": corpus_digest(),
        "packet_id": packet.packet_id,
        "packet_sha256": sha256(packet.canonical_json).hexdigest(),
        "coverage_sha256": ledger.coverage_manifest["coverage_sha256"],
        "atom_ids": list(packet.atom_ids),
        "relation_ids": list(packet.relation_ids),
    }


def git_head(repository: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True, encoding="utf-8").strip()


def write(output: Path, expected_head: str | None) -> tuple[Path, Path]:
    repository = PROGRAM.parents[3]
    actual_head = git_head(repository)
    if expected_head and actual_head != expected_head:
        raise SystemExit(f"checked out head mismatch: expected {expected_head}, got {actual_head}")
    output.mkdir(parents=True, exist_ok=True)
    canonical_path = output / "canonical-evidence.json"
    environment_path = output / "environment-evidence.json"
    canonical_path.write_bytes(json.dumps(canonical_fixture(), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n")
    environment = {
        "schema_version": "e53-provider-environment.1",
        "head": actual_head,
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "python_hash_seed": __import__("os").environ.get("PYTHONHASHSEED", ""),
        "platform": platform.platform(),
    }
    environment_path.write_bytes(json.dumps(environment, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n")
    return canonical_path, environment_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-head")
    args = parser.parse_args()
    canonical, environment = write(args.output, args.expected_head)
    print(json.dumps({"canonical_sha256": sha256(canonical.read_bytes()).hexdigest(), "environment_sha256": sha256(environment.read_bytes()).hexdigest()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
