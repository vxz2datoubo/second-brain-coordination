from __future__ import annotations
import json, sys, tempfile, unittest
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from offline_research.engine import Bar, ContractRuntime, DeterministicReplay, KnowledgeAtom, KnowledgeGateway, OfflineResearchRunner, SchemaRegistry, SimulationConfig, ValidationError, candidate_signals, digest, learning_packet, load_fixture, simulate_portfolio, validate
AS_OF='2026-01-31T23:59:59Z'; FIXTURE=ROOT/'fixtures'/'synthetic_bars.csv'

class OfflineResearchTests(unittest.TestCase):
 def setUp(self): self.bars,self.quarantine,self.manifest=load_fixture(FIXTURE,AS_OF)
 def test_csv_ingest_preserves_lineage(self):
  self.assertEqual(len(self.bars),8); self.assertEqual(self.quarantine,[]); self.assertTrue(self.manifest['synthetic']); self.assertEqual(self.bars[0].source_id,'synthetic-public-safe')
 def test_jsonl_ingest(self):
  b,q,m=load_fixture(ROOT/'fixtures'/'synthetic_bars.jsonl',AS_OF); self.assertEqual(len(b),2); self.assertEqual(q,[]); self.assertEqual(m['formats_supported'],['csv','json','jsonl'])
 def test_json_ingest(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'x.json'; p.write_text(json.dumps([self.bars[0].payload()])); b,q,_=load_fixture(p,AS_OF); self.assertEqual(b[0].event_id,self.bars[0].event_id); self.assertEqual(q,[])
 def test_schema_registry(self):
  r=SchemaRegistry(); r.require_compatible('OfflineReplay','1.2.0'); r.require_compatible('C2_A_SHARE_RULE_SNAPSHOT','1.9.0')
  with self.assertRaisesRegex(ValidationError,'unknown_schema'): r.require_compatible('Future','1.0.0')
  with self.assertRaisesRegex(ValidationError,'incompatible_schema_major'): r.require_compatible('OfflineReplay','2.0.0')
 def test_future_availability(self):
  with self.assertRaisesRegex(ValidationError,'future_available_at'): ContractRuntime().validate_bar(replace(self.bars[0],available_at='2026-02-01T00:00:00Z'),AS_OF)
 def test_missing_lineage_capability_entitlement(self):
  with self.assertRaisesRegex(ValidationError,'missing_lineage'): ContractRuntime().validate_bar(replace(self.bars[0],source_id=''),AS_OF)
  with self.assertRaisesRegex(ValidationError,'unsupported_capability'): ContractRuntime().validate_bar(replace(self.bars[0],capability_level='RAW_TRADE_TICK'),AS_OF)
  with self.assertRaisesRegex(ValidationError,'entitlement_not_confirmed'): ContractRuntime().validate_bar(replace(self.bars[0],entitlement_status='unknown'),AS_OF)
 def test_invalid_values(self):
  with self.assertRaisesRegex(ValidationError,'negative_market_value'): ContractRuntime().validate_bar(replace(self.bars[0],volume=-1),AS_OF)
  with self.assertRaisesRegex(ValidationError,'invalid_ohlc'): ContractRuntime().validate_bar(replace(self.bars[0],close=99),AS_OF)
  with self.assertRaisesRegex(ValidationError,'available_before_event'): ContractRuntime().validate_bar(replace(self.bars[0],available_at='2026-01-05T14:59:00Z'),AS_OF)
 def test_envelope_deterministic(self):
  r=ContractRuntime(); a=r.envelope(self.bars[0],'r','t'); b=r.envelope(self.bars[0],'r','t'); self.assertTrue(a['no_trade_gate']); self.assertFalse(a['authority_write']); self.assertEqual(digest(a),digest(b))
 def test_replay_sort_duplicate(self):
  x=DeterministicReplay(AS_OF,'r','t').run(list(reversed(self.bars))+[self.bars[0]]); self.assertEqual([i.event_id for i in x.events],[i.event_id for i in self.bars]); self.assertEqual(x.quarantine[0].outcome,'DUPLICATE')
 def test_near_duplicate(self):
  n=replace(self.bars[0],event_id='near',close=10.0005,high=10.10); x=DeterministicReplay(AS_OF,'r','t').run([self.bars[0],n]); self.assertEqual(x.quarantine[0].outcome,'NEAR_DUPLICATE')
 def test_checkpoint(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'c.json'; a=DeterministicReplay(AS_OF,'r','t').run(self.bars,p); b=DeterministicReplay(AS_OF,'r','t').run(self.bars,p,True); self.assertEqual(a.checkpoint['next_index'],8); self.assertEqual(b.event_ledger,[])
   with self.assertRaisesRegex(ValidationError,'checkpoint_input_mismatch'): DeterministicReplay(AS_OF,'r','t').run(self.bars[:-1],p,True)
 def test_signals_candidate(self):
  s=candidate_signals(self.bars); self.assertEqual(len(s),6); self.assertTrue(all(x['status']=='candidate' for x in s)); self.assertTrue(all('no_execution_adapter' in x['failure_conditions'] for x in s))
 def test_sim_waits_for_availability(self):
  sig={'signal_id':'s','symbol':self.bars[0].symbol,'event_id':'x','available_at':self.bars[0].available_at,'action':'BUY_CANDIDATE'}; l,_=simulate_portfolio(self.bars[:2], [sig], SimulationConfig()); self.assertEqual(l[0]['event_id'],self.bars[1].event_id); self.assertTrue(l[0]['executed_in_simulation'])
 def test_same_day_t1_lock(self):
  b=replace(self.bars[0],limit_reference_price=10.0); later=replace(b,event_id='later',event_time='2026-01-05T15:00:30Z',available_at='2026-01-05T15:01:30Z',session='CLOSE_AUCTION')
  buy={'signal_id':'b','symbol':b.symbol,'event_id':'b','available_at':'2026-01-05T14:00:00Z','action':'BUY_CANDIDATE'}; sell={'signal_id':'s','symbol':b.symbol,'event_id':'s','available_at':'2026-01-05T15:00:10Z','action':'SELL_CANDIDATE'}
  l,_=simulate_portfolio([b,later],[buy,sell],SimulationConfig(trading_days=('2026-01-05','2026-01-06'))); self.assertEqual(l[-1]['reason'],'T_PLUS_ONE_LOCK')
 def test_suspension(self):
  sig={'signal_id':'b','symbol':self.bars[1].symbol,'event_id':'x','available_at':'2026-01-01T00:00:00Z','action':'BUY_CANDIDATE'}; l,_=simulate_portfolio([replace(self.bars[1],suspended=True)],[sig],SimulationConfig()); self.assertEqual(l[0]['reason'],'SUSPENDED')
 def test_chinext_limit_is_20_and_fill_unknown(self):
  bar=replace(self.bars[1],close=12.0,high=12.0,limit_reference_price=10.0); sig={'signal_id':'l','symbol':bar.symbol,'event_id':'x','available_at':'2026-01-01T00:00:00Z','action':'BUY_CANDIDATE'}; l,_=simulate_portfolio([bar],[sig],SimulationConfig()); self.assertEqual(l[0]['reason'],'ORDER_FILLABILITY_UNKNOWN'); self.assertEqual(l[0]['price_validity_state'],'PRICE_VALID')
 def test_costs_and_sh_transfer(self):
  b=replace(self.bars[1],symbol='600000.SH',exchange='SH',limit_reference_price=10.0); n=replace(b,event_id='next',event_time='2026-01-08T15:00:00Z',available_at='2026-01-08T15:01:00Z',limit_reference_price=b.close)
  buy={'signal_id':'b','symbol':b.symbol,'event_id':'x','available_at':'2026-01-01T00:00:00Z','action':'BUY_CANDIDATE'}; sell={'signal_id':'s','symbol':b.symbol,'event_id':'y','available_at':'2026-01-07T00:00:00Z','action':'SELL_CANDIDATE'}; l,_=simulate_portfolio([b,n],[buy,sell],SimulationConfig(fixed_slippage_bps=10,trading_days=('2026-01-06','2026-01-07','2026-01-08'))); self.assertTrue(l[0]['executed_in_simulation']); self.assertTrue(l[1]['executed_in_simulation']); self.assertEqual(l[0]['rule_version'],'ashare-research-r143-w2-c2')
 def test_turnover_limit(self):
  sig={'signal_id':'b','symbol':self.bars[0].symbol,'event_id':'x','available_at':'2026-01-01T00:00:00Z','action':'BUY_CANDIDATE'}; l,_=simulate_portfolio([self.bars[0]],[sig],SimulationConfig(max_turnover=.01)); self.assertEqual(l[0]['reason'],'MAX_TURNOVER')
 def test_validation_temporal(self):
  self.assertEqual(validate(self.bars[:5],[],SimulationConfig())['validation_status'],'ABSTAIN'); full=validate(self.bars,[],SimulationConfig()); self.assertEqual(full['validation_status'],'EXPERIMENTAL_ONLY'); self.assertFalse(full['random_shuffle']); self.assertTrue(full['zero_market_impact_baseline_assumption'])
 def test_unknown_semantics_preserved(self):
  u=replace(self.bars[0],volume=None,suspended=None,is_st=None); ContractRuntime().validate_bar(u,AS_OF); self.assertIsNone(u.volume)
 def test_unknown_signal_abstains(self):
  u=[replace(b,volume=None,suspended=None,is_st=None) for b in self.bars]; s=candidate_signals(u); self.assertTrue(all(x['action']=='ABSTAIN' for x in s))
 def test_unknown_simulation_blocks(self):
  u=replace(self.bars[0],volume=None,suspended=None,is_st=None); sig={'signal_id':'x','symbol':u.symbol,'event_id':'x','available_at':'2026-01-01T00:00:00Z','action':'BUY_CANDIDATE'}; l,_=simulate_portfolio([u],[sig],SimulationConfig()); self.assertEqual(l[0]['reason'],'REQUIRED_MARKET_SEMANTICS_UNKNOWN')
 def test_unknown_validation_abstains(self):
  u=[replace(b,volume=None,suspended=None,is_st=None) for b in self.bars]; r=validate(u,[],SimulationConfig()); self.assertEqual(r['validation_status'],'ABSTAIN')
 def test_knowledge_gateway(self):
  g=KnowledgeGateway([KnowledgeAtom('a','momentum candidate alpha','candidate',['s'],'weak')]); self.assertEqual(len(g.query('momentum',100)['atoms']),1); self.assertEqual(g.query('show api_key',100)['abstention'],'DENIED_HARD_SECRET')
 def test_learning_packet(self):
  p=learning_packet({'run_id':'r'},{'validation_status':'EXPERIMENTAL_ONLY'},'e'); q=learning_packet({'run_id':'r'},{'validation_status':'EXPERIMENTAL_ONLY'},'e'); self.assertEqual(p['packet_content_hash'],q['packet_content_hash']); self.assertFalse(p['authority_write'])
 def test_end_to_end(self):
  with tempfile.TemporaryDirectory() as t:
   a=OfflineResearchRunner(FIXTURE,Path(t)/'a').run(); b=OfflineResearchRunner(FIXTURE,Path(t)/'b').run(); self.assertEqual(a['bundle']['evidence_hash'],b['bundle']['evidence_hash']); self.assertTrue((Path(t)/'a'/'ReproducibilityBundleManifest.json').exists())

if __name__=='__main__': unittest.main()
