from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

from tools.verify_public_safe_boundary import (
    BoundaryViolation,
    CONFIG_PATH,
    _load_floor,
    _load_rules,
    _require_floor,
    verify_browser_source,
    verify_python_source,
    verify_repository,
    verify_workflow,
)
from tools.verify_r175_scope import FORBIDDEN, verify_scope


ROOT = Path(__file__).resolve().parents[1]
BASE = "740788a3847a402923bf2e89093d910eda0c89d0"
RULES = json.loads((ROOT / CONFIG_PATH).read_text(encoding="utf-8"))


class PythonCapabilityFloorTests(unittest.TestCase):
    def test_nonliteral_and_computed_dynamic_imports_fail_closed(self) -> None:
        attacks = (
            "m = __import__('req' + 'uests')\n",
            "name = 'requests'\nm = __import__(name)\n",
            "prefix = 'http'\nname = prefix + 'x'\nm = __import__(name)\n",
            "name = input()\nm = __import__(name)\n",
            "import importlib\nname = 'httpx'\nm = importlib.import_module(name)\n",
            "m = __import__.__call__('requests')\n",
        )
        for source in attacks:
            with self.subTest(source=source), self.assertRaises(BoundaryViolation):
                verify_python_source(source, "attack.py", RULES)

    def test_reflective_environment_access_fails_closed(self) -> None:
        attacks = (
            "import os\ngetattr(os, 'get' + 'env')('TOKEN')\n",
            "import os\nname = 'environ'\ngetattr(os, name).get('TOKEN')\n",
            "import os\nos.__dict__['environ'].get('TOKEN')\n",
            "import os as system\nmodule = system\ngetattr(module, 'getenv')('TOKEN')\n",
            "import os\nvars(os)['environ'].get('TOKEN')\n",
            "import os\nos.__getattribute__('environ').get('TOKEN')\n",
            "import os\nd = os.__dict__\nd.get('environ').get('TOKEN')\n",
            "exec(\"import requests\")\n",
            "__builtins__['__import__']('socket')\n",
            "__builtins__.__import__('requests')\n",
            "__import__('os').getenv('TOKEN')\n",
            "module = __import__('os')\nmodule.environ['TOKEN']\n",
            "getattr(__builtins__, '__import__')('requests')\n",
            "from os import environ as env\nenv['TOKEN']\n",
        )
        for source in attacks:
            with self.subTest(source=source), self.assertRaises(BoundaryViolation):
                verify_python_source(source, "attack.py", RULES)

    def test_safe_bounded_dynamic_import_and_safe_getattr_pass(self) -> None:
        verify_python_source(
            "name = 'json'\nmodule = __import__(name)\nvalue = getattr(module, 'dumps')({'offline': True})\n",
            "safe.py",
            RULES,
        )


class BrowserNormalizationFloorTests(unittest.TestCase):
    def test_alias_bracket_computed_and_escaped_browser_attacks_fail(self) -> None:
        attacks = (
            ("const f = window.fetch; f('https://x.invalid')", ".js"),
            ("globalThis['fetch']('https://x.invalid')", ".js"),
            ("globalThis['fe' + 'tch']('/collect')", ".js"),
            ("const u='https://x.invalid/m.js'; import(u)", ".mjs"),
            (r"body{background:url(\2f\2f x.invalid/a.png)}", ".css"),
            ("<svg><feImage href='https://x.invalid/a.png'/></svg>", ".svg"),
            ("<svg><mpath href='//x.invalid/path'/></svg>", ".svg"),
            ("<svg><script href='https://x.invalid/code.js'/></svg>", ".svg"),
            (r"<img src='https:\\x.invalid\a.png'>", ".html"),
            ("<script>const f=window.fetch; f('/relative')</script>", ".html"),
            ("const root=window; root[key]('/relative')", ".js"),
        )
        for source, suffix in attacks:
            with self.subTest(source=source), self.assertRaises(BoundaryViolation):
                verify_browser_source(source, "attack" + suffix, suffix)

    def test_direct_protocol_relative_meta_svg_and_srcset_fail(self) -> None:
        attacks = (
            "<img src='//x.invalid/a.png'>",
            "<img srcset='/a.png 1x, //x.invalid/b.png 2x'>",
            "<meta http-equiv='refresh' content='0; url=//x.invalid'>",
            "<svg><image xlink:href='//x.invalid/a.png'/></svg>",
        )
        for source in attacks:
            with self.subTest(source=source), self.assertRaises(BoundaryViolation):
                verify_browser_source(source, "attack.html", ".html")

    def test_relative_offline_assets_pass(self) -> None:
        verify_browser_source(
            "<img src='/assets/hero.png'><svg><use href='#hero'/></svg>",
            "offline.html",
            ".html",
        )


