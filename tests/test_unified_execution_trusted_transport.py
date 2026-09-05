import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from coordination.GOVERNANCE import unified_execution_trust_gate as gate
from coordination.GOVERNANCE import unified_execution_trusted_transport as transport


def _run(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _make_bare_with_main(root: Path, name: str, marker: str) -> tuple[Path, str]:
    work = root / f"{name}-work"
    bare = root / f"{name}.git"
    work.mkdir()
    _run(work, "init", "--quiet", "-b", "main")
    _run(work, "config", "user.email", "test@example.invalid")
    _run(work, "config", "user.name", "UEF Test")
    (work / "marker.txt").write_text(marker, encoding="utf-8")
    _run(work, "add", "marker.txt")
    _run(work, "commit", "--quiet", "-m", "seed")
    sha = _run(work, "rev-parse", "HEAD")
    subprocess.run(
        ["git", "clone", "--bare", "--quiet", str(work), str(bare)],
        check=True,
    )
    return bare, sha


class TrustedTransportRewriteIsolationTests(unittest.TestCase):
    def test_repo_local_insteadof_cannot_redirect_initial_readback_or_fetch(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            legit, legit_sha = _make_bare_with_main(root, "legit", "LEGIT")
            fake, fake_sha = _make_bare_with_main(root, "fake", "FAKE")
            user_repo = root / "user"
            user_repo.mkdir()
            _run(user_repo, "init", "--quiet")

            legit_url = legit.as_uri()
            fake_url = fake.as_uri()
            _run(user_repo, "config", f"url.{fake_url}.insteadOf", legit_url)

            with patch.object(transport, "TRUSTED_CONTROL_PLANE_URL", legit_url):
                observed, read = transport.open_trusted_main(user_repo)

            self.assertEqual(observed, legit_sha)
            self.assertNotEqual(observed, fake_sha)
            self.assertEqual(read("marker.txt"), b"LEGIT")

    def test_environment_insteadof_cannot_redirect_trusted_transport(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            legit, legit_sha = _make_bare_with_main(root, "legit", "LEGIT")
            fake, _ = _make_bare_with_main(root, "fake", "FAKE")
            legit_url = legit.as_uri()
            fake_url = fake.as_uri()
            poisoned = {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": f"url.{fake_url}.insteadOf",
                "GIT_CONFIG_VALUE_0": legit_url,
            }
            with patch.dict(os.environ, poisoned, clear=False), patch.object(
                transport, "TRUSTED_CONTROL_PLANE_URL", legit_url
            ):
                self.assertEqual(transport.remote_main_sha(root), legit_sha)

    def test_terminal_recheck_uses_isolated_transport_not_user_repo_config(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            legit, legit_sha = _make_bare_with_main(root, "legit", "LEGIT")
            fake, _ = _make_bare_with_main(root, "fake", "FAKE")
            user_repo = root / "user"
            user_repo.mkdir()
            _run(user_repo, "init", "--quiet")
            legit_url = legit.as_uri()
            fake_url = fake.as_uri()
            _run(user_repo, "config", f"url.{fake_url}.insteadOf", legit_url)

            with patch.object(transport, "TRUSTED_CONTROL_PLANE_URL", legit_url):
                gate._terminal_remote_main_recheck(user_repo, legit_sha)


class DuplicateProtectedAdapterKeyTests(unittest.TestCase):
    def test_duplicate_trading_order_authority_fails_closed(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "coordination"
            / "EXECUTION"
            / "PROJECT-ADAPTERS"
            / "TRADING-SYSTEM.yaml"
        )
        text = path.read_text(encoding="utf-8")
        needle = '  order_authority: "SEPARATE_EXPLICIT_OWNER_GATE"\n'
        mutated = text.replace(needle, needle + '  order_authority: "GENERIC_ENGINEERING_ROUTE"\n', 1)
        with self.assertRaises(gate.ExecutionContractError):
            gate._strict_parse_adapter(mutated)

    def test_duplicate_top_level_execution_repository_fails_closed(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "coordination"
            / "EXECUTION"
            / "PROJECT-ADAPTERS"
            / "AI-DIRECTOR.yaml"
        )
        text = path.read_text(encoding="utf-8")
        needle = 'execution_repository: "vxz2datoubo/eustia-ai-film"\n'
        mutated = text.replace(
            needle,
            needle + 'execution_repository: "vxz2datoubo/second-brain-coordination"\n',
            1,
        )
        with self.assertRaises(gate.ExecutionContractError):
            gate._strict_parse_adapter(mutated)


if __name__ == "__main__":
    unittest.main()
