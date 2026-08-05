"""Product-source mutation harness.  It copies and mutates E53 source, never production paths."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Callable


@dataclass(frozen=True, slots=True)
class MutationResult:
    mutation_id: str
    file_names: tuple[str, ...]
    original_sha256: str
    mutated_sha256: str
    replacement_counts: tuple[int, ...]
    mutated_test_exit_code: int
    restored_test_exit_code: int
    killed: bool
    stdout_sha256: str
    stderr_sha256: str
    detected: bool


@dataclass(frozen=True, slots=True)
class CleanupResult:
    command: tuple[str, ...]
    timeout_seconds: float
    timed_out: bool
    reaped: bool


_MUTATIONS = (
    ("MUT-UTF8-STRICT", (("utf8_index.py", 'data.decode("utf-8", "strict")', 'data.decode("latin-1", "strict")'),)),
    ("MUT-ATOM-LEDGER", (("atoms.py", "if not self._ledger.is_exact_atom_candidate(start, end):", "if False:  # E53 deliberate mutation"),)),
    (
        "MUT-JSON-NAN",
        (
            ("packet.py", "normalized_validation = ensure_json_value(validation or {})", "normalized_validation = validation or {}  # E53 deliberate mutation"),
            (
                "packet.py",
                "return json.dumps(ensure_json_value(value), ensure_ascii=False, sort_keys=True, separators=(\",\", \":\"), allow_nan=False).encode(\"utf-8\")",
                "return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(\",\", \":\"), allow_nan=True).encode(\"utf-8\")",
            ),
        ),
    ),
)


def run_product_mutations(source_root: Path, timeout_seconds: float = 5.0) -> tuple[MutationResult, ...]:
    """Each mutation must cause its probe to fail its expected rejection assertion."""
    results: list[MutationResult] = []
    with tempfile.TemporaryDirectory(prefix="e53-mutation-") as raw_temp:
        temp = Path(raw_temp)
        copied_root = temp / "src"
        copied_tests = temp / "tests"
        shutil.copytree(source_root, copied_root)
        shutil.copytree(source_root.parent / "tests", copied_tests)
        for mutation_id, targets in _MUTATIONS:
            originals: dict[Path, str] = {}
            counts: list[int] = []
            original_parts: list[bytes] = []
            mutated_parts: list[bytes] = []
            for file_name, old, new in targets:
                target = copied_root / "e53_authority" / file_name
                original = originals.setdefault(target, target.read_text(encoding="utf-8"))
                replacement_count = original.count(old)
                if replacement_count != 1:
                    raise RuntimeError(f"mutation anchor mismatch for {mutation_id}: {replacement_count}")
                mutated = original.replace(old, new, 1)
                originals[target] = mutated
                counts.append(replacement_count)
                original_parts.append(original.encode("utf-8"))
                mutated_parts.append(mutated.encode("utf-8"))
            for target, mutated in originals.items():
                target.write_text(mutated, encoding="utf-8", newline="\n")
            environment = {**os.environ, "PYTHONPATH": str(copied_root), "PYTHONDONTWRITEBYTECODE": "1"}
            killed = False
            try:
                result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(copied_tests), "-p", "test_source_bound_authority.py"], capture_output=True, text=False, env=environment, timeout=timeout_seconds)
                exit_code = result.returncode
                stdout = result.stdout
                stderr = result.stderr
            except subprocess.TimeoutExpired as exc:
                killed = True
                exit_code = -9
                stdout = exc.stdout or b""
                stderr = exc.stderr or b""
            # The copied real product test must fail nonzero when the guard is removed.
            detected = exit_code != 0
            for target, original in originals.items():
                # Recover the pristine content from the source, not a mutable test alias.
                pristine = (source_root / "e53_authority" / target.name).read_text(encoding="utf-8")
                target.write_text(pristine, encoding="utf-8", newline="\n")
            restored = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(copied_tests), "-p", "test_source_bound_authority.py"], capture_output=True, text=False, env=environment, timeout=timeout_seconds)
            results.append(
                MutationResult(
                    mutation_id,
                    tuple(file_name for file_name, _, _ in targets),
                    sha256(b"\0".join(original_parts)).hexdigest(),
                    sha256(b"\0".join(mutated_parts)).hexdigest(),
                    tuple(counts),
                    exit_code,
                    restored.returncode,
                    killed,
                    sha256(stdout).hexdigest(),
                    sha256(stderr).hexdigest(),
                    detected,
                )
            )
            if restored.returncode != 0:
                raise RuntimeError(f"mutation restoration test failed for {mutation_id}")
    return tuple(results)


def prove_timeout_kill_and_reap(timeout_seconds: float = 0.2) -> CleanupResult:
    """Prove that an intentionally nonterminating child is killed and reaped."""
    command = (sys.executable, "-c", "while True: pass")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        process.communicate(timeout=5.0)
    return CleanupResult(command, timeout_seconds, timed_out, process.poll() is not None)
