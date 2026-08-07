"""Executable E59 mutation registry using isolated copies and byte restoration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Iterable


TASK_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class MutationSpec:
    mutation_id: str
    blocker: str
    target: str
    original: str
    replacement: str
    test_selector: str
    invariant: str


MUTATION_SPECS: tuple[MutationSpec, ...] = (
    MutationSpec(
        "E59-M01", "E58-B1-public-self-bootstrap", "src/e59_runtime/authority_client.py",
        "if _factory_marker is not _FACTORY_MARKER:", "if False:",
        "test_authority_boundary.CanonicalAuthorityBoundaryTests.test_direct_caller_constructor_cannot_create_a_canonical_verifier",
        "A caller cannot construct an accepted verifier.",
    ),
    MutationSpec(
        "E59-M02", "E58-B2-caller-authored-evidence", "src/e59_runtime/authority_host.py",
        "if stored is None:\n            return False", "if stored is None:\n            return True",
        "test_authority_boundary.CanonicalAuthorityBoundaryTests.test_caller_authored_evidence_object_fails_host_ledger_verification",
        "A caller-created evidence object cannot pass host-ledger verification.",
    ),
    MutationSpec(
        "E59-M03", "E58-B3-caller-relation-label", "src/e59_runtime/authority_host.py",
        "if hint is not None and str(hint) != relation_type:", "if False:",
        "test_authority_boundary.CanonicalAuthorityBoundaryTests.test_caller_relation_label_cannot_override_ontology",
        "A caller relation label cannot override ontology derivation.",
    ),
    MutationSpec(
        "E59-M04", "E58-B4-unbound-excerpt", "src/e59_runtime/authority_host.py",
        "if not hmac.compare_digest(excerpt, str(span[\"decoded_text\"])):", "if False:",
        "test_authority_boundary.CanonicalAuthorityBoundaryTests.test_source_span_binding_rejects_changed_excerpt",
        "Evidence excerpt must exactly equal authority-issued decoded span text.",
    ),
    MutationSpec(
        "E59-M05", "E58-B5-direct-child-only", "src/e59_runtime/process_tree.py",
        "while changed:", "while False:",
        "test_process_tree.OwnedProcessTreeTests.test_root_exit_first_keeps_grandchildren_owned_until_cleanup",
        "Observed grandchildren remain owned after root exit.",
    ),
    MutationSpec(
        "E59-M06", "E58-B6-pid-reuse", "src/e59_runtime/process_tree.py",
        "return self.pid == current.pid and self.creation_time == current.creation_time", "return self.pid == current.pid",
        "test_process_tree.OwnedProcessTreeTests.test_pid_reuse_is_not_treated_as_same_owned_process",
        "PID reuse cannot authorize cleanup without creation-time equality.",
    ),
    MutationSpec(
        "E59-M07", "E58-B7-resource-cpu-gate", "src/e59_runtime/process_tree.py",
        "if cpu_workers > self.max_task_cpu_workers or cpu_workers > self.max_shared_cpu_workers:", "if False:",
        "test_process_tree.OwnedProcessTreeTests.test_gate_rejects_cpu_worker_cap",
        "CPU worker cap is an executable gate.",
    ),
    MutationSpec(
        "E59-M08", "E58-B8-shared-mutex", "src/e59_runtime/process_tree.py",
        "raise ResourceViolation(\"HEAVY_STAGE_MUTEX_UNAVAILABLE\")", "return",
        "test_process_tree.OwnedProcessTreeTests.test_second_gate_is_rejected_while_heavy_mutex_is_held",
        "The shared heavy-stage mutex rejects a second owner.",
    ),
    MutationSpec(
        "E59-M09", "E58-B9-global-python-kill", "src/e59_runtime/process_tree.py",
        "[\"taskkill\", \"/PID\", str(owned.pid), \"/T\"]", "[\"taskkill\", \"/IM\", \"python.exe\", \"/PID\", str(owned.pid), \"/T\"]",
        "test_process_tree.OwnedProcessTreeTests.test_cleanup_never_uses_an_executable_name_global_kill",
        "Cleanup must never target Python by executable name.",
    ),
)


def catalog_digest() -> str:
    payload = [asdict(spec) for spec in MUTATION_SPECS]
    return sha256(repr(payload).encode("utf-8")).hexdigest()


def run_mutation(spec: MutationSpec) -> dict[str, object]:
    """Run one real source mutation in a disposable copy and restore in finally."""

    # Windows can retain a just-closed test file briefly. The mutated source is
    # restored before this context exits; a delayed disposable-directory purge
    # must never erase the mutation verdict or impersonate a restore failure.
    with tempfile.TemporaryDirectory(prefix="e59-mutation-", ignore_cleanup_errors=True) as temp:
        root = Path(temp) / "CODEX-E59"
        shutil.copytree(TASK_ROOT / "src", root / "src")
        shutil.copytree(TASK_ROOT / "tests", root / "tests")
        target = root / spec.target
        before = target.read_bytes()
        before_hash = sha256(before).hexdigest()
        count = before.count(spec.original.encode("utf-8"))
        if count != 1:
            raise RuntimeError(f"MUTATION_TARGET_NOT_UNIQUE:{spec.mutation_id}:{count}")
        mutated = before.replace(spec.original.encode("utf-8"), spec.replacement.encode("utf-8"), 1)
        restored_hash = "NOT_RUN"
        completed = False
        try:
            target.write_bytes(mutated)
            environment = dict(os.environ)
            environment.update(
                {
                    "PYTHONPATH": str(root / "src") + os.pathsep + str(root / "tests"),
                    "OMP_NUM_THREADS": "1",
                    "MKL_NUM_THREADS": "1",
                    "OPENBLAS_NUM_THREADS": "1",
                    "NUMEXPR_NUM_THREADS": "1",
                    "TOKENIZERS_PARALLELISM": "false",
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
            )
            process = subprocess.run(
                [sys.executable, "-W", "error::ResourceWarning", "-m", "unittest", spec.test_selector],
                cwd=root / "tests",
                env=environment,
                capture_output=True,
                text=True,
                timeout=45,
                check=False,
            )
            completed = True
            return {
                "mutation_id": spec.mutation_id,
                "blocker": spec.blocker,
                "target": spec.target,
                "before_sha256": before_hash,
                "mutated_sha256": sha256(mutated).hexdigest(),
                "test_selector": spec.test_selector,
                "exit_code": process.returncode,
                "killed": process.returncode != 0,
                "stdout_sha256": sha256(process.stdout.encode("utf-8", "replace")).hexdigest(),
                "stderr_sha256": sha256(process.stderr.encode("utf-8", "replace")).hexdigest(),
                "completed": completed,
            }
        finally:
            target.write_bytes(before)
            restored_hash = sha256(target.read_bytes()).hexdigest()
            if restored_hash != before_hash:
                raise RuntimeError(f"MUTATION_RESTORE_FAILED:{spec.mutation_id}")
            time.sleep(0.05)


def run_all_mutations() -> list[dict[str, object]]:
    return [run_mutation(spec) for spec in MUTATION_SPECS]
