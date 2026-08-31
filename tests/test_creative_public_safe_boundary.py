from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from tools.verify_public_safe_boundary import (
    BoundaryViolation,
    verify_browser_source,
    verify_python_source,
    verify_repository,
    verify_workflow_congruence,
)


ROOT = Path(__file__).resolve().parents[1]
RULES = json.loads((ROOT / "tools" / "public_safe_boundary_rules.json").read_text(encoding="utf-8"))


class PublicSafeCapabilityTests(unittest.TestCase):
    def test_alias_and_from_import_network_capabilities_fail(self) -> None:
        attacks = (
            "import requests as r\nr.get('https://example.invalid')\n",
            "from requests import get\nget('https://example.invalid')\n",
            "from urllib import request\nrequest.urlopen('https://example.invalid')\n",
            "import socket as s\ns.create_connection(('example.invalid', 443))\n",
        )
        for source in attacks:
            with self.subTest(source=source), self.assertRaises(BoundaryViolation):
                verify_python_source(source, "attack.py", RULES)

    def test_alias_and_from_import_environment_capabilities_fail(self) -> None:
        attacks = (
            "from os import getenv\ngetenv('TOKEN')\n",
            "import os as o\no.environ['TOKEN']\n",
            "from os import environ as secrets\nprint(secrets.get('TOKEN'))\n",
        )
        for source in attacks:
            with self.subTest(source=source), self.assertRaises(BoundaryViolation):
                verify_python_source(source, "attack.py", RULES)

    def test_safe_standard_library_source_passes(self) -> None:
        verify_python_source("import json\nprint(json.dumps({'offline': True}))\n", "safe.py", RULES)

    def test_protocol_relative_active_browser_loads_fail(self) -> None:
        attacks = (
            "<img src='//tracker.invalid/pixel'>",
            "<iframe src=\"//remote.invalid/frame\"></iframe>",
            "<form action='//remote.invalid/collect'></form>",
            "<style>body{background:url(//remote.invalid/a.png)}</style>",
            "<img srcset='/local.png 1x, //remote.invalid/a.png 2x'>",
        )
        for source in attacks:
            with self.subTest(source=source), self.assertRaises(BoundaryViolation):
                verify_browser_source(source, "attack.html", ".html")

    def test_relative_browser_assets_pass(self) -> None:
        verify_browser_source("<img src='/assets/hero.png'><form action='/choose'></form>", "safe.html", ".html")

    def test_repository_verifier_passes_current_tree(self) -> None:
        receipt = verify_repository(ROOT)
        self.assertEqual(receipt["status"], "PASS")
        self.assertGreater(receipt["file_count"], 0)


class PublicSafeTraversalAndWorkflowTests(unittest.TestCase):
    def _minimal_repository(self, root: Path) -> None:
        (root / "creative_runtime").mkdir(parents=True)
        (root / "apps" / "cli").mkdir(parents=True)
        (root / "apps" / "web").mkdir(parents=True)
        (root / "tools").mkdir(parents=True)
        (root / ".github" / "workflows").mkdir(parents=True)
        for directory in (root / "creative_runtime", root / "apps" / "cli", root / "apps" / "web", root / "tools"):
            (directory / "safe.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "tools" / "public_safe_boundary_rules.json").write_text(
            json.dumps(RULES, sort_keys=True), encoding="utf-8"
        )
        paths = "\n".join(f"      - '{item}'" for item in RULES["required_pull_request_paths"])
        (root / ".github" / "workflows" / "creative-runtime-offline.yml").write_text(
            f"name: test\non:\n  pull_request:\n    paths:\n{paths}\njobs: {{}}\n", encoding="utf-8"
        )

    def _make_symlink(self, link: Path, target: Path, directory: bool) -> None:
        try:
            os.symlink(target, link, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"symlink creation unavailable: {error}")

    def test_nested_directory_symlink_to_inside_root_fails_before_filtering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self._minimal_repository(repo)
            target = repo / "creative_runtime" / "real"
            target.mkdir()
            (target / "payload.bin").write_bytes(b"not-a-scanned-suffix")
            self._make_symlink(repo / "creative_runtime" / "nested-link", target, True)
            with self.assertRaises(BoundaryViolation):
                verify_repository(repo)

    def test_nested_directory_symlink_to_outside_root_fails_before_filtering(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            repo = Path(directory)
            self._minimal_repository(repo)
            self._make_symlink(repo / "apps" / "web" / "external", Path(outside), True)
            with self.assertRaises(BoundaryViolation):
                verify_repository(repo)

    def test_nested_file_symlink_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            repo = Path(directory)
            self._minimal_repository(repo)
            target = Path(outside) / "payload.txt"
            target.write_text("opaque", encoding="utf-8")
            self._make_symlink(repo / "tools" / "opaque.data", target, False)
            with self.assertRaises(BoundaryViolation):
                verify_repository(repo)

    def test_workflow_trigger_drift_fails_mechanically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self._minimal_repository(repo)
            workflow = repo / ".github" / "workflows" / "creative-runtime-offline.yml"
            workflow.write_text(workflow.read_text(encoding="utf-8").replace("      - 'tools/**'\n", ""), encoding="utf-8")
            with self.assertRaises(BoundaryViolation):
                verify_workflow_congruence(repo, RULES)

    def test_unexpected_workflow_trigger_also_fails_congruence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self._minimal_repository(repo)
            workflow = repo / ".github" / "workflows" / "creative-runtime-offline.yml"
            workflow.write_text(
                workflow.read_text(encoding="utf-8").replace("jobs: {}", "      - 'unscanned/**'\njobs: {}"),
                encoding="utf-8",
            )
            with self.assertRaises(BoundaryViolation):
                verify_workflow_congruence(repo, RULES)

    def test_empty_non_utf8_and_unknown_config_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self._minimal_repository(repo)
            config = repo / "bad.json"
            for payload in (b"", b"\xff", b'{"schema":"Unknown/v1"}'):
                config.write_bytes(payload)
                with self.subTest(payload=payload), self.assertRaises(BoundaryViolation):
                    verify_repository(repo, Path("bad.json"))


if __name__ == "__main__":
    unittest.main()