class CanonicalPolicyAndTraversalTests(unittest.TestCase):
    def test_current_repository_passes_immutable_floor(self) -> None:
        receipt = verify_repository(ROOT, policy_floor_ref=BASE)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["policy_floor_ref"], BASE)
        self.assertGreater(receipt["file_count"], 0)

    def test_config_and_workflow_cannot_co_shrink_floor(self) -> None:
        floor, _digest = _load_floor(ROOT, BASE)
        shrunk = copy.deepcopy(RULES)
        shrunk["scan_roots"].remove("apps/web")
        shrunk["required_pull_request_paths"].remove("apps/web/**")
        with self.assertRaises(BoundaryViolation):
            _require_floor(shrunk, floor)

    def test_config_cannot_claim_capability_class_while_shrinking_imports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.json"
            shrunk = copy.deepcopy(RULES)
            shrunk["forbidden_python_imports"].remove("socket")
            path.write_text(json.dumps(shrunk), encoding="utf-8")
            with self.assertRaises(BoundaryViolation):
                _load_rules(path)

    def test_rules_cannot_escape_repository_or_use_ambiguous_paths(self) -> None:
        attacks = (
            ("scan_roots", "../private"),
            ("scan_roots", "C:/Users/Administrator"),
            ("scan_roots", "apps\\web"),
            ("required_pull_request_paths", "../**"),
            ("scanned_suffixes", "py"),
        )
        for field, value in attacks:
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "rules.json"
                poisoned = copy.deepcopy(RULES)
                poisoned[field].append(value)
                path.write_text(json.dumps(poisoned), encoding="utf-8")
                with self.assertRaises(BoundaryViolation):
                    _load_rules(path)

    def test_fake_pull_request_block_outside_on_fails_closed(self) -> None:
        floor, _digest = _load_floor(ROOT, BASE)
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            workflow = repo / ".github" / "workflows" / "creative-runtime-offline.yml"
            workflow.parent.mkdir(parents=True)
            fake_paths = "\n".join(f"      - '{value}'" for value in RULES["required_pull_request_paths"])
            workflow.write_text(
                "name: fake\non:\n  workflow_dispatch:\nenv:\n  pull_request:\n    paths:\n"
                + fake_paths
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(BoundaryViolation):
                verify_workflow(repo, RULES, floor)

    def test_capability_classes_and_suffixes_cannot_shrink_floor(self) -> None:
        floor, _digest = _load_floor(ROOT, BASE)
        for field, value in (
            ("scanned_suffixes", ".svg"),
            ("forbidden_capability_classes", "DYNAMIC_REMOTE_IMPORT"),
        ):
            shrunk = copy.deepcopy(RULES)
            shrunk[field].remove(value)
            with self.subTest(field=field), self.assertRaises(BoundaryViolation):
                _require_floor(shrunk, floor)

    def test_scope_rejects_canonical_floor_and_unrelated_paths(self) -> None:
        with self.assertRaises(ValueError):
            verify_scope([FORBIDDEN])
        with self.assertRaises(ValueError):
            verify_scope(["coordination/ACTIVE-CODEX-TASK.yaml"])
        verify_scope(["creative_runtime/migration.py", "tests/test_creative_public_safe_boundary.py"])

    def _link(self, link: Path, target: Path, directory: bool) -> None:
        try:
            os.symlink(target, link, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"symlink unavailable: {error}")

    def test_nested_file_and_directory_links_fail_before_suffix_filter(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            target = Path(outside)
            (target / "opaque.bin").write_bytes(b"opaque")
            self._link(root / "external", target, True)
            from tools.verify_public_safe_boundary import _walk_no_indirection

            with self.assertRaises(BoundaryViolation):
                _walk_no_indirection(root)


if __name__ == "__main__":
    unittest.main()
