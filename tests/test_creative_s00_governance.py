from __future__ import annotations

from pathlib import Path
import unittest

from creative_runtime.governance import GovernanceViolation, load_task_governance


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "coordination" / "PROGRAMS" / "CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001" / "AUTHORIZED-PATH-MANIFEST.json"


class CreativeS00GovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.governance = load_task_governance(str(POLICY))

    def test_authorized_task_paths_are_accepted(self) -> None:
        self.governance.require_allowed_write_paths(
            [
                "creative_runtime/ledger.py",
                "apps/cli/creativectl.py",
                "tests/test_creative_ledger.py",
                "coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/AI_HANDOFF.yaml",
            ]
        )

    def test_control_plane_and_unapproved_paths_are_rejected(self) -> None:
        with self.assertRaises(GovernanceViolation):
            self.governance.require_allowed_write_paths(
                ["coordination/ACTIVE-CODEX-TASK.yaml", "brain_core/service.py"]
            )

    def test_authority_declaration_must_be_complete_and_exact(self) -> None:
        self.governance.require_authority_declaration(
            self.governance.authority_invariants
        )
        with self.assertRaises(GovernanceViolation):
            self.governance.require_authority_declaration(
                {
                    **self.governance.authority_invariants,
                    "generation_execution": "external_paid_allowed",
                }
            )

    def test_authority_declaration_cannot_omit_knowledge_boundary(self) -> None:
        declaration = dict(self.governance.authority_invariants)
        declaration.pop("knowledge_write")
        with self.assertRaises(GovernanceViolation):
            self.governance.require_authority_declaration(declaration)


if __name__ == "__main__":
    unittest.main()
