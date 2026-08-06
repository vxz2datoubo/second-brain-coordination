"""Independently validate downloaded Provider archive bytes and inner payloads."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from e56_authority.authority import AuthorityError  # noqa: E402
from e56_authority.mutations import MUTATION_SPECS  # noqa: E402
from e56_authority.provider import CONTRACT_PATH, DEFAULT_PROVIDER_CONTRACT, verify_provider_snapshot  # noqa: E402


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _archive_inner(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}


def verify_archives(snapshot: dict[str, object], archive_root: Path, *, expected_head: str) -> dict[str, object]:
    contract_result = verify_provider_snapshot(snapshot, DEFAULT_PROVIDER_CONTRACT, expected_head=expected_head)
    artifacts = snapshot["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != DEFAULT_PROVIDER_CONTRACT.artifact_count:
        raise AuthorityError("snapshot artifact count is invalid")
    canonical_payloads: list[bytes] = []
    mutation_ids = tuple(sorted(spec.mutation_id for spec in MUTATION_SPECS))
    bound: list[dict[str, object]] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise AuthorityError("artifact record is invalid")
        archive = archive_root / str(artifact["archive_file"])
        raw = archive.read_bytes()
        if digest(raw) != artifact.get("archive_sha256"):
            raise AuthorityError("archive digest differs from snapshot")
        inner = _archive_inner(archive)
        name = str(artifact["name"])
        if name.startswith("canonical-"):
            if set(inner) != {"canonical.json"}:
                raise AuthorityError("canonical archive inner files are invalid")
            canonical_payloads.append(inner["canonical.json"])
        elif name.startswith("environment-"):
            if set(inner) != {"environment.json", "mutation-results.json", "job-evidence.json"}:
                raise AuthorityError("environment archive inner files are invalid")
            environment = json.loads(inner["environment.json"].decode("utf-8"))
            mutation_payload = inner["mutation-results.json"]
            job_evidence = json.loads(inner["job-evidence.json"].decode("utf-8"))
            if digest(mutation_payload) != environment["mutation_result_sha256"]:
                raise AuthorityError("mutation results are not digest-bound to environment evidence")
            if digest(inner["job-evidence.json"]) != environment.get("job_evidence_sha256"):
                raise AuthorityError("environment payload does not bind job evidence")
            if (
                job_evidence.get("schema") != "e56-provider-job-evidence-v1"
                or job_evidence.get("head_sha") != expected_head
                or job_evidence.get("run_id") != snapshot.get("run_id")
                or job_evidence.get("job_name") != artifact.get("job_name")
                or job_evidence.get("contract_sha256") != digest(CONTRACT_PATH.read_bytes())
            ):
                raise AuthorityError("job evidence does not bind the archive to the exact authority contract")
            results = json.loads(mutation_payload.decode("utf-8"))["results"]
            observed_ids = tuple(sorted(str(item["mutation_id"]) for item in results))
            expected_by_id = {item.mutation_id: item for item in MUTATION_SPECS}
            required_hashes = ("pristine_sha256", "mutated_sha256", "restored_sha256", "command_sha256", "mutated_stdout_sha256", "mutated_stderr_sha256", "restored_stdout_sha256", "restored_stderr_sha256")
            if observed_ids != mutation_ids or any(
                item.get("target") != expected_by_id[str(item["mutation_id"])].target
                or item.get("counterexample_id") != expected_by_id[str(item["mutation_id"])].counterexample_id
                or not isinstance(item.get("anchor_offset"), int)
                or item.get("replacement_count") != 1
                or any(not isinstance(item.get(field), str) or len(item[field]) != 64 for field in required_hashes)
                or item.get("mutated_exit_code", 0) == 0
                or item.get("restored_exit_code") != 0
                or item.get("pristine_sha256") == item.get("mutated_sha256")
                or item.get("pristine_sha256") != item.get("restored_sha256")
                for item in results
            ):
                raise AuthorityError("mutation result payload fails exact kill/restoration contract")
        elif name == "provider-compare":
            if set(inner) != {"provider-compare.json"}:
                raise AuthorityError("compare archive inner files are invalid")
        else:
            raise AuthorityError("unexpected artifact name")
        bound.append({"artifact_id": artifact["id"], "name": name, "archive_sha256": digest(raw), "inner_names": tuple(sorted(inner))})
    if len(canonical_payloads) != 6 or len(set(canonical_payloads)) != 1:
        raise AuthorityError("six canonical payloads must be byte-identical")
    return {"contract": contract_result, "canonical_sha256": digest(canonical_payloads[0]), "bound_artifacts": bound}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--archive-root", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = verify_archives(json.loads(Path(args.snapshot).read_text(encoding="utf-8")), Path(args.archive_root), expected_head=args.expected_head)
    Path(args.output).write_bytes(json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
