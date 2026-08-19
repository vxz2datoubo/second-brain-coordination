from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import provider_runner  # noqa: E402


class ProviderArtifactToolTests(unittest.TestCase):
    def test_canonical_payload_excludes_environment_specific_mutation_results(self) -> None:
        payload = provider_runner.canonical_payload()
        self.assertEqual(payload["schema"], "e55-provider-canonical-v1")
        self.assertNotIn("mutation_result_sha256", payload)
        self.assertNotIn("mutation_count", payload)

    def test_parallel_downloaded_artifact_directories_are_compared(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e55-artifacts-") as temporary:
            root = Path(temporary) / "provider-artifacts"
            for version in ("3.11", "3.13"):
                for seed in ("0", "1", "777"):
                    canonical = root / f"canonical-py{version}-seed{seed}"
                    environment = root / f"environment-py{version}-seed{seed}"
                    canonical.mkdir(parents=True)
                    environment.mkdir(parents=True)
                    (canonical / "canonical.json").write_text(json.dumps({"version": version, "seed": seed}), encoding="utf-8")
                    (environment / "environment.json").write_text(json.dumps({"head": "candidate", "version": version, "seed": seed}), encoding="utf-8")
            output = Path(temporary) / "compare.json"
            run = subprocess.run([sys.executable, str(ROOT / "tools" / "compare_provider_artifacts.py"), "--root", str(root), "--output", str(output)], capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            body = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(body["artifacts"]), 12)
            self.assertEqual(len(body["artifact_digests"]), 12)


if __name__ == "__main__":
    unittest.main()
