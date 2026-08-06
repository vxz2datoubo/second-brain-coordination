from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile

from e56_authority.authority import AuthorityError
from e56_authority.mutations import MUTATION_SPECS
from e56_authority.provider import CONTRACT_PATH, DEFAULT_PROVIDER_CONTRACT, build_canonical_evaluation, canonical_artifact_bytes, load_provider_contract, verify_provider_snapshot


ROOT = Path(__file__).resolve().parents[1]


def load_tool(name: str):
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"e56_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


COMPARE = load_tool("compare_provider_artifacts")
VERIFY = load_tool("verify_provider_run")
COLLECT = load_tool("collect_provider_snapshot")


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


class ProviderTests(unittest.TestCase):
    def test_canonical_contains_executed_fixture_outcomes(self):
        payload = build_canonical_evaluation(ROOT / "src" / "e56_authority", test_result={"test_count": 1, "exit_code": 0}, mutation_summary=[])
        self.assertEqual(payload["schema"], "e56-canonical-evaluation-v1")
        self.assertGreaterEqual(len(payload["fixture_outcomes"]), 4)
        self.assertIn("graph_evaluation_digest", payload)
        self.assertIn("production_source_hashes", payload)

    def test_canonical_bytes_are_deterministic_for_same_executed_inputs(self):
        first = build_canonical_evaluation(ROOT / "src" / "e56_authority", test_result={"test_count": 1, "exit_code": 0}, mutation_summary=[])
        second = build_canonical_evaluation(ROOT / "src" / "e56_authority", test_result={"test_count": 1, "exit_code": 0}, mutation_summary=[])
        self.assertEqual(canonical_artifact_bytes(first), canonical_artifact_bytes(second))

    def test_canonical_excludes_executor_command_details(self):
        first = build_canonical_evaluation(ROOT / "src" / "e56_authority", test_result={"test_count": 1, "exit_code": 0, "command": ["/py311/python"]}, mutation_summary=[])
        second = build_canonical_evaluation(ROOT / "src" / "e56_authority", test_result={"test_count": 1, "exit_code": 0, "command": ["/py313/python"]}, mutation_summary=[])
        self.assertEqual(canonical_artifact_bytes(first), canonical_artifact_bytes(second))

    def test_versioned_provider_contract_is_loaded_from_its_own_file(self):
        loaded = load_provider_contract(CONTRACT_PATH)
        self.assertEqual(loaded, DEFAULT_PROVIDER_CONTRACT)
        self.assertEqual(len(loaded.matrix_artifact_bindings), 13)

    def snapshot(self):
        run_id = 7001
        jobs = [{"id": number + 1, "name": name, "conclusion": "success", "head_sha": "a" * 40, "run_id": run_id} for number, name in enumerate(DEFAULT_PROVIDER_CONTRACT.matrix_job_names + (DEFAULT_PROVIDER_CONTRACT.compare_job_name,))]
        job_ids = {item["name"]: item["id"] for item in jobs}
        artifacts = [{"id": 100 + number, "name": artifact_name, "job_name": job_name, "job_id": job_ids[job_name], "run_id": run_id} for number, (artifact_name, job_name) in enumerate(DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings)]
        return {"workflow": DEFAULT_PROVIDER_CONTRACT.workflow, "branch": DEFAULT_PROVIDER_CONTRACT.branch, "head_sha": "a" * 40, "run_id": run_id, "jobs": jobs, "artifacts": artifacts}

    def test_provider_snapshot_rejects_extra_job(self):
        snapshot = self.snapshot()
        snapshot["jobs"].append({"id": 88, "name": "unexpected", "conclusion": "success", "head_sha": "a" * 40, "run_id": snapshot["run_id"]})
        with self.assertRaises(AuthorityError):
            verify_provider_snapshot(snapshot, DEFAULT_PROVIDER_CONTRACT, expected_head="a" * 40)

    def test_provider_snapshot_rejects_duplicate_job_id(self):
        snapshot = self.snapshot()
        snapshot["jobs"][1]["id"] = snapshot["jobs"][0]["id"]
        with self.assertRaises(AuthorityError):
            verify_provider_snapshot(snapshot, DEFAULT_PROVIDER_CONTRACT, expected_head="a" * 40)

    def test_provider_snapshot_rejects_unexpected_artifact_kind(self):
        snapshot = self.snapshot()
        snapshot["artifacts"][-1]["name"] = "unexpected-artifact"
        with self.assertRaises(AuthorityError):
            verify_provider_snapshot(snapshot, DEFAULT_PROVIDER_CONTRACT, expected_head="a" * 40)

    def test_provider_snapshot_rejects_duplicate_artifact_id(self):
        snapshot = self.snapshot()
        snapshot["artifacts"][1]["id"] = snapshot["artifacts"][0]["id"]
        with self.assertRaises(AuthorityError):
            verify_provider_snapshot(snapshot, DEFAULT_PROVIDER_CONTRACT, expected_head="a" * 40)

    def test_provider_snapshot_rejects_compare_artifact_job_collision(self):
        snapshot = self.snapshot()
        snapshot["artifacts"][-1]["job_id"] = 1
        with self.assertRaises(AuthorityError):
            verify_provider_snapshot(snapshot, DEFAULT_PROVIDER_CONTRACT, expected_head="a" * 40)

    def test_provider_snapshot_rejects_artifact_name_to_job_substitution(self):
        snapshot = self.snapshot()
        snapshot["artifacts"][0]["job_name"] = DEFAULT_PROVIDER_CONTRACT.compare_job_name
        with self.assertRaises(AuthorityError):
            verify_provider_snapshot(snapshot, DEFAULT_PROVIDER_CONTRACT, expected_head="a" * 40)

    def test_public_collector_builds_exact_logical_job_artifact_binding(self):
        snapshot = self.snapshot()
        run = {"id": snapshot["run_id"], "head_sha": snapshot["head_sha"], "head_branch": DEFAULT_PROVIDER_CONTRACT.branch, "event": "pull_request", "name": "codex-e56-canonical-authority-closure"}
        archives = {item["id"]: {"archive_file": f"artifact-{item['id']}.zip", "archive_sha256": "e" * 64} for item in snapshot["artifacts"]}
        rebuilt = COLLECT.build_snapshot(DEFAULT_PROVIDER_CONTRACT, run=run, jobs=snapshot["jobs"], artifacts=snapshot["artifacts"], archive_records=archives, expected_head="a" * 40)
        self.assertEqual(rebuilt["artifacts"], [
            {"id": item["id"], "name": item["name"], "job_name": item["job_name"], "job_id": item["job_id"], "run_id": item["run_id"], "archive_file": f"artifact-{item['id']}.zip", "archive_sha256": "e" * 64}
            for item in snapshot["artifacts"]
        ])


