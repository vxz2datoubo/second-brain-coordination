"""R147 regression: one malformed request must not strand valid batch peers."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve()
R147 = HERE.parents[1]
PLANE = R147.parent
S0E = PLANE / "S0E-EXPLICIT-INTAKE-ADAPTIVE-GATEWAY"
S0C = PLANE / "S0-SYNTHETIC"
sys.path[:0] = [
    str(R147 / "src"),
    str(S0E / "src"),
    str(S0C / "src"),
    str(S0E / "tests"),
    str(R147 / "tests"),
]

from r147_ingress import FreshAuthorityMaterialCache  # noqa: E402
from r147_transport_workflow import R147_ROOT, persist_push_batch  # noqa: E402
from test_r147_ingress import AuthorityHarness, request  # noqa: E402


def git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def configure(root: Path) -> None:
    git(root, "config", "user.email", "r147-malformed@example.invalid")
    git(root, "config", "user.name", "R147 Malformed Isolation")


def write_request(root: Path, attempt: str, payload: dict) -> str:
    relative = f"{R147_ROOT}/transport/requests/{attempt}.json"
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return relative


class R147MalformedBatchIsolationTests(unittest.TestCase):
    def test_malformed_request_is_isolated_and_valid_peers_persist(self):
        with tempfile.TemporaryDirectory() as directory:
            base_dir = Path(directory)
            remote = base_dir / "remote.git"
            seed = base_dir / "seed"
            worker = base_dir / "worker"
            verifier = base_dir / "verifier"
            runtime = base_dir / "runtime"
            runtime.mkdir()

            subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
            git(base_dir, "init", "-q", str(seed))
            configure(seed)
            (seed / "README.md").write_text("base\n", encoding="utf-8")
            git(seed, "add", "README.md")
            git(seed, "commit", "-q", "-m", "base")
            git(seed, "branch", "-M", "main")
            before = git(seed, "rev-parse", "HEAD")
            git(seed, "remote", "add", "origin", str(remote))
            git(seed, "push", "-q", "origin", "main")
            git(seed, "checkout", "-q", "-b", "signal-tower/ingress")

            first_attempt = "malformed-good-a"
            first_path = write_request(
                seed,
                first_attempt,
                request(attempt_id=first_attempt, capture_identity=first_attempt),
            )
            git(seed, "add", first_path)
            git(seed, "commit", "-q", "-m", "valid request before malformed")

            bad_attempt = "malformed-bad"
            bad_relative = f"{R147_ROOT}/transport/requests/{bad_attempt}.json"
            bad_path = seed / bad_relative
            bad_path.write_text('{"attempt_id": "malformed-bad",\n', encoding="utf-8")
            git(seed, "add", bad_relative)
            git(seed, "commit", "-q", "-m", "malformed request")

            last_attempt = "malformed-good-c"
            last_path = write_request(
                seed,
                last_attempt,
                request(attempt_id=last_attempt, capture_identity=last_attempt),
            )
            git(seed, "add", last_path)
            git(seed, "commit", "-q", "-m", "valid request after malformed")
            after = git(seed, "rev-parse", "HEAD")
            git(seed, "push", "-q", "origin", "signal-tower/ingress")

            subprocess.run(["git", "clone", "-q", str(remote), str(worker)], check=True)
            git(worker, "checkout", "-q", "signal-tower/ingress")

            with AuthorityHarness() as authority:
                materializer = FreshAuthorityMaterialCache(lambda _request: authority.material)
                result = persist_push_batch(
                    runtime_root=runtime,
                    transport_root=worker,
                    before=before,
                    after=after,
                    created=False,
                    observation_pr=443,
                    authority_materializer=materializer,
                )

            self.assertEqual("PERSISTED", result["status"])
            self.assertEqual(
                [first_attempt, bad_attempt, last_attempt],
                result["receipt_attempts"],
            )

            subprocess.run(["git", "clone", "-q", str(remote), str(verifier)], check=True)
            git(verifier, "checkout", "-q", "signal-tower/ingress")
            receipt_root = verifier / R147_ROOT / "transport" / "receipts"
            first = json.loads((receipt_root / f"{first_attempt}.json").read_text(encoding="utf-8"))
            bad = json.loads((receipt_root / f"{bad_attempt}.json").read_text(encoding="utf-8"))
            last = json.loads((receipt_root / f"{last_attempt}.json").read_text(encoding="utf-8"))

            self.assertEqual("ADMITTED", first["status"])
            self.assertTrue(first["durable_success"])
            self.assertEqual("NEEDS_REVALIDATION", bad["status"])
            self.assertFalse(bad["durable_success"])
            self.assertEqual("R147_REQUEST_FILE_INVALID", bad["code"])
            self.assertEqual(bad_attempt, bad["attempt_id"])
            self.assertEqual("ADMITTED", last["status"])
            self.assertTrue(last["durable_success"])

            journal = verifier / R147_ROOT / "transport" / "admitted_events.jsonl"
            rows = [line for line in journal.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(2, len(rows), "malformed request must not enter S0C replay transport")


if __name__ == "__main__":
    unittest.main()
