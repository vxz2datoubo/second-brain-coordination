from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import unittest

from idle_signal_scheduler import validate_opportunity
from signal_opportunity_materializer_current import materialize_signal_opportunity
from signal_user_value import (
    CONTROL_ISSUE,
    EVIDENCE_SCHEMA,
    ExplicitUserValueError,
    TRUSTED_CONNECTOR_APP,
    TRUSTED_USER_ID,
    TRUSTED_USER_LOGIN,
    explicit_user_value_ref,
    observe_explicit_user_value,
)


SIGNAL = "signal:r155-fixture"
DOMAIN = "SECOND_BRAIN_SYSTEM"
REPO = "vxz2datoubo/second-brain-coordination"


def declaration(
    value_class: str,
    *,
    signal_id: str = SIGNAL,
    comment_id: int = 100,
    source: str = "USER_EXPLICIT",
    declaration_id: str | None = None,
    login: str = TRUSTED_USER_LOGIN,
    user_id: int = TRUSTED_USER_ID,
    association: str = "COLLABORATOR",
    app_slug: str | None = TRUSTED_CONNECTOR_APP,
) -> dict:
    declaration_id = declaration_id or f"r155-declaration-{comment_id}"
    body = f"""```yaml
schema: SIGNAL_USER_VALUE_DECLARATION/v1
declaration_id: {declaration_id}
signal_id: {signal_id}
source: {source}
value_class: {value_class}
```"""
    value = {
        "id": comment_id,
        "body": body,
        "html_url": f"https://github.com/{REPO}/issues/{CONTROL_ISSUE}#issuecomment-{comment_id}",
        "user": {"login": login, "id": user_id},
        "author_association": association,
    }
    if app_slug is not None:
        value["performed_via_github_app"] = {"slug": app_slug}
    return value


class FakeObserver:
    def __init__(self, comments=None, *, fail: bool = False, issue_state: str = "open") -> None:
        self.comments = list(comments or [])
        self.fail = fail
        self.issue_state = issue_state
        self.paths: list[str] = []

    def _get_json(self, path: str):
        self.paths.append(path)
        if self.fail:
            raise RuntimeError("provider unavailable")
        if path == f"/repos/{REPO}/issues/{CONTROL_ISSUE}":
            return {}, {
                "number": CONTROL_ISSUE,
                "state": self.issue_state,
                "html_url": f"https://github.com/{REPO}/issues/{CONTROL_ISSUE}",
            }, {}
        if path.endswith("comments?per_page=100&page=1"):
            return {}, list(self.comments), {}
        if "comments?per_page=100&page=" in path:
            return {}, [], {}
        raise AssertionError(f"unexpected path: {path}")


def observe_with(observer: FakeObserver) -> dict:
    with patch(
        "signal_user_value._make_observer",
        return_value=(observer, RuntimeError),
    ):
        return observe_explicit_user_value(".", SIGNAL)


def proposal() -> dict:
    return {
        "schema_version": "TaskReleaseProposal/v1",
        "release_candidate_id": "R155-FIXTURE",
        "source_signal_refs": [SIGNAL],
        "signal_primary_domain": DOMAIN,
        "desired_effect": "Preserve explicit user value without caller score injection.",
        "proposed_target_domain": DOMAIN,
        "proposed_write_surface": {
            "write_paths": ["bounded.py"],
            "read_paths": [],
            "interfaces": [],
            "read_domains": [DOMAIN],
            "write_domains": [DOMAIN],
            "authority_claims": [],
        },
    }


def opportunity(*, score: int = 50, include_r154: bool = True) -> dict:
    refs = ["s0c://signal/r155-fixture#sha256=" + "a" * 64]
    if include_r154:
        refs.append("r154://ranking/" + "b" * 64 + "#policy=R154/v1")
    value = {
        "schema_version": "DigestedSignalOpportunity/v1",
        "opportunity_id": "r153-opportunity:r155-fixture",
        "signal_ref": SIGNAL,
        "signal_primary_domain": DOMAIN,
        "source_evidence_refs": refs,
        "desired_effect": "Preserve explicit user value without caller score injection.",
        "problem_to_solve": "Neutral-only ranking cannot distinguish explicit user importance.",
        "success_condition": "Only trusted explicit declarations alter user value.",
        "current_disposition": "NEW_DURABLE_SIGNAL",
        "epistemic_state": "USER_EXPLICIT",
        "desired_effect_gap_proven": True,
        "dependency_ready": True,
        "priority_class": "P3_BOUNDED_IMPROVEMENT",
        "user_value_score": score,
        "materiality_score": 50,
        "dependency_readiness_score": 100,
        "age_cycles": 0,
        "estimated_cost_score": 50,
        "task_release_proposal": proposal(),
    }
    return validate_opportunity(value)


