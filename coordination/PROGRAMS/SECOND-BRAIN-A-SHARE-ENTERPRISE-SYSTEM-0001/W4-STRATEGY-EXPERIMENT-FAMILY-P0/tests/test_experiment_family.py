import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1] / "src"
sys.path.insert(0, str(ROOT))
from w4_experiment_family.registry import RegistryError, open_store, registered_family_digest_v1

def h(value): return hashlib.sha256(value.encode()).hexdigest()

class W4RegistryTests(unittest.TestCase):
    def setUp(self):
        self.store = open_store(); self.f="family"; self.r="rev-1"; self.seq=0; self.head=None
        self.a, self.b = h("trial-A"), h("trial-B")
        self.append("FAMILY_CREATED", {"experiment_family_ref":"family@rev-1","benchmark_ref":"BENCHMARK","metric_id":"METRIC","horizon_id":"HORIZON","search_space_ref":"SEARCH"})
    def append(self, typ, payload, **kwargs):
        out=self.store.append(family_id=self.f,family_revision_id=self.r,expected_sequence=kwargs.pop("sequence",self.seq),expected_previous_digest=kwargs.pop("head",self.head),event_id=kwargs.pop("event_id",f"event-{self.seq+1}"),idempotency_key=kwargs.pop("idempotency_key",f"idem-{self.seq+1}"),event_type=typ,payload=payload)
        if not out["duplicate"]: self.seq=out["sequence"]; self.head=out["event_digest"]
        return out
    def freeze_ready(self):
        self.append("TRIAL_REGISTERED", {"trial_id":"A","immutable_digest":self.a,"selection_affecting":True})
        self.append("TRIAL_REGISTERED", {"trial_id":"B","immutable_digest":self.b,"selection_affecting":True})
        self.append("SELECTION_RULE_REGISTERED", {"selection_rule_ref":"SELECT"})
        d=registered_family_digest_v1(experiment_family_ref="family@rev-1", expected_trial_digests={"A":self.a,"B":self.b}, benchmark_ref="BENCHMARK",metric_id="METRIC",horizon_id="HORIZON",search_space_ref="SEARCH",selection_rule_ref="SELECT")
        self.append("FAMILY_FROZEN", {"expected_trial_digests":{"A":self.a,"B":self.b},"registered_family_digest":d})
    def test_append_only_complete_snapshot_and_selection(self):
        self.freeze_ready()
        for trial, status in (("A","SUCCESS"),("B","FAILURE")):
            self.append("TRIAL_STARTED", {"trial_id":trial}); self.append("TRIAL_TERMINATED", {"trial_id":trial,"status":status,"configuration_digest":h("config"+trial)})
        self.append("CANDIDATE_FROZEN", {}); self.append("TRIAL_SELECTED", {"trial_id":"A"})
        snapshot=self.store.reduce_family_snapshot(self.f,self.r)
        self.assertEqual("COMPLETE",snapshot["completeness_state"]); self.assertEqual(2,snapshot["economic_trial_count"]); self.assertTrue(self.store.verify_event_chain(self.f,self.r))
    def test_freeze_blocks_hidden_winner_and_incomplete_selection(self):
        self.freeze_ready()
        with self.assertRaisesRegex(RegistryError,"FAMILY_FROZEN_NO_NEW_TRIAL"): self.append("TRIAL_REGISTERED", {"trial_id":"winner","immutable_digest":h("winner"),"selection_affecting":True})
        with self.assertRaisesRegex(RegistryError,"TRIAL_HISTORY_NOT_TERMINAL"): self.append("CANDIDATE_FROZEN", {})
    def test_stale_and_idempotent_response_loss(self):
        payload={"trial_id":"A","immutable_digest":self.a,"selection_affecting":True}
        first=self.append("TRIAL_REGISTERED",payload,event_id="fixed",idempotency_key="fixed-key")
        replay=self.store.append(family_id=self.f,family_revision_id=self.r,expected_sequence=0,expected_previous_digest=None,event_id="fixed",idempotency_key="fixed-key",event_type="TRIAL_REGISTERED",payload=payload)
        self.assertTrue(replay["duplicate"]); self.assertEqual(first["event_digest"],replay["event_digest"])
        with self.assertRaisesRegex(RegistryError,"STALE_FAMILY_SEQUENCE"): self.append("TRIAL_REGISTERED", {"trial_id":"B","immutable_digest":self.b,"selection_affecting":True},sequence=0,head=None)
    def test_mutated_authoritative_row_fails_chain(self):
        self.append("TRIAL_REGISTERED", {"trial_id":"A","immutable_digest":self.a,"selection_affecting":True})
        self.store.db.execute("UPDATE experiment_events SET record_json='{}' WHERE family_sequence=2"); self.store.db.commit()
        with self.assertRaisesRegex(RegistryError,"EVENT_CHAIN_INVALID"): self.store.verify_event_chain(self.f,self.r)
    def test_registration_digest_is_order_independent(self):
        one=registered_family_digest_v1(experiment_family_ref="x",expected_trial_digests={"B":self.b,"A":self.a},benchmark_ref="b",metric_id="m",horizon_id="h",search_space_ref="s",selection_rule_ref="r")
        two=registered_family_digest_v1(experiment_family_ref="x",expected_trial_digests={"A":self.a,"B":self.b},benchmark_ref="b",metric_id="m",horizon_id="h",search_space_ref="s",selection_rule_ref="r")
        self.assertEqual(one,two)

    def test_g6_r183_registered_family_golden_vector(self):
        actual=registered_family_digest_v1(
            experiment_family_ref="W4-GOLDEN-FAMILY-001@rev-1",
            expected_trial_digests={"trial-C":"77e965d526e35671f478776f1642cc41ad6aba93132b3c83709db174d63d61b8","trial-A":"5b9d28e3bbd3f99e9c7886c42965782d3545a2c86a8bdf4fcc4b0439cec5cc8d","trial-B":"2ce0faef2997478d5d7df1e5e6f2c069b7ea29d8300f3cb5ef6f77f87f1d6ee8"},
            benchmark_ref="BENCHMARK.ZERO_SKILL.V1",metric_id="SHARPE_OBSERVATION_FREQUENCY_V1",horizon_id="HORIZON.DAILY.20D.V1",search_space_ref="SEARCHSPACE.GOLDEN.001",selection_rule_ref="SELECT.MAX_METRIC.LEXICAL_TIES_FORBIDDEN.V1")
        self.assertEqual("c73a2e5e20ddc8a4f202c5f201e6cceee06c9bc82e15dbdaed3f4c6f5927ee90",actual)

if __name__ == "__main__": unittest.main()
