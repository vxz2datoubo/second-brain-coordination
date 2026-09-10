from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1] / "src"
sys.path.insert(0, str(ROOT))
from w4_experiment_family.registry import RegistryError, digest, open_store, registered_family_digest_v1

DS10_FIXTURE = Path(__file__).parents[2] / "DS10-RESEARCH-INTEGRITY-P0A" / "fixtures" / "research-integrity.synthetic.yaml"


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class W4RegistryTests(unittest.TestCase):
    def setUp(self):
        self.store = open_store(); self.f = "family"; self.r = "rev-1"; self.seq = 0; self.head = None
        self.append("FAMILY_CREATED", self.family())

    def family(self, **more):
        value = {"experiment_family_ref": f"{self.f}@{self.r}", "benchmark_ref": "BENCHMARK", "metric_id": "METRIC", "horizon_id": "HORIZON", "search_space_ref": "SEARCH"}
        value.update(more); return value

    def trial(self, trial_id: str, **more):
        value = {"trial_id": trial_id, "immutable_digest": h("trial-" + trial_id), "selection_affecting": True, "parameter_manifest_ref": "params@1", "feature_manifest_ref": "features@1", "dataset_snapshot_refs": ["dataset@1"], "code_version_refs": ["code@1"], "rule_snapshot_refs": ["rules@1"], "seed_or_randomness_ref": "seed@1", "strategy_definition_ref": "strategy@1", "cost_model_ref": "cost@1", "search_space_ref": "search@1", "metric_result_ref": None}
        value.update(more); return value

    def append(self, typ, payload, **kwargs):
        out = self.store.append(family_id=self.f, family_revision_id=self.r, expected_sequence=kwargs.pop("sequence", self.seq), expected_previous_digest=kwargs.pop("head", self.head), event_id=kwargs.pop("event_id", f"event-{self.seq + 1}"), idempotency_key=kwargs.pop("idempotency_key", f"idem-{self.seq + 1}"), event_type=typ, payload=payload)
        if not out["duplicate"]: self.seq = out["sequence"]; self.head = out["event_digest"]
        return out

    def freeze_ready(self, ids=("A", "B")):
        trials = {trial_id: self.trial(trial_id) for trial_id in ids}
        for value in trials.values(): self.append("TRIAL_REGISTERED", value)
        self.append("SELECTION_RULE_REGISTERED", {"selection_rule_ref": "SELECT"})
        expected = {key: value["immutable_digest"] for key, value in trials.items()}
        registered = registered_family_digest_v1(experiment_family_ref=f"{self.f}@{self.r}", expected_trial_digests=expected, benchmark_ref="BENCHMARK", metric_id="METRIC", horizon_id="HORIZON", search_space_ref="SEARCH", selection_rule_ref="SELECT")
        self.append("FAMILY_FROZEN", {"expected_trial_digests": expected, "registered_family_digest": registered})

    def terminate_all(self, rows):
        for trial, status in rows:
            self.append("TRIAL_STARTED", {"trial_id": trial})
            payload = {"trial_id": trial, "status": status, "configuration_digest": h("config" + trial)}
            if status == "NUMERICAL_ERROR": payload["failure_class"] = "NUMERICAL_ERROR"
            self.append("TRIAL_TERMINATED", payload)

    def test_full_object_schema_is_enforced_and_read_surface_is_closed(self):
        with self.assertRaisesRegex(RegistryError, "SCHEMA_ADDITIONAL_PROPERTY"):
            self.append("TRIAL_REGISTERED", self.trial("bad", invented="no"))
        with self.assertRaisesRegex(RegistryError, "SCHEMA_PATTERN_INVALID"):
            self.append("TRIAL_REGISTERED", self.trial("bad2", immutable_digest="bad"))
        self.freeze_ready(); self.terminate_all((("A", "SUCCESS"), ("B", "FAILURE")))
        snap = self.store.read_experiment_family("family@rev-1")
        self.assertEqual("ExperimentFamilySnapshot/v1", snap["schema"])
        self.assertTrue(all(value is False for value in snap["authority"].values()))

    def test_status_mapping_is_single_and_unknown_fails_closed(self):
        self.append("TRIAL_REGISTERED", self.trial("A")); self.append("TRIAL_STARTED", {"trial_id": "A"})
        self.append("TRIAL_TERMINATED", {"trial_id": "A", "status": "NUMERICAL_ERROR", "configuration_digest": h("a"), "failure_class": "NUMERICAL_ERROR"})
        self.assertEqual("ERROR", self.store.reduce_family_snapshot(self.f, self.r)["trials"][0]["status"])
        self.append("TRIAL_REGISTERED", self.trial("B")); self.append("TRIAL_STARTED", {"trial_id": "B"})
        with self.assertRaisesRegex(RegistryError, "INVALID_TRIAL_STATUS"):
            self.append("TRIAL_TERMINATED", {"trial_id": "B", "status": "SUPERSEDED_BY_NEW_FAMILY_REVISION", "configuration_digest": h("b")})

    def test_rerun_collision_and_terminal_one_shot(self):
        self.append("TRIAL_REGISTERED", self.trial("A")); self.append("TRIAL_STARTED", {"trial_id": "A"})
        self.append("TRIAL_TERMINATED", {"trial_id": "A", "status": "SUCCESS", "configuration_digest": h("a")})
        with self.assertRaisesRegex(RegistryError, "TRIAL_ALREADY_TERMINAL"):
            self.append("TRIAL_TERMINATED", {"trial_id": "A", "status": "FAILED", "configuration_digest": h("again")})
        with self.assertRaisesRegex(RegistryError, "TRIAL_ID_COLLISION"):
            self.append("RERUN_REGISTERED", {"trial_id": "A", "rerun_of": "A", "immutable_digest": h("trial-A"), "selection_affecting": False})

    def test_manifest_is_complete_not_winner_only_and_includes_all_outcomes(self):
        self.freeze_ready(("winner", "loser", "aborted", "numerical", "precheck"))
        self.terminate_all((("winner", "SUCCESS"), ("loser", "FAILED"), ("aborted", "ABORTED"), ("numerical", "NUMERICAL_ERROR"), ("precheck", "REJECTED_BY_PRECHECK")))
        self.append("CANDIDATE_FROZEN", {}); self.append("TRIAL_SELECTED", {"trial_id": "winner"})
        snap = self.store.reduce_family_snapshot(self.f, self.r)
        self.assertEqual(5, snap["economic_trial_count"]); self.assertEqual(5, len(snap["trials"])); self.assertEqual("COMPLETE", snap["completeness_state"])
        self.assertEqual({"SUCCESS": 1, "FAILURE": 1, "ABORTED": 2, "ERROR": 1}, snap["status_counts"])

    def test_incomplete_provenance_is_retained_and_legacy_is_never_clean(self):
        incomplete = self.trial("missing", dataset_snapshot_refs=[])
        self.append("TRIAL_REGISTERED", incomplete)
        self.assertEqual("INCOMPLETE", self.store.reduce_family_snapshot(self.f, self.r)["trials"][0]["provenance_state"])
        other = open_store(); other.append(family_id="legacy", family_revision_id="r1", expected_sequence=0, expected_previous_digest=None, event_id="one", idempotency_key="one", event_type="FAMILY_CREATED", payload={"experiment_family_ref": "legacy@r1", "benchmark_ref": "b", "metric_id": "m", "horizon_id": "h", "search_space_ref": "s"})
        other.append(family_id="legacy", family_revision_id="r1", expected_sequence=1, expected_previous_digest=other.read_family_event_stream("legacy", "r1")[-1]["event_digest"], event_id="two", idempotency_key="two", event_type="LEGACY_INCOMPLETE_REGISTERED", payload=self.trial("legacy"))
        self.assertEqual("LEGACY_INCOMPLETE_PROVENANCE", other.reduce_family_snapshot("legacy", "r1")["completeness_state"])

    def test_freeze_requires_new_revision_for_changed_definition_and_preserves_old(self):
        self.freeze_ready(); self.terminate_all((("A", "SUCCESS"), ("B", "FAILURE")))
        with self.assertRaisesRegex(RegistryError, "SELECTION_RULE_IMMUTABLE"):
            self.append("SELECTION_RULE_REGISTERED", {"selection_rule_ref": "CHANGED"})
        with self.assertRaisesRegex(RegistryError, "FAMILY_FROZEN_NO_NEW_TRIAL"):
            self.append("TRIAL_REGISTERED", self.trial("outcome-inspected"))
        self.assertTrue(self.store.verify_event_chain(self.f, self.r))
        self.assertRaises(RegistryError, self.store.read_experiment_family, "family@rev-2")

    def test_snapshot_digest_is_order_independent_and_semantic_changes_are_not(self):
        self.freeze_ready(); self.terminate_all((("A", "SUCCESS"), ("B", "FAILURE")))
        first = self.store.reduce_family_snapshot(self.f, self.r)
        reordered = dict(first); reordered["trials"] = list(reversed(first["trials"])); reordered.pop("snapshot_digest"); reordered.pop("family_snapshot_digest")
        normalized = dict(reordered); normalized["trials"] = sorted(reordered["trials"], key=lambda value: value["trial_id"])
        self.assertEqual(first["snapshot_digest"], digest(normalized))
        changed = dict(normalized); changed["selected_trial_id"] = "B"; self.assertNotEqual(first["snapshot_digest"], digest(changed))

    def test_authority_attack_and_caller_minted_digest_fail_closed(self):
        attacker = open_store()
        with self.assertRaisesRegex(RegistryError, "SCHEMA_"):
            attacker.append(family_id="attack", family_revision_id="r1", expected_sequence=0, expected_previous_digest=None, event_id="a", idempotency_key="a", event_type="FAMILY_CREATED", payload=self.family(authority={"w4_strategy_experiment_write_authority": True}))
        with self.assertRaisesRegex(RegistryError, "SCHEMA_PATTERN_INVALID"):
            self.append("TRIAL_REGISTERED", self.trial("attacker", immutable_digest="caller-declared-canonical"))

    def test_golden_vector_is_derived_from_ds10_owned_fixture(self):
        # DS-10 fixture provenance: read-only path above; blob identity is recorded in R189 receipt.
        text = DS10_FIXTURE.read_text(encoding="utf-8")
        self.assertIn("complete_family:", text)
        complete_family = text.split("  complete_family:", 1)[1].split("\n  trial_count_laundering_attempt:", 1)[0]
        expected = dict(re.findall(r"^      (t[0-9]+): \"([0-9a-f]{64})\"$", complete_family, re.MULTILINE))
        self.assertEqual({"t1", "t2", "t3"}, set(expected))
        ds10_path = Path(__file__).parents[2] / "DS10-RESEARCH-INTEGRITY-P0A" / "src" / "offline_research" / "research_integrity.py"
        module_name = "ds10_research_integrity"
        spec = importlib.util.spec_from_file_location(module_name, ds10_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        ds10 = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = ds10
        spec.loader.exec_module(ds10)
        experiment_family_ref = "w4:synthetic:complete"
        benchmark_ref = "BENCHMARK.ZERO_SKILL.V1"
        metric_id = "SHARPE_OBSERVATION_FREQUENCY_V1"
        horizon_id = "HORIZON.DAILY.20D.V1"
        search_space_ref = "SEARCHSPACE.DS10_DERIVED"
        selection_rule_ref = "SELECT.DS10_DERIVED"
        material = {"experiment_family_ref": experiment_family_ref, "expected_trial_digests": dict(sorted(expected.items())), "benchmark_ref": benchmark_ref, "metric_id": metric_id, "horizon_id": horizon_id, "search_space_ref": search_space_ref, "selection_rule_ref": selection_rule_ref}
        value = registered_family_digest_v1(experiment_family_ref=experiment_family_ref, expected_trial_digests=expected, benchmark_ref=benchmark_ref, metric_id=metric_id, horizon_id=horizon_id, search_space_ref=search_space_ref, selection_rule_ref=selection_rule_ref)
        self.assertEqual(ds10._digest(material), value)
        self.assertEqual(value, registered_family_digest_v1(experiment_family_ref="w4:synthetic:complete", expected_trial_digests=dict(reversed(list(expected.items()))), benchmark_ref="BENCHMARK.ZERO_SKILL.V1", metric_id="SHARPE_OBSERVATION_FREQUENCY_V1", horizon_id="HORIZON.DAILY.20D.V1", search_space_ref="SEARCHSPACE.DS10_DERIVED", selection_rule_ref="SELECT.DS10_DERIVED"))


if __name__ == "__main__": unittest.main()