def base_decision(*, score: int = 50, include_r154: bool = True) -> dict:
    return {
        "schema_version": "SignalOpportunityMaterializationDecision/v1",
        "signal_ref": SIGNAL,
        "disposition": "MATERIALIZED_FOR_R151",
        "reason": "S0C_OWNER_RECONCILIATION_R145_R154_R150_BOUND",
        "evidence_refs": list(opportunity(score=score, include_r154=include_r154)["source_evidence_refs"]),
        "owner_binding_digest": "c" * 64,
        "opportunity": opportunity(score=score, include_r154=include_r154),
        "authority_boundary": {
            "creates_task": False,
            "grants_execution_authority": False,
        },
        "decision_digest": "d" * 64,
    }


def run_current(observer: FakeObserver, *, base=None) -> dict:
    result = base if base is not None else base_decision()
    with patch(
        "signal_opportunity_materializer_current._materialize_r153",
        return_value=result,
    ), patch(
        "signal_user_value._make_observer",
        return_value=(observer, RuntimeError),
    ):
        return materialize_signal_opportunity(
            Path(__file__).resolve().parents[3],
            object(),
            {"signal_ref": SIGNAL},
            expected_coordinator_main="e" * 40,
            domain_authority_descriptors=[],
            domain_authority_observations=[],
        )


