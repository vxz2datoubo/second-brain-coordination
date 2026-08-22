"""Fail closed when downloaded E56 canonical evidence differs by one byte."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from e56_authority.provider import CONTRACT_PATH, DEFAULT_PROVIDER_CONTRACT  # noqa: E402


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def compare(root: Path) -> dict[str, object]:
    canonical = sorted(root.glob("canonical-*/canonical.json"))
    environment = sorted(root.glob("environment-*/environment.json"))
    mutation = sorted(root.glob("environment-*/mutation-results.json"))
    job_evidence = sorted(root.glob("environment-*/job-evidence.json"))
    expected = dict(DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings)
    expected_canonical = {name for name in expected if name.startswith("canonical-")}
    expected_environment = {name for name in expected if name.startswith("environment-")}
    if len(canonical) != 6 or len(environment) != 6 or len(mutation) != 6 or len(job_evidence) != 6:
        raise RuntimeError("expected exactly six canonical, six environment and six mutation-result inner files")
    if {path.parent.name for path in canonical} != expected_canonical or {path.parent.name for path in environment} != expected_environment:
        raise RuntimeError("downloaded matrix artifact names do not match the fixed Provider contract")
    canonical_bytes = [path.read_bytes() for path in canonical]
    if len(set(canonical_bytes)) != 1:
        raise RuntimeError("canonical Provider inner files differ byte-for-byte")
    environment_entries = []
    for env_path, mutation_path, job_path in zip(environment, mutation, job_evidence):
        if env_path.parent != mutation_path.parent or env_path.parent != job_path.parent:
            raise RuntimeError("environment evidence inner files are not co-located")
        payload = json.loads(env_path.read_text(encoding="utf-8"))
        mutation_digest = digest(mutation_path.read_bytes())
        if payload.get("mutation_result_sha256") != mutation_digest:
            raise RuntimeError("environment payload does not bind its mutation result payload")
        evidence_bytes = job_path.read_bytes()
        evidence = json.loads(evidence_bytes.decode("utf-8"))
        expected_job_name = expected[env_path.parent.name]
        _prefix, expected_runtime, expected_seed = expected_job_name.split(" / ")
        expected_version = expected_runtime.removeprefix("py")
        expected_seed = expected_seed.removeprefix("seed=")
        if (
            digest(evidence_bytes) != payload.get("job_evidence_sha256")
            or evidence.get("schema") != "e56-provider-job-evidence-v1"
            or evidence.get("job_name") != expected_job_name
            or evidence.get("contract_sha256") != digest(CONTRACT_PATH.read_bytes())
            or not isinstance(evidence.get("run_id"), int)
            or evidence["run_id"] <= 0
            or payload.get("python_version") != expected_version
            or payload.get("hash_seed") != expected_seed
        ):
            raise RuntimeError("environment job evidence is not bound to its fixed matrix slot")
        environment_entries.append({"environment": env_path.parent.name, "environment_sha256": digest(env_path.read_bytes()), "mutation_sha256": mutation_digest, "job_evidence_sha256": digest(evidence_bytes), "job_name": expected_job_name})
    return {
        "schema": "e56-provider-compare-v1",
        "canonical_sha256": digest(canonical_bytes[0]),
        "canonical_count": len(canonical),
        "environment_bindings": environment_entries,
        "compare_digest": digest(json.dumps(environment_entries, sort_keys=True, separators=(",", ":")).encode("utf-8")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    Path(args.output).write_bytes(json.dumps(compare(Path(args.root)), sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
