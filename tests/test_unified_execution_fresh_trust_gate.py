import dataclasses
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "coordination"
    / "GOVERNANCE"
    / "unified_execution_trust_gate.py"
)
spec = importlib.util.spec_from_file_location(
    "unified_execution_trust_gate", MODULE_PATH
)
gate = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)
base = gate.base

MAIN = "a" * 40


def _authority(payload=None):
    material = payload or {
        "canonical_main_sha": MAIN,
        "marker": "canonical",
    }
    return base.VerifiedCanonicalAuthority(
        base._freeze(material), base._ISSUER
    )


def _release(payload=None):
    material = payload or {
        "canonical_main_sha": MAIN,
        "release_ref": "coordination/RELEASES/TASK.yaml",
        "marker": "canonical",
    }
    return base.VerifiedReleaseWitness(
        base._freeze(material), base._ISSUER
    )


class CallerMintingAttackTests(unittest.TestCase):
    def test_direct_verified_authority_constructor_cannot_mint_authority(self):
        legit = _authority()
        forged = base.VerifiedCanonicalAuthority(
            base._freeze(
                {"canonical_main_sha": MAIN, "marker": "forged"}
            ),
            base._ISSUER,
        )
        with patch.object(
            gate, "_fresh_canonical_authority", return_value=legit
        ):
            with self.assertRaises(base.ExecutionContractError):
                gate.validate_canonical_authority(".", forged)

    def test_internal_authority_factory_cannot_mint_authority(self):
        legit = _authority()
        forged = base._issue_authority(
            {"canonical_main_sha": MAIN, "marker": "forged"}
        )
        with patch.object(
            gate, "_fresh_canonical_authority", return_value=legit
        ):
            with self.assertRaises(base.ExecutionContractError):
                gate.validate_canonical_authority(".", forged)

    def test_dataclasses_replace_cannot_clone_authority_with_forged_payload(self):
        legit = _authority()
        forged = dataclasses.replace(
            legit,
            _payload=base._freeze(
                {"canonical_main_sha": MAIN, "marker": "forged"}
            ),
        )
        with patch.object(
            gate, "_fresh_canonical_authority", return_value=legit
        ):
            with self.assertRaises(base.ExecutionContractError):
                gate.validate_canonical_authority(".", forged)

    def test_release_direct_constructor_cannot_mint_release_authority(self):
        legit = _release()
        forged = base.VerifiedReleaseWitness(
            base._freeze(
                {
                    "canonical_main_sha": MAIN,
                    "release_ref": "coordination/RELEASES/TASK.yaml",
                    "marker": "forged",
                }
            ),
            base._ISSUER,
        )
        with patch.object(
            gate, "_fresh_release_witness", return_value=legit
        ):
            with self.assertRaises(base.ExecutionContractError):
                gate.validate_release_witness(
                    ".", "coordination/RELEASES/TASK.yaml", forged
                )

    def test_release_dataclasses_replace_cannot_preserve_trust(self):
        legit = _release()
        forged = dataclasses.replace(
            legit,
            _payload=base._freeze(
                {
                    "canonical_main_sha": MAIN,
                    "release_ref": "coordination/RELEASES/TASK.yaml",
                    "marker": "forged",
                }
            ),
        )
        with patch.object(
            gate, "_fresh_release_witness", return_value=legit
        ):
            with self.assertRaises(base.ExecutionContractError):
                gate.validate_release_witness(
                    ".", "coordination/RELEASES/TASK.yaml", forged
                )

    def test_process_start_uses_fresh_snapshot_not_caller_object_identity(self):
        fresh = _authority()
        claimed = dataclasses.replace(fresh)
        admission = {"admission": "candidate"}
        dispatch = {"dispatch": "candidate"}

        with patch.object(
            gate, "_fresh_canonical_authority", return_value=fresh
        ), patch.object(base, "validate_local_admission") as validate:
            returned = gate.validate_process_start(
                ".", admission, dispatch, claimed
            )

        self.assertIs(returned, fresh)
        validate.assert_called_once_with(admission, dispatch, fresh)


