"""Adversarial regressions for R147 operational review blockers."""
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

from r147_ingress import FreshAuthorityMaterialCache, GitReplayTransport, derive_envelope, validate_transport_request  # noqa: E402
from r147_transport_workflow import (  # noqa: E402
    R147_ROOT,
    TransportWorkflowError,
    enumerate_push_request_changes,
    persist_push_batch,
)
from test_r147_ingress import AuthorityHarness, R147AutomaticIngressTests, request  # noqa: E402


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
    git(root, "config", "user.email", "r147-remediation@example.invalid")
    git(root, "config", "user.name", "R147 Remediation")


def write_request(root: Path, name: str, attempt: str, payload=None) -> str:
    relative = f"{R147_ROOT}/transport/requests/{name}.json"
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    value = {"attempt_id": attempt} if payload is None else dict(payload)
    target.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    return relative


class R147ReviewRemediationTests(unittest.TestCase):
    def test_explicit_capture_identity_survives_source_project_metadata_change_and_fails_closed(self):
        harness = R147AutomaticIngressTests(methodName="runTest")
        harness.setUp()
        self.addCleanup(harness.tearDown)
        first_raw = request(
            attempt_id="identity-project-1",
            capture_identity="stable-upstream-message-445",
            source_project="EUSTIA_AI_FILM",
        )
        second_raw = request(
            attempt_id="identity-project-2",
            capture_identity="stable-upstream-message-445",
            source_project="EUSTIA_AI_FILM_RENAMED_METADATA",
        )
        first_envelope = derive_envelope(
            validate_transport_request(first_raw),
            captured_at="2026-08-24T04:00:00+00:00",
        )
        second_envelope = derive_envelope(
            validate_transport_request(second_raw),
            captured_at="2026-08-24T04:01:00+00:00",
        )
        self.assertEqual(first_envelope["envelope_id"], second_envelope["envelope_id"])

        with AuthorityHarness() as authority:
            ingress = harness.ingress(authority)
            first = ingress.process(first_raw)
            second = ingress.process(second_raw)
        self.assertEqual("ADMITTED", first["status"])
        self.assertFalse(second["durable_success"])
        self.assertEqual("IDEMPOTENCY_KEY_COLLISION", second["code"])
        transport = GitReplayTransport(harness.journal)
        ledger, replay = transport.replay(transport.load_events())
        try:
            self.assertEqual(1, replay["event_count"])
        finally:
            ledger.close()

    def test_batched_push_enumerates_every_request_commit_not_only_tip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-q")
            configure(root)
            (root / "README.md").write_text("base\n", encoding="utf-8")
            git(root, "add", "README.md")
            git(root, "commit", "-q", "-m", "base")
            before = git(root, "rev-parse", "HEAD")

            path_a = write_request(root, "batch-a", "batch-a")
            git(root, "add", path_a)
            git(root, "commit", "-q", "-m", "request a")
            commit_a = git(root, "rev-parse", "HEAD")

            path_b = write_request(root, "batch-b", "batch-b")
            git(root, "add", path_b)
            git(root, "commit", "-q", "-m", "request b")
            commit_b = git(root, "rev-parse", "HEAD")

            changes = enumerate_push_request_changes(
                root,
                before=before,
                after=commit_b,
                created=False,
            )
            self.assertEqual(
                [(commit_a, path_a), (commit_b, path_b)],
                [(item.commit, item.path) for item in changes],
            )

    def test_new_transport_branch_range_is_bounded_from_main_merge_base(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-q")
            configure(root)
            (root / "README.md").write_text("base\n", encoding="utf-8")
            git(root, "add", "README.md")
            git(root, "commit", "-q", "-m", "base")
            git(root, "branch", "main")

            path_a = write_request(root, "new-branch-a", "new-branch-a")
            git(root, "add", path_a)
            git(root, "commit", "-q", "-m", "request a")
            path_b = write_request(root, "new-branch-b", "new-branch-b")
            git(root, "add", path_b)
            git(root, "commit", "-q", "-m", "request b")
            after = git(root, "rev-parse", "HEAD")

            changes = enumerate_push_request_changes(
                root,
                before="0" * 40,
                after=after,
                created=True,
                main_ref="main",
            )
            self.assertEqual([path_a, path_b], [item.path for item in changes])

    def test_non_request_change_anywhere_in_batched_range_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-q")
            configure(root)
            (root / "README.md").write_text("base\n", encoding="utf-8")
            git(root, "add", "README.md")
            git(root, "commit", "-q", "-m", "base")
            before = git(root, "rev-parse", "HEAD")

            (root / "forbidden.txt").write_text("not a request\n", encoding="utf-8")
            git(root, "add", "forbidden.txt")
            git(root, "commit", "-q", "-m", "forbidden earlier change")
            path_b = write_request(root, "later-request", "later-request")
            git(root, "add", path_b)
            git(root, "commit", "-q", "-m", "request")
            after = git(root, "rev-parse", "HEAD")

            with self.assertRaises(TransportWorkflowError) as caught:
                enumerate_push_request_changes(
                    root,
                    before=before,
                    after=after,
                    created=False,
                )
            self.assertEqual("R147_TRIGGER_SCOPE_FORBIDDEN", caught.exception.code)

    def test_remote_advance_race_reconciles_and_replays_without_losing_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            base_dir = Path(directory)
            remote = base_dir / "remote.git"
            seed = base_dir / "seed"
            worker = base_dir / "worker"
            racer = base_dir / "racer"
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
            base = git(seed, "rev-parse", "HEAD")
            git(seed, "remote", "add", "origin", str(remote))
            git(seed, "push", "-q", "origin", "main")
            git(seed, "checkout", "-q", "-b", "signal-tower/ingress")
            request_one = write_request(seed, "race-one", "race-one")
            git(seed, "add", request_one)
            git(seed, "commit", "-q", "-m", "request one")
            trigger_after = git(seed, "rev-parse", "HEAD")
            git(seed, "push", "-q", "origin", "signal-tower/ingress")

            subprocess.run(["git", "clone", "-q", str(remote), str(worker)], check=True)
            git(worker, "checkout", "-q", "signal-tower/ingress")
            subprocess.run(["git", "clone", "-q", str(remote), str(racer)], check=True)
            git(racer, "checkout", "-q", "signal-tower/ingress")
            configure(racer)

            def fake_processor(*, runtime_root, transport_root, request_path, observation_pr):
                del runtime_root, observation_pr
                raw = json.loads(request_path.read_text(encoding="utf-8"))
                attempt = raw["attempt_id"]
                state = transport_root / R147_ROOT / "transport"
                state.mkdir(parents=True, exist_ok=True)
                journal = state / "admitted_events.jsonl"
                rows = []
                if journal.exists():
                    rows = [line for line in journal.read_text(encoding="utf-8").splitlines() if line]
                marker = json.dumps({"attempt_id": attempt}, sort_keys=True)
                if marker not in rows:
                    rows.append(marker)
                journal.write_text("\n".join(rows) + "\n", encoding="utf-8")
                receipt = state / "receipts" / f"{attempt}.json"
                receipt.parent.mkdir(parents=True, exist_ok=True)
                payload = {"attempt_id": attempt, "status": "ADMITTED"}
                receipt.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
                return payload

            def advance_remote(push_attempt: int) -> None:
                if push_attempt != 1:
                    return
                request_two = write_request(racer, "race-two", "race-two")
                git(racer, "add", request_two)
                git(racer, "commit", "-q", "-m", "external request races first job")
                git(racer, "push", "-q", "origin", "signal-tower/ingress")

            result = persist_push_batch(
                runtime_root=runtime,
                transport_root=worker,
                before=base,
                after=trigger_after,
                created=False,
                observation_pr=443,
                processor=fake_processor,
                before_push_hook=advance_remote,
            )
            self.assertEqual("PERSISTED", result["status"])
            self.assertEqual(2, result["push_attempt"])

            subprocess.run(["git", "clone", "-q", str(remote), str(verifier)], check=True)
            git(verifier, "checkout", "-q", "signal-tower/ingress")
            external_request = verifier / R147_ROOT / "transport" / "requests" / "race-two.json"
            receipt = verifier / R147_ROOT / "transport" / "receipts" / "race-one.json"
            journal = verifier / R147_ROOT / "transport" / "admitted_events.jsonl"
            self.assertTrue(external_request.is_file(), "remote caller request must survive reconciliation")
            self.assertTrue(receipt.is_file(), "original job receipt must survive non-fast-forward retry")
            self.assertIn('"attempt_id": "race-one"', journal.read_text(encoding="utf-8"))

    def test_compatible_batch_reuses_one_fresh_authority_material_under_one_call_budget(self):
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
            (seed / "README.md").write_text("base\
", encoding="utf-8")
            git(seed, "add", "README.md")
            git(seed, "commit", "-q", "-m", "base")
            git(seed, "branch", "-M", "main")
            before = git(seed, "rev-parse", "HEAD")
            git(seed, "remote", "add", "origin", str(remote))
            git(seed, "push", "-q", "origin", "main")
            git(seed, "checkout", "-q", "-b", "signal-tower/ingress")

            attempts = []
            for index in range(4):
                attempt = f"budget-{index}"
                attempts.append(attempt)
                payload = request(
                    attempt_id=attempt,
                    capture_identity=f"budget-capture-{index}",
                )
                path = write_request(seed, attempt, attempt, payload)
                git(seed, "add", path)
                git(seed, "commit", "-q", "-m", f"request {index}")
            after = git(seed, "rev-parse", "HEAD")
            git(seed, "push", "-q", "origin", "signal-tower/ingress")

            subprocess.run(["git", "clone", "-q", str(remote), str(worker)], check=True)
            git(worker, "checkout", "-q", "signal-tower/ingress")

            with AuthorityHarness() as authority:
                calls = []

                def one_call_budget(_request):
                    calls.append(True)
                    if len(calls) > 1:
                        raise AssertionError("simulated live-observation budget exhausted")
                    return authority.material

                result = persist_push_batch(
                    runtime_root=runtime,
                    transport_root=worker,
                    before=before,
                    after=after,
                    created=False,
                    observation_pr=443,
                    authority_materializer=FreshAuthorityMaterialCache(one_call_budget),
                )

            self.assertEqual("PERSISTED", result["status"])
            self.assertEqual(1, len(calls), "compatible batch must spend one authority observation budget")
            self.assertEqual(attempts, result["receipt_attempts"])

            subprocess.run(["git", "clone", "-q", str(remote), str(verifier)], check=True)
            git(verifier, "checkout", "-q", "signal-tower/ingress")
            for attempt in attempts:
                receipt_path = verifier / R147_ROOT / "transport" / "receipts" / f"{attempt}.json"
                payload = json.loads(receipt_path.read_text(encoding="utf-8"))
                self.assertTrue(payload["durable_success"], payload)
                self.assertEqual("ADMITTED", payload["status"], payload)

    def test_push_range_skips_structural_merge_node_and_keeps_parent_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-q")
            configure(root)
            (root / "README.md").write_text("base\
", encoding="utf-8")
            git(root, "add", "README.md")
            git(root, "commit", "-q", "-m", "base")
            before = git(root, "rev-parse", "HEAD")
            main_branch = git(root, "branch", "--show-current")

            git(root, "checkout", "-q", "-b", "request-side")
            side_path = write_request(root, "merge-side", "merge-side")
            git(root, "add", side_path)
            git(root, "commit", "-q", "-m", "side request")

            git(root, "checkout", "-q", main_branch)
            main_path = write_request(root, "merge-main", "merge-main")
            git(root, "add", main_path)
            git(root, "commit", "-q", "-m", "main request")
            git(root, "merge", "-q", "--no-ff", "request-side", "-m", "merge request histories")
            after = git(root, "rev-parse", "HEAD")

            changes = enumerate_push_request_changes(
                root,
                before=before,
                after=after,
                created=False,
            )
            paths = [item.path for item in changes]
            self.assertCountEqual([main_path, side_path], paths)
            self.assertEqual(2, len(paths), "structural merge commit must not create a phantom request")


if __name__ == "__main__":
    unittest.main()
