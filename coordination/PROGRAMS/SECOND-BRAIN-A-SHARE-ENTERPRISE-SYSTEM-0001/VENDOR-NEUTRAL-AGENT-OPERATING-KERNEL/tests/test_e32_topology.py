from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

from vendor_neutral_agent_kernel.evidence import (
    E32_RECEIPT_ALLOWLIST,
    validate_e32_archive_manifest,
    validate_e32_topology,
)


ROOT = Path(__file__).resolve().parents[1]


class E32TopologyTests(unittest.TestCase):
    def _topology(self, status: str = "TESTED_HEAD") -> dict:
        return json.loads((ROOT / "E32-TOPOLOGY-EVIDENCE.json").read_text(encoding="utf-8")) | {"status": status}

    def _write_topology(self, root: Path, value: dict) -> None:
        (root / "E32-TOPOLOGY-EVIDENCE.json").write_text(json.dumps(value, indent=2), encoding="utf-8")

    def _git(self, cwd: Path, *args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()

    def _repo(self) -> tuple[Path, Path, str]:
        base = Path(tempfile.mkdtemp(prefix="e32-topology-"))
        root = base / "coordination" / "PROGRAMS" / "SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001" / "VENDOR-NEUTRAL-AGENT-OPERATING-KERNEL"
        root.mkdir(parents=True)
        self._write_topology(root, self._topology())
        (root / "E32-ARCHIVE-PROVENANCE-MATRIX.yaml").write_text(
            yaml.safe_dump({
                "schema_version": "VNAK_E32_ARCHIVE_PROVENANCE_v1",
                "task_id": "CODEX-PEOS-0010-E31-FINAL-EXECUTABLE-HEAD-ARCHIVE-AND-SINGLE-RECEIPT-TOPOLOGY-CLOSURE-0024-E32",
                "status": "RUNTIME_EXPECTED",
                "required_root_count": 3,
                "tested_identity": {"binding": "EXACT_CI_CONTEXT", "commit": "CURRENT_CI_HEAD", "tree": "CURRENT_CI_TREE"},
                "declared_artifact_surface": {"name": "test", "path_count": 0, "paths": []},
                "roots": [],
            }, sort_keys=False), encoding="utf-8"
        )
        for path in E32_RECEIPT_ALLOWLIST:
            relative = Path(path).relative_to("coordination")
            target = base / "coordination" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target != root / "E32-TOPOLOGY-EVIDENCE.json" and target != root / "E32-ARCHIVE-PROVENANCE-MATRIX.yaml":
                target.write_text("evidence\n", encoding="utf-8")
        self._git(base, "init", "-q")
        self._git(base, "config", "user.email", "codex@example.invalid")
        self._git(base, "config", "user.name", "CODEX")
        self._git(base, "add", ".")
        self._git(base, "commit", "-qm", "tested head")
        tested = self._git(base, "rev-parse", "HEAD")
        return base, root, tested

    def test_tested_head_binds_exact_ci_context(self):
        _base, root, tested = self._repo()
        tree = self._git(root.parents[3], "rev-parse", f"{tested}^{{tree}}")
        result = validate_e32_topology(root, current_commit=tested, current_tree=tree, tested_commit=tested, tested_tree=tree)
        self.assertEqual(result["phase"], "TESTED_HEAD")

    def test_receipt_parent_must_equal_tested_head(self):
        base, root, tested = self._repo()
        for path in E32_RECEIPT_ALLOWLIST:
            relative = Path(path).relative_to("coordination")
            target = base / "coordination" / relative
            target.write_text("receipt\n", encoding="utf-8")
        evidence = self._topology("RECEIPT_HEAD")
        evidence["tested_identity"] = {"binding": "EXACT_TESTED_HEAD", "commit": tested, "tree": self._git(base, "rev-parse", f"{tested}^{{tree}}")}
        evidence["receipt_contract"] = {"binding": "EXACT_TESTED_PARENT", "parent_commit": "f" * 40, "head_binding": "CURRENT_PR_HEAD"}
        self._write_topology(root, evidence)
        self._git(base, "add", ".")
        self._git(base, "commit", "-qm", "receipt")
        current = self._git(base, "rev-parse", "HEAD")
        with self.assertRaisesRegex(ValueError, "RECEIPT_PARENT_CONTRACT_INVALID"):
            validate_e32_topology(root, current_commit=current, current_tree=self._git(base, "rev-parse", "HEAD^{tree}"), tested_commit=tested, tested_tree=self._git(base, "rev-parse", f"{tested}^{{tree}}"))

    def test_receipt_head_accepts_one_evidence_only_commit(self):
        base, root, tested = self._repo()
        tested_tree = self._git(base, "rev-parse", f"{tested}^{{tree}}")
        for path in E32_RECEIPT_ALLOWLIST:
            target = base / "coordination" / Path(path).relative_to("coordination")
            target.write_text("receipt\n", encoding="utf-8")
        evidence = self._topology("RECEIPT_HEAD")
        evidence["tested_identity"] = {"binding": "EXACT_TESTED_HEAD", "commit": tested, "tree": tested_tree}
        evidence["receipt_contract"] = {"binding": "EXACT_TESTED_PARENT", "parent_commit": tested, "head_binding": "CURRENT_PR_HEAD"}
        self._write_topology(root, evidence)
        self._git(base, "add", ".")
        self._git(base, "commit", "-qm", "receipt")
        current = self._git(base, "rev-parse", "HEAD")
        result = validate_e32_topology(root, current_commit=current, current_tree=self._git(base, "rev-parse", "HEAD^{tree}"), tested_commit=tested, tested_tree=tested_tree)
        self.assertEqual(result["receipt_parent"], tested)

    def test_executable_diff_cannot_hide_behind_receipt_label(self):
        base, root, tested = self._repo()
        tested_tree = self._git(base, "rev-parse", f"{tested}^{{tree}}")
        for path in E32_RECEIPT_ALLOWLIST:
            target = base / "coordination" / Path(path).relative_to("coordination")
            target.write_text("receipt\n", encoding="utf-8")
        (root / "ci_verify.py").write_text("print('changed')\n", encoding="utf-8")
        self._git(base, "add", ".")
        self._git(base, "commit", "-qm", "receipt evidence with executable change")
        current = self._git(base, "rev-parse", "HEAD")
        evidence = self._topology("RECEIPT_HEAD")
        evidence["tested_identity"] = {"binding": "EXACT_TESTED_HEAD", "commit": tested, "tree": tested_tree}
        evidence["receipt_contract"] = {"binding": "EXACT_TESTED_PARENT", "parent_commit": tested, "head_binding": "CURRENT_PR_HEAD"}
        self._write_topology(root, evidence)
        with self.assertRaisesRegex(ValueError, "RECEIPT_ALLOWLIST_VIOLATION"):
            validate_e32_topology(root, current_commit=current, current_tree=self._git(base, "rev-parse", "HEAD^{tree}"), tested_commit=tested, tested_tree=tested_tree)

    def test_runtime_archive_template_is_not_final(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.yaml"
            path.write_text((ROOT / "E32-ARCHIVE-PROVENANCE-MATRIX.yaml").read_text(encoding="utf-8"), encoding="utf-8")
            self.assertEqual(validate_e32_archive_manifest(path)["status"], "RUNTIME_EXPECTED")
            with self.assertRaisesRegex(ValueError, "FINAL_ARCHIVE_REQUIRED"):
                validate_e32_archive_manifest(path, require_final=True)

    def test_allowlist_is_exact_and_stable(self):
        self.assertEqual(tuple(sorted(E32_RECEIPT_ALLOWLIST)), E32_RECEIPT_ALLOWLIST)
        self.assertNotIn("ci_verify.py", E32_RECEIPT_ALLOWLIST)


if __name__ == "__main__":
    unittest.main()