class FreshReadbackHardeningTests(unittest.TestCase):
    def test_terminal_remote_head_recheck_fails_when_main_moves(self):
        moved = "b" * 40
        with patch.object(
            base,
            "_run_git",
            return_value=f"{moved}\trefs/heads/main",
        ):
            with self.assertRaises(base.ExecutionContractError):
                gate._terminal_remote_main_recheck(".", MAIN)

    def test_fresh_authority_rechecks_after_adapter_validation(self):
        fresh = _authority()
        events = []

        with patch.object(
            base,
            "build_verified_canonical_authority",
            side_effect=lambda _repo: events.append("build") or fresh,
        ), patch.object(
            base,
            "validate_canonical_authority",
            side_effect=lambda _snapshot: events.append("structure"),
        ), patch.object(
            gate,
            "_revalidate_project_adapter_at_sha",
            side_effect=lambda _repo, _mapping: events.append("adapter"),
        ), patch.object(
            gate,
            "_terminal_remote_main_recheck",
            side_effect=lambda _repo, _sha: events.append("terminal"),
        ):
            result = gate._fresh_canonical_authority(".")

        self.assertIs(result, fresh)
        self.assertEqual(
            events, ["build", "structure", "adapter", "terminal"]
        )

    def test_runtime_project_projection_rejects_semantic_floor_downgrade(self):
        documents = {}
        for path in base.PROJECT_ADAPTER_PATHS:
            text = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("TRADING-SYSTEM.yaml"):
                text = text.replace(
                    'order_authority: "SEPARATE_EXPLICIT_OWNER_GATE"',
                    'order_authority: "GENERIC_ENGINEERING_ROUTE"',
                )
            documents[path] = text

        canonical = {
            "canonical_main_sha": MAIN,
            "project_id": "TRADING_SYSTEM",
            "execution_repository": "vxz2datoubo/second-brain-coordination",
        }

        with patch.object(
            gate,
            "_read_at_sha",
            side_effect=lambda _repo, _sha, path: documents[path],
        ):
            with self.assertRaises(base.ExecutionContractError):
                gate._revalidate_project_adapter_at_sha(".", canonical)


class CarrierHandoffFreshGateTests(unittest.TestCase):
    def test_handoff_substitutes_fresh_release_and_new_authority(self):
        claimed_new = _authority(
            {"canonical_main_sha": MAIN, "marker": "claimed-new"}
        )
        fresh_new = _authority(
            {"canonical_main_sha": MAIN, "marker": "fresh-new"}
        )
        claimed_release = _release(
            {
                "canonical_main_sha": MAIN,
                "release_ref": "coordination/RELEASES/TASK.yaml",
                "marker": "claimed-release",
            }
        )
        fresh_release = _release(
            {
                "canonical_main_sha": MAIN,
                "release_ref": "coordination/RELEASES/TASK.yaml",
                "marker": "fresh-release",
            }
        )
        old = _authority(
            {"canonical_main_sha": "0" * 40, "marker": "old"}
        )

        with patch.object(
            gate, "validate_local_admission", return_value=fresh_new
        ), patch.object(
            gate, "validate_release_witness", return_value=fresh_release
        ), patch.object(base, "validate_carrier_handoff") as validate:
            gate.validate_carrier_handoff(
                ".",
                "coordination/RELEASES/TASK.yaml",
                {"handoff": True},
                {"old_dispatch": True},
                old,
                claimed_release,
                {"new_dispatch": True},
                {"new_admission": True},
                claimed_new,
            )

        args = validate.call_args.args
        self.assertIs(args[3], fresh_release)
        self.assertIs(args[6], fresh_new)


if __name__ == "__main__":
    unittest.main()
