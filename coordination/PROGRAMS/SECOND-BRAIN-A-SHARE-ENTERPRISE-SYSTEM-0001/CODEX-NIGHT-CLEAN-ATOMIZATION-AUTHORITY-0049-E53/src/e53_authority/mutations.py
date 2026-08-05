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
    file_name: str
    original_sha256: str
    mutated_sha256: str
    replacement_count: int
    probe_exit_code: int
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


_PROBES = {
    "MUT-UTF8-STRICT": "from e53_authority import SourceEvidence\nSourceEvidence.from_bytes(b'\\xed', source_id='x', format_name='text')\n",
    "MUT-ATOM-LEDGER": "from e53_authority import SourceEvidence, build_ledger, AtomFactory\ne=SourceEvidence.from_bytes(b'alpha\\n', source_id='x', format_name='text')\nAtomFactory(e, build_ledger(e)).issue(0, 1)\n",
    "MUT-JSON-NAN": "from e53_authority.atoms import ensure_json_value\nensure_json_value(float('nan'))\n",
}

_MUTATIONS = (
    ("MUT-UTF8-STRICT", "utf8_index.py", 'data.decode("utf-8", "strict")', 'data.decode("latin-1", "strict")'),
    ("MUT-ATOM-LEDGER", "atoms.py", "if not self._ledger.is_exact_atom_candidate(start, end):", "if False:  # E53 deliberate mutation"),
    ("MUT-JSON-NAN", "atoms.py", "if not math.isfinite(value):", "if False:  # E53 deliberate mutation"),
)


def run_product_mutations(source_root: Path, timeout_seconds: float = 5.0) -> tuple[MutationResult, ...]:
    """Each mutation must cause its probe to fail its expected rejection assertion."""
    results: list[MutationResult] = []
    with tempfile.TemporaryDirectory(prefix="e53-mutation-") as raw_temp:
        temp = Path(raw_temp)
        copied_root = temp / "src"
        shutil.copytree(source_root, copied_root)
        for mutation_id, file_name, old, new in _MUTATIONS:
            target = copied_root / "e53_authority" / file_name
            original = target.read_text(encoding="utf-8")
            replacement_count = original.count(old)
            if replacement_count != 1:
                raise RuntimeError(f"mutation anchor mismatch for {mutation_id}: {replacement_count}")
            original_sha = sha256(original.encode("utf-8")).hexdigest()
            mutated = original.replace(old, new, 1)
            target.write_text(mutated, encoding="utf-8", newline="\n")
            environment = {**os.environ, "PYTHONPATH": str(copied_root), "PYTHONDONTWRITEBYTECODE": "1"}
            killed = False
            try:
                result = subprocess.run([sys.executable, "-c", _PROBES[mutation_id]], capture_output=True, text=False, env=environment, timeout=timeout_seconds)
                exit_code = result.returncode
                stdout = result.stdout
                stderr = result.stderr
            except subprocess.TimeoutExpired as exc:
                killed = True
                exit_code = -9
                stdout = exc.stdout or b""
                stderr = exc.stderr or b""
            # The intentionally mutated implementation must ACCEPT the bad input,
            # so the rejection probe returns 0.  That is a detected killed mutant.
            detected = exit_code == 0
            results.append(
                MutationResult(
                    mutation_id,
                    file_name,
                    original_sha,
                    sha256(mutated.encode("utf-8")).hexdigest(),
                    replacement_count,
                    exit_code,
                    killed,
                    sha256(stdout).hexdigest(),
                    sha256(stderr).hexdigest(),
                    detected,
                )
            )
            target.write_text(original, encoding="utf-8", newline="\n")
            if target.read_text(encoding="utf-8") != original:
                raise RuntimeError(f"mutation restoration failed for {mutation_id}")
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
