"""R147 regression: stale runtime main must be reconciled, not stranded."""
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

from r147_ingress import FreshAuthorityMaterialCache, process_github_request  # noqa: E402
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
    git(root, "config", "user.email", "r147-runtime-align@example.invalid")
    git(root, "config", "user.name", "R147 Runtime Alignment")


def write_request(root: Path, attempt: str) -> str:
    relative = f"{R147_ROOT}/transport/requests/{attempt}.json"
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            request(attempt_id=attempt, capture_identity=attempt),
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    return relative


class R147RuntimeMainAlignmentTests(unittest.TestCase):
    def test_main_advance_after_runtime_checkout_reconciles_then_admits(self):
        with tempfile.TemporaryDirectory() as directory:
            base_dir = Path(directory)

            runtime_remote = base_dir / "runtime-remote.git"
            runtime_seed = base_dir / "runtime-seed"
            runtime_worker = base_dir / "runtime-worker"
            subprocess.run(["git", "init", "--bare", "-q", str(runtime_remote)], check=True)
            git(base_dir, "init", "-q", str(runtime_seed))
            configure(runtime_seed)
            (runtime_seed / "canonical.txt").write_text("old-main\n", encoding="utf-8")
            git(runtime_seed, "add", "canonical.txt")
            git(runtime_seed, "commit", "-q", "-m", "old canonical main")
            git(runtime_seed, "branch", "-M", "main")
            old_main = git(runtime_seed, "rev-parse", "HEAD")
            git(runtime_seed, "remote", "add", "origin", str(runtime_remote))
            git(runtime_seed, "push", "-q", "origin", "main")
            subprocess.run(["git", "clone", "-q", str(runtime_remote), str(runtime_worker)], check=True)
            self.assertEqual(old_main, git(runtime_worker, "rev-parse", "HEAD"))

            # Adversarial timing: canonical main advances only after the runtime
            # checkout already exists, before the authority observation/binding.
            (runtime_seed / "canonical.txt").write_text("new-main\n", encoding="utf-8")
            git(runtime_seed, "add", "canonical.txt")
            git(runtime_seed, "commit", "-q", "-m", "advance canonical main")
            live_main = git(runtime_seed, "rev-parse", "HEAD")
            git(runtime_seed, "push", "-q", "origin", "main")
            self.assertNotEqual(old_main, live_main)
            self.assertEqual(old_main, git(runtime_worker, "rev-parse", "HEAD"))

            transport_remote = base_dir / "transport-remote.git"
            transport_seed = base_dir / "transport-seed"
            transport_worker = base_dir / "transport-worker"
            verifier = base_dir / "verifier"
            subprocess.run(["git", "init", "--bare", "-q", str(transport_remote)], check=True)
            git(base_dir, "init", "-q", str(transport_seed))
            configure(transport_seed)
            (transport_seed / "README.md").write_text("base\n", encoding="utf-8")
            git(transport_seed, "add", "README.md")
            git(transport_seed, "commit", "-q", "-m", "base")
            git(transport_seed, "branch", "-M", "main")
            before = git(transport_seed, "rev-parse", "HEAD")
            git(transport_seed, "remote", "add", "origin", str(transport_remote))
            git(transport_seed, "push", "-q", "origin", "main")
            git(transport_seed, "checkout", "-q", "-b", "signal-tower/ingress")
            attempt = "runtime-main-advance"
            request_path = write_request(transport_seed, attempt)
            git(transport_seed, "add", request_path)
            git(transport_seed, "commit", "-q", "-m", "request after stale runtime checkout")
            after = git(transport_seed, "rev-parse", "HEAD")
            git(transport_seed, "push", "-q", "origin", "signal-tower/ingress")
            subprocess.run(["git", "clone", "-q", str(transport_remote), str(transport_worker)], check=True)
            git(transport_worker, "checkout", "-q", "signal-tower/ingress")

            calls: list[str] = []
            with AuthorityHarness() as authority:
                materializer = FreshAuthorityMaterialCache(lambda _request: authority.material)

                def processor(*, runtime_root, transport_root, request_path, observation_pr):
                    current = git(runtime_root, "rev-parse", "HEAD")
                    calls.append(current)
                    if len(calls) == 1:
                        self.assertEqual(old_main, current)
                        # Model the canonical R145 result when live GitHub main is
                        # newer than the stale runtime binding. Nothing durable is
                        # written for this stale proof attempt.
                        return {
                            "attempt_id": attempt,
                            "status": "NEEDS_REVALIDATION",
                            "durable_success": False,
                            "code": "DOMAIN_AUTHORITY_CANONICAL_FRESHNESS_UNVERIFIED",
                        }
                    self.assertEqual(live_main, current)
                    return process_github_request(
                        runtime_root=runtime_root,
                        transport_root=transport_root,
                        request_path=request_path,
                        observation_pr=observation_pr,
                        authority_materializer=materializer,
                    )

                result = persist_push_batch(
                    runtime_root=runtime_worker,
                    transport_root=transport_worker,
                    before=before,
                    after=after,
                    created=False,
                    observation_pr=443,
                    processor=processor,
                    max_runtime_reconcile_attempts=3,
                )

            self.assertEqual([old_main, live_main], calls)
            self.assertEqual(live_main, git(runtime_worker, "rev-parse", "HEAD"))
            self.assertEqual("PERSISTED", result["status"])
            self.assertEqual([attempt], result["receipt_attempts"])

            subprocess.run(["git", "clone", "-q", str(transport_remote), str(verifier)], check=True)
            git(verifier, "checkout", "-q", "signal-tower/ingress")
            receipt_path = verifier / R147_ROOT / "transport" / "receipts" / f"{attempt}.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual("ADMITTED", receipt["status"])
            self.assertTrue(receipt["durable_success"])
            self.assertEqual("VERIFIED_SAME_LEDGER", receipt["readback_verification_status"])
            self.assertEqual("VERIFIED_FRESH_S0C_REPLAY", receipt["fresh_replay_verification_status"])
            self.assertNotEqual("NEEDS_REVALIDATION", receipt["status"])

            journal = verifier / R147_ROOT / "transport" / "admitted_events.jsonl"
            rows = [line for line in journal.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(1, len(rows), "stale attempt must not append; aligned retry appends exactly once")


if __name__ == "__main__":
    unittest.main()