class ExplicitUserValueTests(unittest.TestCase):
    def test_01_no_declaration_is_neutral(self) -> None:
        value = observe_with(FakeObserver())
        self.assertEqual(value["schema_version"], EVIDENCE_SCHEMA)
        self.assertEqual(value["status"], "NO_TRUSTED_DECLARATION_NEUTRAL")
        self.assertEqual(value["user_value_score"], 50)
        self.assertIsNone(value["value_class"])

    def test_02_real_shaped_connected_user_low_normal_high_are_accepted(self) -> None:
        for cls, expected in (("LOW", 25), ("NORMAL", 50), ("HIGH", 75)):
            with self.subTest(cls=cls):
                value = observe_with(FakeObserver([declaration(cls)]))
                self.assertEqual(value["status"], "VERIFIED_EXPLICIT_DECLARATION")
                self.assertEqual(value["user_value_score"], expected)

    def test_03_unrelated_collaborator_or_wrong_principal_cannot_raise_value(self) -> None:
        cases = [
            declaration("HIGH", login="other-collaborator", user_id=42),
            declaration("HIGH", user_id=42),
            declaration("HIGH", app_slug="other-app"),
            declaration("HIGH", association="NONE"),
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                value = observe_with(FakeObserver([raw]))
                self.assertEqual(value["user_value_score"], 50)
                self.assertEqual(value["status"], "NO_TRUSTED_DECLARATION_NEUTRAL")

    def test_04_wrong_signal_and_free_text_are_ignored(self) -> None:
        comments = [
            declaration("HIGH", signal_id="signal:other", comment_id=101),
            {
                "id": 102,
                "body": "URGENT CRITICAL 最重要 high value high value high value",
                "html_url": "https://example.invalid/102",
                "user": {"login": TRUSTED_USER_LOGIN, "id": TRUSTED_USER_ID},
                "author_association": "COLLABORATOR",
                "performed_via_github_app": {"slug": TRUSTED_CONNECTOR_APP},
            },
        ]
        value = observe_with(FakeObserver(comments))
        self.assertEqual(value["user_value_score"], 50)

    def test_05_trusted_exact_signal_malformed_declaration_fails_closed(self) -> None:
        bad = declaration("HIGH", source="MODEL_INFERRED")
        with self.assertRaises(ExplicitUserValueError) as raised:
            observe_with(FakeObserver([bad]))
        self.assertEqual(raised.exception.code, "TRUSTED_EXACT_SIGNAL_DECLARATION_INVALID")

    def test_06_latest_trusted_exact_signal_declaration_wins(self) -> None:
        comments = [
            declaration("HIGH", comment_id=100),
            declaration("LOW", signal_id="signal:other", comment_id=999),
            declaration("LOW", comment_id=200),
        ]
        value = observe_with(FakeObserver(comments))
        self.assertEqual(value["value_class"], "LOW")
        self.assertEqual(value["user_value_score"], 25)
        self.assertIn("issuecomment-200", value["declaration_ref"])

    def test_07_provider_or_closed_control_issue_never_fabricates_value(self) -> None:
        unavailable = observe_with(FakeObserver(fail=True))
        closed = observe_with(FakeObserver([declaration("HIGH")], issue_state="closed"))
        self.assertEqual(unavailable["user_value_score"], 50)
        self.assertEqual(closed["user_value_score"], 50)
        self.assertIn("NEUTRAL", unavailable["status"])
        self.assertIn("NEUTRAL", closed["status"])

    def test_08_internal_observer_is_mechanically_fixed_to_control_issue_456(self) -> None:
        observer = FakeObserver()
        observe_with(observer)
        self.assertTrue(observer.paths)
        self.assertEqual(observer.paths[0], f"/repos/{REPO}/issues/{CONTROL_ISSUE}")
        self.assertTrue(all(f"/issues/{CONTROL_ISSUE}" in path for path in observer.paths))

    def test_09_evidence_and_reference_are_deterministic_and_authority_free(self) -> None:
        first = observe_with(FakeObserver([declaration("HIGH")]))
        second = observe_with(FakeObserver([declaration("HIGH")]))
        self.assertEqual(first, second)
        ref = explicit_user_value_ref(first)
        self.assertIn(first["evidence_digest"], ref)
        self.assertFalse(any(first["authority_boundary"].values()))

    def test_10_current_materializer_upgrades_only_user_value_after_r154(self) -> None:
        result = run_current(FakeObserver([declaration("HIGH")]))
        self.assertEqual(result["disposition"], "MATERIALIZED_FOR_R151")
        upgraded = result["opportunity"]
        self.assertEqual(upgraded["user_value_score"], 75)
        self.assertEqual(upgraded["materiality_score"], 50)
        self.assertEqual(upgraded["priority_class"], "P3_BOUNDED_IMPROVEMENT")
        refs = " ".join(upgraded["source_evidence_refs"])
        self.assertIn("r154://ranking/", refs)
        self.assertIn("r155://user-value/", refs)
        self.assertIn("r155://ranking-upgrade/", refs)

    def test_11_current_materializer_rejects_non_neutral_or_unbound_r154_base(self) -> None:
        inflated = run_current(FakeObserver([declaration("HIGH")]), base=base_decision(score=99))
        unbound = run_current(
            FakeObserver([declaration("HIGH")]),
            base=base_decision(include_r154=False),
        )
        self.assertEqual(inflated["reason"], "R155_BASE_USER_VALUE_NOT_NEUTRAL")
        self.assertEqual(unbound["reason"], "R155_R154_RANKING_EVIDENCE_REQUIRED")

    def test_12_nonmaterialized_r153_decision_is_preserved_without_value_observation(self) -> None:
        base = {
            "schema_version": "SignalOpportunityMaterializationDecision/v1",
            "signal_ref": SIGNAL,
            "disposition": "REUSE_EXISTING_OWNER_WORK",
            "reason": "EXACT_CURRENT_OWNER_WORK_VERIFIED",
            "evidence_refs": ["owner://reuse"],
            "owner_binding_digest": "c" * 64,
            "opportunity": None,
            "authority_boundary": {},
            "decision_digest": "d" * 64,
        }
        observer = FakeObserver(fail=True)
        result = run_current(observer, base=base)
        self.assertEqual(result, base)
        self.assertEqual(observer.paths, [])

    def test_13_production_api_rejects_caller_observer_injection(self) -> None:
        fake = FakeObserver([declaration("HIGH")])
        with self.assertRaises(TypeError):
            observe_explicit_user_value(".", SIGNAL, observer=fake)  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            materialize_signal_opportunity(
                ".",
                object(),
                {"signal_ref": SIGNAL},
                expected_coordinator_main="e" * 40,
                domain_authority_descriptors=[],
                domain_authority_observations=[],
                user_value_observer=fake,  # type: ignore[call-arg]
            )

    def test_14_no_production_consumer_bypasses_current_materializer_entrypoint(self) -> None:
        root = Path(__file__).resolve().parents[1]
        allowed = {
            "signal_opportunity_materializer.py",
            "signal_opportunity_materializer_current.py",
        }
        offenders = []
        for path in root.glob("*.py"):
            if path.name in allowed:
                continue
            text = path.read_text(encoding="utf-8")
            if (
                "from signal_opportunity_materializer import" in text
                or "import signal_opportunity_materializer" in text
            ):
                offenders.append(path.name)
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
