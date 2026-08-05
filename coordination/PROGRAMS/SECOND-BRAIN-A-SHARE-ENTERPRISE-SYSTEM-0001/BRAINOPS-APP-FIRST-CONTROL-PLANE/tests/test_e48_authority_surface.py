"""Product-facing validation that rejects E47's forbidden parallel pattern."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from brainops_control_plane.authority_surface import (  # noqa: E402
    AuthoritySurfaceCode,
    validate_single_positive_authority,
)


class E48AuthoritySurfaceTests(unittest.TestCase):
    def test_actual_package_has_one_positive_authority_chain(self):
        result = validate_single_positive_authority(PROGRAM_ROOT)
        self.assertEqual(result.code, AuthoritySurfaceCode.READY)

    def test_parallel_caller_mintable_lifecycle_fixture_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "src" / "brainops_control_plane"
            package.mkdir(parents=True)
            (package / "durable_authority.py").write_text("class DurableClaimAuthority: pass\n", encoding="utf-8")
            (package / "execution_lease.py").write_text("class DurableExecutionLeaseAuthority: pass\n", encoding="utf-8")
            (package / "recoverable_lifecycle.py").write_text(
                "class LifecycleBinding: pass\nclass RecoverableLifecycleAuthority: pass\n",
                encoding="utf-8",
            )
            result = validate_single_positive_authority(root)

        self.assertEqual(result.code, AuthoritySurfaceCode.CALLER_MINTABLE_LIFECYCLE)
        self.assertTrue(any("recoverable_lifecycle.py" in value for value in result.violations))

    def test_missing_actual_claim_mutation_fixture_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "src" / "brainops_control_plane"
            package.mkdir(parents=True)
            (package / "durable_authority.py").write_text(
                "class DurableClaimAuthority: pass\n", encoding="utf-8"
            )
            (package / "execution_lease.py").write_text(
                "class DurableExecutionLeaseAuthority: pass\n",
                encoding="utf-8",
            )
            result = validate_single_positive_authority(root)

        self.assertEqual(result.code, AuthoritySurfaceCode.ACTUAL_CLAIM_MUTATION_MISSING)
