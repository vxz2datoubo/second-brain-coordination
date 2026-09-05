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


def _make_malicious_template(
    root: Path, fake_url: str, trusted_url: str
) -> Path:
    template = root / "malicious-template"
    template.mkdir()
    (template / "config").write_text(
        '[core]\n'
        '    repositoryformatversion = 0\n'
        '    bare = true\n'
        f'[url "{fake_url}"]\n'
        f'    insteadOf = {trusted_url}\n',
        encoding="utf-8",
    )
    return template


def _make_fake_git_shim(root: Path) -> tuple[Path, Path]:
    shim_dir = root / "poisoned-path"
    shim_dir.mkdir()
    marker = root / "fake-git-was-invoked"
    shim = shim_dir / "git"
    shim.write_text(
        "#!/bin/sh\n"
        f"printf invoked > '{marker}'\n"
        "printf 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\\trefs/heads/main\\n'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return shim_dir, marker


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

    def test_git_template_dir_cannot_seed_url_rewrite_into_trust_repo(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            legit, legit_sha = _make_bare_with_main(root, "legit", "LEGIT")
            fake, fake_sha = _make_bare_with_main(root, "fake", "FAKE")
            legit_url = legit.as_uri()
            fake_url = fake.as_uri()
            malicious_template = _make_malicious_template(
                root, fake_url, legit_url
            )

            with patch.dict(
                os.environ,
                {"GIT_TEMPLATE_DIR": str(malicious_template)},
                clear=False,
            ), patch.object(transport, "TRUSTED_CONTROL_PLANE_URL", legit_url):
                observed, read = transport.open_trusted_main(root)
                terminal = transport.remote_main_sha(root)
                gate._terminal_remote_main_recheck(root, legit_sha)

            self.assertEqual(observed, legit_sha)
            self.assertEqual(terminal, legit_sha)
            self.assertNotEqual(observed, fake_sha)
            self.assertEqual(read("marker.txt"), b"LEGIT")

    @unittest.skipIf(os.name == "nt", "POSIX real-shim attack regression")
    def test_poisoned_path_cannot_select_fake_git_executable(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            legit, legit_sha = _make_bare_with_main(root, "legit", "LEGIT")
            shim_dir, marker = _make_fake_git_shim(root)

            with patch.dict(
                os.environ,
                {"PATH": str(shim_dir)},
                clear=False,
            ), patch.object(
                transport, "TRUSTED_CONTROL_PLANE_URL", legit.as_uri()
            ):
                observed = transport.remote_main_sha(root)

            self.assertEqual(observed, legit_sha)
            self.assertFalse(marker.exists(), "caller PATH git shim was executed")

    def test_sanitized_env_is_minimal_and_drops_execution_injection(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            poisoned = {
                "PATH": str(root / "evil-bin"),
                "LD_PRELOAD": str(root / "evil.so"),
                "DYLD_INSERT_LIBRARIES": str(root / "evil.dylib"),
                "PYTHONPATH": str(root / "evil-python"),
                "HTTPS_PROXY": "http://127.0.0.1:9",
                "SSL_CERT_FILE": str(root / "evil-ca.pem"),
                "GIT_TEMPLATE_DIR": str(root / "evil-template"),
                "GIT_EXEC_PATH": str(root / "evil-exec"),
                "GIT_SSH_COMMAND": "false",
                "GIT_CONFIG_COUNT": "1",
            }
            identity = transport._resolve_trusted_git_executable()
            with patch.dict(os.environ, poisoned, clear=False):
                env = transport._sanitized_env(
                    root / "home", identity=identity
                )

            self.assertNotEqual(env["PATH"], poisoned["PATH"])
            self.assertNotIn("LD_PRELOAD", env)
            self.assertNotIn("DYLD_INSERT_LIBRARIES", env)
            self.assertNotIn("PYTHONPATH", env)
            self.assertNotIn("HTTPS_PROXY", env)
            self.assertNotIn("SSL_CERT_FILE", env)
            self.assertNotIn("GIT_EXEC_PATH", env)
            self.assertNotIn("GIT_SSH_COMMAND", env)
            self.assertNotIn("GIT_CONFIG_COUNT", env)
            self.assertEqual(env["GIT_CONFIG_NOSYSTEM"], "1")
            self.assertEqual(env["GIT_CONFIG_GLOBAL"], os.devnull)
            self.assertNotEqual(env["GIT_TEMPLATE_DIR"], poisoned["GIT_TEMPLATE_DIR"])

    def test_trusted_git_identity_is_absolute_digest_attested(self):
        identity = transport._resolve_trusted_git_executable()
        self.assertTrue(identity.path.is_absolute())
        self.assertEqual(len(identity.sha256), 64)
        transport._assert_trusted_git_identity(identity)

    @unittest.skipIf(os.name == "nt", "POSIX temp executable mutation regression")
    def test_trusted_git_identity_digest_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            executable = root / "git"
            executable.write_bytes(b"first")
            executable.chmod(0o755)
            identity = transport.TrustedGitExecutable(
                path=executable.resolve(),
                sha256=transport._hash_file(executable),
                provenance="TEST_ONLY",
            )
            transport._assert_trusted_git_identity(identity)
            executable.write_bytes(b"second")
            with self.assertRaises(transport.TrustedTransportError):
                transport._assert_trusted_git_identity(identity)

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

    def test_duplicate_top_level_hard_boundaries_section_fails_closed(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "coordination"
            / "EXECUTION"
            / "PROJECT-ADAPTERS"
            / "TRADING-SYSTEM.yaml"
        )
        text = path.read_text(encoding="utf-8")
        mutated = text + '\nhard_boundaries:\n  - "ALLOW_LIVE_TRADE"\n'
        with self.assertRaises(gate.ExecutionContractError):
            gate._strict_parse_adapter(mutated)

    def test_duplicate_top_level_authority_section_fails_closed(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "coordination"
            / "EXECUTION"
            / "PROJECT-ADAPTERS"
            / "TRADING-SYSTEM.yaml"
        )
        text = path.read_text(encoding="utf-8")
        mutated = text + '\nauthority:\n  order_authority: "GENERIC_ENGINEERING_ROUTE"\n'
        with self.assertRaises(gate.ExecutionContractError):
            gate._strict_parse_adapter(mutated)


if __name__ == "__main__":
    unittest.main()
