from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "verify_public_safe_boundary.py"
CONFIG = ROOT / "tools" / "public_safe_boundary_rules.json"
WORKFLOW = ROOT / ".github" / "workflows" / "creative-runtime-offline.yml"
SPEC = importlib.util.spec_from_file_location("creative_public_safe_boundary", TOOL)
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class PublicSafeBoundaryTests(unittest.TestCase):
    def _fixture(self, directory: str) -> tuple[Path, Path]:
        root = Path(directory)
        for relative in ("creative_runtime", "apps/cli", "tools", "apps/web"):
            (root / relative).mkdir(parents=True, exist_ok=True)
        (root / "creative_runtime" / "runtime.py").write_text("VALUE = 'offline'\n", encoding="utf-8")
        (root / "apps" / "cli" / "cli.py").write_text("def run(): return 'offline'\n", encoding="utf-8")
        (root / "tools" / "tool.py").write_text("RESULT = 'safe'\n", encoding="utf-8")
        (root / "apps" / "web" / "player.html").write_text("<html><body>offline</body></html>\n", encoding="utf-8")
        config = root / "rules.json"
        config.write_text(CONFIG.read_text(encoding="utf-8"), encoding="utf-8")
        return root, config

    def test_current_repository_passes_without_external_scanner(self) -> None:
        receipt = verifier.verify(ROOT, CONFIG)
        self.assertEqual("PASS", receipt["status"])
        self.assertFalse(receipt["external_scanner_required"])
        self.assertGreater(receipt["surface_file_counts"]["python_runtime"], 0)
        self.assertGreater(receipt["surface_file_counts"]["static_web"], 0)

    def test_ci_invokes_repository_verifier_and_retains_its_receipt(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python tools/verify_public_safe_boundary.py", workflow)
        self.assertIn("creative-runtime-public-safe-boundary-python-3.13.json", workflow)
        self.assertNotIn("if rg ", workflow)
        self.assertNotIn("CREATIVE_RUNTIME_PUBLIC_SAFE_BOUNDARY=PASS", workflow)

    def test_every_python_forbidden_class_fails(self) -> None:
        samples = {
            "requests.get('x')": "PY_REQUESTS",
            "urllib.request.urlopen('x')": "PY_URLLIB_REQUEST",
            "import httpx": "PY_HTTPX",
            "import openai": "PY_OPENAI",
            "import anthropic": "PY_ANTHROPIC",
            "os.environ['TOKEN']": "PY_OS_ENVIRON",
            "os.getenv('TOKEN')": "PY_OS_GETENV",
        }
        for content, rule_id in samples.items():
            with self.subTest(rule_id=rule_id), tempfile.TemporaryDirectory() as directory:
                root, config = self._fixture(directory)
                (root / "creative_runtime" / "runtime.py").write_text(content + "\n", encoding="utf-8")
                with self.assertRaisesRegex(verifier.PublicSafeBoundaryError, rule_id):
                    verifier.verify(root, config)

    def test_every_web_forbidden_class_fails(self) -> None:
        samples = {
            "<script>fetch('/x')</script>": "WEB_FETCH",
            "<script>new XMLHttpRequest()</script>": "WEB_XMLHTTPREQUEST",
            "<script>new WebSocket('/x')</script>": "WEB_WEBSOCKET",
            "<script>navigator.sendBeacon('/x')</script>": "WEB_SEND_BEACON",
            "<a href='https://example.invalid'>x</a>": "WEB_REMOTE_URL",
            "<script src='/remote.js'></script>": "WEB_REMOTE_SCRIPT",
        }
        for content, rule_id in samples.items():
            with self.subTest(rule_id=rule_id), tempfile.TemporaryDirectory() as directory:
                root, config = self._fixture(directory)
                (root / "apps" / "web" / "player.html").write_text(content + "\n", encoding="utf-8")
                with self.assertRaisesRegex(verifier.PublicSafeBoundaryError, rule_id):
                    verifier.verify(root, config)

    def test_missing_empty_and_non_utf8_surfaces_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, config = self._fixture(directory)
            missing_root = root / "apps" / "web"
            missing_root.rename(root / "apps" / "web-missing")
            with self.assertRaisesRegex(verifier.PublicSafeBoundaryError, "missing"):
                verifier.verify(root, config)
        with tempfile.TemporaryDirectory() as directory:
            root, config = self._fixture(directory)
            (root / "apps" / "web" / "player.html").unlink()
            with self.assertRaisesRegex(verifier.PublicSafeBoundaryError, "contains no declared files"):
                verifier.verify(root, config)
        with tempfile.TemporaryDirectory() as directory:
            root, config = self._fixture(directory)
            (root / "creative_runtime" / "runtime.py").write_bytes(b"\xff\xfe")
            with self.assertRaisesRegex(verifier.PublicSafeBoundaryError, "valid UTF-8"):
                verifier.verify(root, config)

    def test_malformed_configuration_and_regex_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, config = self._fixture(directory)
            config.write_text("{not-json", encoding="utf-8")
            with self.assertRaisesRegex(verifier.PublicSafeBoundaryError, "Malformed"):
                verifier.verify(root, config)
        with tempfile.TemporaryDirectory() as directory:
            root, config = self._fixture(directory)
            payload = json.loads(config.read_text(encoding="utf-8"))
            payload["surfaces"][0]["forbidden_patterns"][0]["regex"] = "("
            config.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(verifier.PublicSafeBoundaryError, "Malformed regex"):
                verifier.verify(root, config)

    def test_unexpected_verifier_exception_returns_nonzero_and_never_prints_pass(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(verifier, "verify", side_effect=RuntimeError("scanner exploded")):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = verifier.main(["--root", str(ROOT), "--config", str(CONFIG)])
        self.assertEqual(2, code)
        self.assertNotIn('"status":"PASS"', stdout.getvalue() + stderr.getvalue())
        self.assertIn('"status":"FAIL"', stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
