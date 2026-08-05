"""Copied-production mutation harness for E54 authority guards.

Every mutation edits a copied E54 source file, invokes the copied product test
suite, records the nonzero result, restores exact pristine bytes, and proves
the restored copy is green. No repository source is modified by this harness.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Sequence


@dataclass(frozen=True, slots=True)
class MutationSpec:
    mutation_id: str
    target_file: str
    old: str
    new: str
    purpose: str


@dataclass(frozen=True, slots=True)
class MutationResult:
    mutation_id: str
    target_file: str
    purpose: str
    replacement_count: int
    pristine_sha256: str
    mutated_sha256: str
    mutated_exit_code: int
    restored_exit_code: int
    mutated_stdout_sha256: str
    mutated_stderr_sha256: str
    restored_source_sha256: str


MUTATION_SPECS: tuple[MutationSpec, ...] = (
    MutationSpec("MUT-LEDGER-ALIAS", "authority.py", "return deep_freeze(thaw(self._manifest))", "return thaw(self._manifest)", "ordinary caller can mutate nested manifest projection"),
    MutationSpec("MUT-LEDGER-RECOMPUTE", "authority.py", "return thaw(self._manifest) == thaw(expected) and self.evidence.verify()", "return True", "ledger accepts a forged manifest without recomputation"),
    MutationSpec("MUT-JSON-KEY-OWNERSHIP", "authority.py", "if lookahead >= length or data[lookahead] != 0x3A:", "if True:", "JSON key content is promoted as an atom"),
    MutationSpec("MUT-JSON-SYNTAX", "authority.py", "json.loads(data.decode(\"utf-8\", \"strict\"))", "None", "malformed JSON is admitted"),
    MutationSpec("MUT-JSONL-BOUNDARY", "authority.py", "if not line.strip():", "if line.strip():", "nonblank JSONL records are skipped"),
    MutationSpec("MUT-JSONL-SYNTAX", "authority.py", "json.loads(line.decode(\"utf-8\", \"strict\"))", "None", "malformed JSONL record is admitted"),
    MutationSpec("MUT-MARKDOWN-BLOCKQUOTE", "authority.py", "if stripped.startswith(b\">\"):", "if False:", "blockquote marker becomes atom-owned"),
    MutationSpec("MUT-MARKDOWN-LIST", "authority.py", "if match:", "if False:", "list marker becomes atom-owned"),
    MutationSpec("MUT-MARKDOWN-FENCE", "authority.py", "if fenced or not stripped or stripped.startswith(b\"#\") or stripped.startswith(b\"|\") or b\"|\" in stripped:", "if not stripped or stripped.startswith(b\"#\") or stripped.startswith(b\"|\") or b\"|\" in stripped:", "fenced code content becomes atom-owned"),
    MutationSpec("MUT-MARKDOWN-TABLE", "authority.py", "or b\"|\" in stripped", "or False", "inline Markdown table row becomes atom-owned"),
    MutationSpec("MUT-FIELD-PROVENANCE", "authority.py", "return field == self.extract_field(atom, name=field.name, start=field.start, end=field.end, rule=field.rule)", "return True", "altered field evidence is accepted"),
    MutationSpec("MUT-RELATION-EVIDENCE", "authority.py", "self._registry.evidence.source_sha256, sha256(raw).hexdigest(), relation.start, relation.end,", "self._registry.evidence.source_sha256, self._registry.evidence.source_sha256, relation.start, relation.end,", "source digest substitutes for exact relation evidence digest"),
    MutationSpec("MUT-PACKET-GRAPH", "authority.py", "packet.canonical_json == expected_json", "True", "packet canonical body is not compared to rebuilt graph"),
    MutationSpec("MUT-REDACTION-BLOCK", "authority.py", "if private_marker in data or b\"ghp_\" in data or b\"sk-\" in data:", "if False:", "private or credential-shaped marker enters source graph"),
    MutationSpec("MUT-HISTORY-ADD-DELETE", "hygiene.py", "bad_history = tuple(item for item in entries if item.forbidden)", "bad_history = ()", "historical generated file is ignored"),
    MutationSpec("MUT-RECEIPT-SHA", "topology.py", "for field in (\"base_sha\", \"plan_sha\", \"tested_sha\", \"receipt_sha\"):", "for field in ():", "placeholder SHA shapes are accepted"),
    MutationSpec("MUT-RECEIPT-FINAL-HEAD", "topology.py", "if head != receipt_sha:", "if False:", "post-receipt commit is accepted"),
    MutationSpec("MUT-PROVIDER-HEAD", "provider.py", "if environment.get(\"head_sha\") != expected_head:", "if False:", "changed Provider artifact head is accepted"),
)


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def run_mutation_matrix(source_package: Path, product_tests: Path, specs: Sequence[MutationSpec] = MUTATION_SPECS, timeout_seconds: float = 30.0) -> tuple[MutationResult, ...]:
    source_package = source_package.resolve()
    product_tests = product_tests.resolve()
    if not source_package.is_dir() or not product_tests.is_dir():
        raise RuntimeError("mutation harness requires existing source package and product tests")
    results: list[MutationResult] = []
    with tempfile.TemporaryDirectory(prefix="e54-mutation-") as temporary:
        root = Path(temporary)
        copied_src = root / "src"
        copied_pkg = copied_src / "e54_authority"
        copied_tests = root / "tests"
        shutil.copytree(source_package, copied_pkg)
        shutil.copytree(product_tests, copied_tests)
        environment = {**os.environ, "PYTHONPATH": str(copied_src), "PYTHONDONTWRITEBYTECODE": "1"}
        command = (sys.executable, "-m", "unittest", "discover", "-s", str(copied_tests), "-p", "test_authority.py")
        for spec in specs:
            target = copied_pkg / spec.target_file
            pristine = target.read_bytes()
            source = pristine.decode("utf-8", "strict")
            replacement_count = source.count(spec.old)
            if replacement_count != 1:
                raise RuntimeError(f"mutation anchor mismatch for {spec.mutation_id}: {replacement_count}")
            mutated = source.replace(spec.old, spec.new, 1).encode("utf-8")
            target.write_bytes(mutated)
            changed = subprocess.run(command, capture_output=True, env=environment, timeout=timeout_seconds, check=False)
            target.write_bytes(pristine)
            if target.read_bytes() != pristine:
                raise RuntimeError(f"source restoration mismatch for {spec.mutation_id}")
            restored = subprocess.run(command, capture_output=True, env=environment, timeout=timeout_seconds, check=False)
            result = MutationResult(
                spec.mutation_id, spec.target_file, spec.purpose, replacement_count, _sha(pristine), _sha(mutated),
                changed.returncode, restored.returncode, _sha(changed.stdout), _sha(changed.stderr), _sha(target.read_bytes()),
            )
            if changed.returncode == 0:
                raise RuntimeError(f"mutation survived copied product suite: {spec.mutation_id}")
            if restored.returncode != 0:
                raise RuntimeError(f"restored copied suite is not green: {spec.mutation_id}")
            results.append(result)
    return tuple(results)