class ToolTests(unittest.TestCase):
    def test_compare_rejects_divergent_canonical_payloads(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(6):
                canonical = root / DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2][0]
                environment = root / DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2 + 1][0]
                canonical.mkdir()
                environment.mkdir()
                canonical.write_text if False else None
                (canonical / "canonical.json").write_bytes(b"same" if index != 5 else b"different")
                mutation = b'{"results":[]}'
                (environment / "mutation-results.json").write_bytes(mutation)
                expected_job = DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2 + 1][1]
                _prefix, runtime, seed = expected_job.split(" / ")
                job = json.dumps({"schema": "e56-provider-job-evidence-v1", "head_sha": "a" * 40, "job_name": expected_job, "run_id": 7001, "run_attempt": 1, "contract_sha256": digest(CONTRACT_PATH.read_bytes())}, sort_keys=True, separators=(",", ":")).encode("utf-8")
                (environment / "job-evidence.json").write_bytes(job)
                (environment / "environment.json").write_text(json.dumps({"mutation_result_sha256": digest(mutation), "job_evidence_sha256": digest(job), "python_version": runtime.removeprefix("py"), "hash_seed": seed.removeprefix("seed=")}), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                COMPARE.compare(root)

    def test_compare_accepts_identical_canonical_payloads(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(6):
                canonical = root / DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2][0]
                environment = root / DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2 + 1][0]
                canonical.mkdir(); environment.mkdir()
                (canonical / "canonical.json").write_bytes(b"same")
                mutation = b'{"results":[]}'
                (environment / "mutation-results.json").write_bytes(mutation)
                expected_job = DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2 + 1][1]
                _prefix, runtime, seed = expected_job.split(" / ")
                job = json.dumps({"schema": "e56-provider-job-evidence-v1", "head_sha": "a" * 40, "job_name": expected_job, "run_id": 7001, "run_attempt": 1, "contract_sha256": digest(CONTRACT_PATH.read_bytes())}, sort_keys=True, separators=(",", ":")).encode("utf-8")
                (environment / "job-evidence.json").write_bytes(job)
                (environment / "environment.json").write_text(json.dumps({"mutation_result_sha256": digest(mutation), "job_evidence_sha256": digest(job), "python_version": runtime.removeprefix("py"), "hash_seed": seed.removeprefix("seed=")}), encoding="utf-8")
            self.assertEqual(COMPARE.compare(root)["canonical_count"], 6)

    def test_compare_rejects_unbound_environment_mutation(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(6):
                canonical = root / DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2][0]
                environment = root / DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2 + 1][0]
                canonical.mkdir(); environment.mkdir()
                (canonical / "canonical.json").write_bytes(b"same")
                mutation = b'{"results":[]}'
                (environment / "mutation-results.json").write_bytes(mutation)
                expected_job = DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2 + 1][1]
                _prefix, runtime, seed = expected_job.split(" / ")
                job = json.dumps({"schema": "e56-provider-job-evidence-v1", "head_sha": "a" * 40, "job_name": expected_job, "run_id": 7001, "run_attempt": 1, "contract_sha256": digest(CONTRACT_PATH.read_bytes())}, sort_keys=True, separators=(",", ":")).encode("utf-8")
                (environment / "job-evidence.json").write_bytes(job)
                (environment / "environment.json").write_text(json.dumps({"mutation_result_sha256": digest(mutation) if index != 2 else "0" * 64, "job_evidence_sha256": digest(job), "python_version": runtime.removeprefix("py"), "hash_seed": seed.removeprefix("seed=")}), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                COMPARE.compare(root)

    def test_compare_rejects_wrong_job_evidence(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(6):
                canonical = root / DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2][0]
                environment = root / DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2 + 1][0]
                canonical.mkdir(); environment.mkdir()
                (canonical / "canonical.json").write_bytes(b"same")
                mutation = b'{"results":[]}'
                (environment / "mutation-results.json").write_bytes(mutation)
                job_name = "forged-job" if index == 3 else DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2 + 1][1]
                expected_job = DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2 + 1][1]
                _prefix, runtime, seed = expected_job.split(" / ")
                job = json.dumps({"schema": "e56-provider-job-evidence-v1", "head_sha": "a" * 40, "job_name": job_name, "run_id": 7001, "run_attempt": 1, "contract_sha256": digest(CONTRACT_PATH.read_bytes())}, sort_keys=True, separators=(",", ":")).encode("utf-8")
                (environment / "job-evidence.json").write_bytes(job)
                (environment / "environment.json").write_text(json.dumps({"mutation_result_sha256": digest(mutation), "job_evidence_sha256": digest(job), "python_version": runtime.removeprefix("py"), "hash_seed": seed.removeprefix("seed=")}), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                COMPARE.compare(root)

    def test_compare_rejects_wrong_runtime_identity(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(6):
                canonical = root / DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2][0]
                environment = root / DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2 + 1][0]
                canonical.mkdir(); environment.mkdir()
                (canonical / "canonical.json").write_bytes(b"same")
                mutation = b'{"results":[]}'
                (environment / "mutation-results.json").write_bytes(mutation)
                expected_job = DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings[index * 2 + 1][1]
                _prefix, runtime, seed = expected_job.split(" / ")
                job = json.dumps({"schema": "e56-provider-job-evidence-v1", "head_sha": "a" * 40, "job_name": expected_job, "run_id": 7001, "run_attempt": 1, "contract_sha256": digest(CONTRACT_PATH.read_bytes())}, sort_keys=True, separators=(",", ":")).encode("utf-8")
                (environment / "job-evidence.json").write_bytes(job)
                (environment / "environment.json").write_text(json.dumps({"mutation_result_sha256": digest(mutation), "job_evidence_sha256": digest(job), "python_version": "0.0" if index == 4 else runtime.removeprefix("py"), "hash_seed": seed.removeprefix("seed=")}), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                COMPARE.compare(root)

    def _archive_snapshot(self, root: Path):
        mutation = json.dumps({"schema": "e56-mutation-results-v1", "results": [{"mutation_id": item.mutation_id, "target": item.target, "counterexample_id": item.counterexample_id, "anchor_offset": 1, "replacement_count": 1, "mutated_exit_code": 1, "restored_exit_code": 0, "pristine_sha256": "b" * 64, "mutated_sha256": "c" * 64, "restored_sha256": "b" * 64, "command_sha256": "d" * 64, "mutated_stdout_sha256": "e" * 64, "mutated_stderr_sha256": "f" * 64, "restored_stdout_sha256": "1" * 64, "restored_stderr_sha256": "2" * 64} for item in MUTATION_SPECS]}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        run_id = 7001
        jobs = [{"id": number + 1, "name": name, "conclusion": "success", "head_sha": "a" * 40, "run_id": run_id} for number, name in enumerate(DEFAULT_PROVIDER_CONTRACT.matrix_job_names + (DEFAULT_PROVIDER_CONTRACT.compare_job_name,))]
        job_ids = {item["name"]: item["id"] for item in jobs}
        artifacts = []
        for number, (name, job_name) in enumerate(DEFAULT_PROVIDER_CONTRACT.matrix_artifact_bindings):
            archive = root / f"{number}.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                if name.startswith("canonical-"):
                    bundle.writestr("canonical.json", b'{"canonical":true}')
                elif name.startswith("environment-"):
                    job_evidence = json.dumps({"schema": "e56-provider-job-evidence-v1", "head_sha": "a" * 40, "job_name": job_name, "run_id": run_id, "run_attempt": 1, "contract_sha256": digest(CONTRACT_PATH.read_bytes())}, sort_keys=True, separators=(",", ":")).encode("utf-8")
                    environment = json.dumps({"mutation_result_sha256": digest(mutation), "job_evidence_sha256": digest(job_evidence)}, sort_keys=True, separators=(",", ":")).encode("utf-8")
                    bundle.writestr("environment.json", environment)
                    bundle.writestr("mutation-results.json", mutation)
                    bundle.writestr("job-evidence.json", job_evidence)
                else:
                    bundle.writestr("provider-compare.json", b'{"compare":true}')
            artifacts.append({"id": 100 + number, "name": name, "job_name": job_name, "job_id": job_ids[job_name], "run_id": run_id, "archive_file": archive.name, "archive_sha256": digest(archive.read_bytes())})
        return {"workflow": DEFAULT_PROVIDER_CONTRACT.workflow, "branch": DEFAULT_PROVIDER_CONTRACT.branch, "head_sha": "a" * 40, "run_id": run_id, "jobs": jobs, "artifacts": artifacts}

    def test_verifier_rejects_tampered_mutation_payload(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = self._archive_snapshot(root)
            artifact = snapshot["artifacts"][1]
            archive = root / artifact["archive_file"]
            original = json.dumps({"schema": "e56-mutation-results-v1", "results": [{"mutation_id": item.mutation_id, "target": item.target, "counterexample_id": item.counterexample_id, "anchor_offset": 1, "replacement_count": 1, "mutated_exit_code": 1, "restored_exit_code": 0, "pristine_sha256": "b" * 64, "mutated_sha256": "c" * 64, "restored_sha256": "b" * 64, "command_sha256": "d" * 64, "mutated_stdout_sha256": "e" * 64, "mutated_stderr_sha256": "f" * 64, "restored_stdout_sha256": "1" * 64, "restored_stderr_sha256": "2" * 64} for item in MUTATION_SPECS]}, sort_keys=True, separators=(",", ":")).encode("utf-8")
            artifact_name = artifact["name"]
            job_evidence = json.dumps({"schema": "e56-provider-job-evidence-v1", "head_sha": "a" * 40, "job_name": artifact["job_name"], "run_id": snapshot["run_id"], "run_attempt": 1, "contract_sha256": digest(CONTRACT_PATH.read_bytes())}, sort_keys=True, separators=(",", ":")).encode("utf-8")
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("environment.json", json.dumps({"mutation_result_sha256": digest(original), "job_evidence_sha256": digest(job_evidence)}).encode("utf-8"))
                bundle.writestr("mutation-results.json", original + b" ")
                bundle.writestr("job-evidence.json", job_evidence)
            artifact["archive_sha256"] = digest(archive.read_bytes())
            with self.assertRaises(AuthorityError):
                VERIFY.verify_archives(snapshot, root, expected_head="a" * 40)

    def test_verifier_rejects_extra_artifact(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = self._archive_snapshot(root)
            existing = dict(snapshot["artifacts"][-1])
            existing["id"] = 999
            snapshot["artifacts"].append(existing)
            with self.assertRaises(AuthorityError):
                VERIFY.verify_archives(snapshot, root, expected_head="a" * 40)

    def test_verifier_accepts_complete_bound_archives(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = self._archive_snapshot(root)
            result = VERIFY.verify_archives(snapshot, root, expected_head="a" * 40)
            self.assertEqual(result["contract"]["artifact_count"], 13)
            self.assertEqual(len(result["bound_artifacts"]), 13)


if __name__ == "__main__":
    unittest.main()
