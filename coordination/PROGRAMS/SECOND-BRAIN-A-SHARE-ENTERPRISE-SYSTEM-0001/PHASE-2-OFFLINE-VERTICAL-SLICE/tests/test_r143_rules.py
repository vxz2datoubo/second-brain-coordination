from __future__ import annotations
import json, sys, unittest
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from offline_research.r143_rules import *

CAL=TradingCalendar('cal','A_SHARE',('2026-07-03','2026-07-06','2026-07-07','2026-07-08','2026-07-10','2026-07-13'),'synthetic-calendar')
R=DEFAULT_RULE_RESOLVER

def ref(snap,day='2026-07-06',kind='OFFICIAL_PREVIOUS_CLOSE',value=10.0): return LimitReferencePrice(value,kind,'official-synthetic-reference',day,snap.rule_snapshot_id)

class RuleSnapshotTests(unittest.TestCase):
 def test_sse_risk_pre_boundary(self): self.assertEqual(R.resolve('SSE','MAIN','RISK_WARNING','2026-07-03').price_limit_pct,.05)
 def test_sse_risk_post_boundary(self): self.assertEqual(R.resolve('SSE','MAIN','RISK_WARNING','2026-07-06').price_limit_pct,.10)
 def test_szse_risk_pre_boundary(self): self.assertEqual(R.resolve('SZSE','MAIN','RISK_WARNING','2026-07-03').price_limit_pct,.05)
 def test_szse_risk_post_boundary(self): self.assertEqual(R.resolve('SZSE','MAIN','RISK_WARNING','2026-07-06').price_limit_pct,.10)
 def test_star_20(self): self.assertEqual(R.resolve('SSE','STAR','NORMAL','2026-07-06').price_limit_pct,.20)
 def test_chinext_20(self): self.assertEqual(R.resolve('SZSE','CHINEXT','NORMAL','2026-07-06').price_limit_pct,.20)
 def test_chinext_risk_20_special_status(self): self.assertEqual(R.resolve('SZSE','CHINEXT','RISK_WARNING','2026-07-06').price_limit_pct,.20)
 def test_main_ipo_no_limit(self): self.assertTrue(R.resolve('SSE','MAIN','NORMAL','2026-07-06',3).no_price_limit)
 def test_star_ipo_no_limit(self): self.assertTrue(R.resolve('SSE','STAR','NORMAL','2026-07-06',5).no_price_limit)
 def test_chinext_ipo_no_limit(self): self.assertTrue(R.resolve('SZSE','CHINEXT','NORMAL','2026-07-06',1).no_price_limit)
 def test_bse_fail_closed(self):
  with self.assertRaisesRegex(RuleGateError,'UNSUPPORTED_MARKET_BSE'): R.resolve('BSE','MAIN','NORMAL','2026-07-06')
 def test_unknown_market_fail_closed(self):
  with self.assertRaisesRegex(RuleGateError,'UNSUPPORTED_MARKET'): R.resolve('HKEX','MAIN','NORMAL','2026-07-06')
 def test_board_exchange_mismatch(self):
  with self.assertRaisesRegex(RuleGateError,'BOARD_EXCHANGE_MISMATCH'): R.resolve('SSE','CHINEXT','NORMAL','2026-07-06')
 def test_pre_effective_fails(self):
  post=[s for s in DEFAULT_RULE_SNAPSHOTS if s.rule_snapshot_id=='SSE_MAIN_RISK_POST_20260706']; rr=AShareRuleResolver(post)
  with self.assertRaisesRegex(RuleGateError,'MISSING_OR_AMBIGUOUS_RULE_SNAPSHOT'): rr.resolve('SSE','MAIN','RISK_WARNING','2026-07-03')
 def test_superseded_interval_fails(self):
  pre=[s for s in DEFAULT_RULE_SNAPSHOTS if s.rule_snapshot_id=='SSE_MAIN_RISK_PRE_20260706']; rr=AShareRuleResolver(pre)
  with self.assertRaisesRegex(RuleGateError,'MISSING_OR_AMBIGUOUS_RULE_SNAPSHOT'): rr.resolve('SSE','MAIN','RISK_WARNING','2026-07-06')
 def test_stale_mutation_fails(self):
  s=R.resolve('SSE','MAIN','RISK_WARNING','2026-07-06'); bad=replace(s,price_limit_pct=.99)
  with self.assertRaisesRegex(RuleGateError,'STALE_RULE_MUTATION'): bad.verify_integrity()
 def test_snapshot_ids_unique(self): self.assertEqual(len({s.rule_snapshot_id for s in DEFAULT_RULE_SNAPSHOTS}),len(DEFAULT_RULE_SNAPSHOTS))

class PriceFillTests(unittest.TestCase):
 def test_official_previous_close_reference(self):
  s=R.resolve('SSE','MAIN','NORMAL','2026-07-06'); a=evaluate_price_validity(11,s,ref(s),'2026-07-06'); self.assertTrue(a.valid); self.assertTrue(a.at_upper_limit); self.assertEqual(a.reference_price_kind,'OFFICIAL_PREVIOUS_CLOSE')
 def test_ex_right_reference(self):
  s=R.resolve('SSE','MAIN','NORMAL','2026-07-06'); a=evaluate_price_validity(9.9,s,ref(s,kind='EX_RIGHT_EX_DIVIDEND_REFERENCE',value=9.0),'2026-07-06'); self.assertTrue(a.at_upper_limit)
 def test_reference_binding_mismatch(self):
  s=R.resolve('SSE','MAIN','NORMAL','2026-07-06'); bad=LimitReferencePrice(10,'OFFICIAL_PREVIOUS_CLOSE','src','2026-07-06','other')
  with self.assertRaisesRegex(RuleGateError,'REFERENCE_PRICE_RULE_BINDING_MISMATCH'): evaluate_price_validity(10,s,bad,'2026-07-06')
 def test_missing_reference_fails(self):
  s=R.resolve('SSE','MAIN','NORMAL','2026-07-06')
  with self.assertRaisesRegex(RuleGateError,'MISSING_RULE_OR_REFERENCE_PRICE'): evaluate_price_validity(10,s,None,'2026-07-06')
 def test_no_limit_needs_no_reference(self):
  s=R.resolve('SSE','STAR','NORMAL','2026-07-06',2); a=evaluate_price_validity(99,s,None,'2026-07-06'); self.assertEqual(a.state,PriceValidityState.PRICE_VALID_NO_LIMIT)
 def test_bar_only_limit_unknown(self):
  s=R.resolve('SSE','MAIN','NORMAL','2026-07-06'); p=evaluate_price_validity(11,s,ref(s),'2026-07-06'); f=evaluate_order_fillability(p); self.assertEqual(f.state,FillabilityState.ORDER_FILLABILITY_UNKNOWN); self.assertTrue(f.abstain); self.assertFalse(f.observed_fact)
 def test_evidence_confirmed_fillable_vocabulary(self):
  s=R.resolve('SSE','MAIN','NORMAL','2026-07-06'); p=evaluate_price_validity(11,s,ref(s),'2026-07-06'); e=FillabilityEvidence('e1','orderbook','2026-07-06T10:00:00+08:00',True,'CONTRA_LIQUIDITY',100); f=evaluate_order_fillability(p,e); self.assertEqual(f.state.value,'ORDER_FILLABILITY_EVIDENCE_CONFIRMED'); self.assertTrue(f.observed_fact); self.assertTrue(f.fillable)
 def test_evidence_confirmed_no_fill_is_observed(self):
  s=R.resolve('SSE','MAIN','NORMAL','2026-07-06'); p=evaluate_price_validity(11,s,ref(s),'2026-07-06'); e=FillabilityEvidence('e2','orderbook','2026-07-06T10:00:00+08:00',False,'QUEUE_ORDER_BOOK'); f=evaluate_order_fillability(p,e); self.assertEqual(f.state,FillabilityState.ORDER_FILLABILITY_EVIDENCE_CONFIRMED); self.assertFalse(f.fillable); self.assertTrue(f.observed_fact)
 def test_conservative_no_fill_is_scenario(self):
  s=R.resolve('SSE','MAIN','NORMAL','2026-07-06'); p=evaluate_price_validity(11,s,ref(s),'2026-07-06'); f=evaluate_order_fillability(p,None,True); self.assertEqual(f.state,FillabilityState.SCENARIO_ASSUMPTION_NO_FILL); self.assertFalse(f.observed_fact); self.assertFalse(f.abstain)
 def test_price_validity_not_fillability(self):
  s=R.resolve('SSE','MAIN','NORMAL','2026-07-06'); p=evaluate_price_validity(11,s,ref(s),'2026-07-06'); f=evaluate_order_fillability(p); self.assertTrue(p.valid); self.assertIsNone(f.fillable)

class InventoryCalendarTests(unittest.TestCase):
 def test_old_settled_plus_same_day_buy(self):
  i=SettlementAwareInventory(); i.acquire('X',100,'2026-07-03','old'); i.acquire('X',50,'2026-07-06','new'); self.assertEqual(i.sellable_quantity('X','2026-07-06',CAL),100); self.assertEqual(i.total_quantity('X'),150)
 def test_partial_old_sale(self):
  i=SettlementAwareInventory(); i.acquire('X',100,'2026-07-03','old'); i.acquire('X',50,'2026-07-06','new'); i.sell('X',40,'2026-07-06',CAL); self.assertEqual(i.total_quantity('X'),110); self.assertEqual(i.sellable_quantity('X','2026-07-06',CAL),60)
 def test_multiple_lots_fifo(self):
  i=SettlementAwareInventory(); i.acquire('X',100,'2026-07-03','a'); i.acquire('X',60,'2026-07-06','b'); i.acquire('X',20,'2026-07-07','c'); i.sell('X',100,'2026-07-07',CAL); self.assertEqual(i.snapshot('X')[0]['remaining_quantity'],0); self.assertEqual(i.sellable_quantity('X','2026-07-07',CAL),60)
 def test_same_day_locked(self):
  i=SettlementAwareInventory(); i.acquire('X',100,'2026-07-06','a'); self.assertEqual(i.sellable_quantity('X','2026-07-06',CAL),0)
 def test_next_trading_day_unlock(self):
  i=SettlementAwareInventory(); i.acquire('X',100,'2026-07-06','a'); self.assertEqual(i.sellable_quantity('X','2026-07-07',CAL),100)
 def test_weekend_not_calendar_day_unlock(self):
  cal=TradingCalendar('w','A_SHARE',('2026-07-10','2026-07-13'),'src'); i=SettlementAwareInventory(); i.acquire('X',100,'2026-07-10','a'); self.assertEqual(i.sellable_quantity('X','2026-07-12',cal),0); self.assertEqual(i.sellable_quantity('X','2026-07-13',cal),100)
 def test_oversell_locked(self):
  i=SettlementAwareInventory(); i.acquire('X',100,'2026-07-06','a')
  with self.assertRaisesRegex(RuleGateError,'T_PLUS_ONE_LOCK'): i.sell('X',1,'2026-07-06',CAL)

class ReplayGateTests(unittest.TestCase):
 def test_supported_session(self): self.assertTrue(replay_gate(resolver=R,exchange='SSE',board='MAIN',security_status='NORMAL',trading_day='2026-07-06',calendar=CAL,session='CONTINUOUS').allowed)
 def test_unknown_session_abstains(self): self.assertEqual(replay_gate(resolver=R,exchange='SSE',board='MAIN',security_status='NORMAL',trading_day='2026-07-06',calendar=CAL,session='AFTER_MIDNIGHT').reason,'UNSUPPORTED_OR_UNKNOWN_SESSION')
 def test_missing_calendar_abstains(self): self.assertEqual(replay_gate(resolver=R,exchange='SSE',board='MAIN',security_status='NORMAL',trading_day='2026-07-06',calendar=None,session='CONTINUOUS').reason,'UNKNOWN_OR_NON_TRADING_CALENDAR_DAY')
 def test_nontrading_day_abstains(self): self.assertEqual(replay_gate(resolver=R,exchange='SSE',board='MAIN',security_status='NORMAL',trading_day='2026-07-05',calendar=CAL,session='CONTINUOUS').reason,'UNKNOWN_OR_NON_TRADING_CALENDAR_DAY')
 def test_same_cutoff_receipt_deterministic(self):
  p={'as_of':'2026-07-06T15:00:00+08:00','rule_snapshot_id':'SSE_MAIN_NORMAL_POST_20260706','events':['a','b']}; self.assertEqual(deterministic_replay_receipt(p)['receipt_hash'],deterministic_replay_receipt(p)['receipt_hash'])

class DurableEvidenceTests(unittest.TestCase):
 def setUp(self):
  self.prov=json.loads((ROOT/'R143'/'OFFICIAL-RULE-PROVENANCE.json').read_text())
  v=json.loads((ROOT/'R143'/'VALIDATION-RECEIPT.json').read_text()); self.adv=v['adversarial_evidence']
  self.receipt=v['deterministic_replay']
  cases=json.loads((ROOT/'fixtures'/'r143_cases.json').read_text()); self.fill={'cases':cases['fillability']}
  self.cal=cases['trading_calendar']
  self.refs={'cases':cases['reference_price']}
 def test_authority_is_adapt_existing_not_new_identity(self):
  a=self.prov['authority']; self.assertEqual(a['object'],'AShareRuleSnapshot'); self.assertEqual(a['contract'],'C2_A_SHARE_RULE_SNAPSHOT'); self.assertEqual(a['materialization'],'ADAPT_EXISTING'); self.assertFalse(a['new_canonical_schema_identity_created'])
 def test_official_sources_have_required_provenance_fields(self):
  required={'exchange','document_identity','document_number','publication_date','effective_at','superseded_rule_version','retrieval_ref','semantics_used','rule_snapshot_ids'}
  for src in self.prov['sources']:
   self.assertTrue(required.issubset(src)); self.assertTrue(src['retrieval_ref'].startswith('https://')); self.assertTrue(src['rule_snapshot_ids'])
 def test_runtime_source_refs_are_manifested(self):
  manifest={s['source_ref'] for s in self.prov['sources']}; runtime={s.source_ref for s in DEFAULT_RULE_SNAPSHOTS}; self.assertTrue(runtime.issubset(manifest), runtime-manifest)
 def test_manifest_snapshot_ids_match_runtime(self):
  runtime={s.rule_snapshot_id for s in DEFAULT_RULE_SNAPSHOTS}; bound={x for s in self.prov['sources'] for x in s['rule_snapshot_ids']}; self.assertEqual(runtime,bound)
 def test_sse_2026_identity(self):
  s=next(x for x in self.prov['sources'] if x['source_ref']=='SSE_TRADING_RULES_2026'); self.assertEqual(s['document_number'],'上证发〔2026〕41号'); self.assertEqual(s['publication_date'],'2026-04-24'); self.assertEqual(s['effective_at'],'2026-07-06'); self.assertEqual(s['superseded_rule_version'],'上证发〔2023〕32号')
 def test_szse_2026_identity(self):
  s=next(x for x in self.prov['sources'] if x['source_ref']=='SZSE_TRADING_RULES_2026'); self.assertEqual(s['document_number'],'深证上〔2026〕551号'); self.assertEqual(s['publication_date'],'2026-04-24'); self.assertEqual(s['effective_at'],'2026-07-06'); self.assertEqual(s['superseded_rule_version'],'深证上〔2023〕98号')
 def test_bse_is_unsupported_without_fallback(self):
  b=self.prov['unsupported']['BSE']; self.assertEqual(b['runtime_state'],'UNSUPPORTED / ABSTAIN'); self.assertFalse(b['fallback_to_sse_or_szse'])
 def test_fillability_fixture_vocabulary_exact(self):
  self.assertEqual({c['expected_state'] for c in self.fill['cases']},{'ORDER_FILLABILITY_UNKNOWN','ORDER_FILLABILITY_EVIDENCE_CONFIRMED','SCENARIO_ASSUMPTION_NO_FILL'})
 def test_fillability_fixture_executes_semantics(self):
  s=DEFAULT_RULE_RESOLVER.resolve('SSE','MAIN','NORMAL','2026-07-06'); p=evaluate_price_validity(11,s,LimitReferencePrice(10,'OFFICIAL_PREVIOUS_CLOSE','fixture','2026-07-06',s.rule_snapshot_id),'2026-07-06')
  for c in self.fill['cases']:
   e=None
   if c.get('evidence'): e=FillabilityEvidence(**c['evidence'])
   out=evaluate_order_fillability(p,e,c.get('conservative_no_fill_scenario',False)); self.assertEqual(out.state.value,c['expected_state']); self.assertEqual(out.observed_fact,c['observed_fact']); self.assertEqual(out.abstain,c['abstain'])
 def test_reference_price_fixture_binds_snapshot(self):
  s=DEFAULT_RULE_RESOLVER.resolve('SSE','MAIN','NORMAL','2026-07-06')
  for c in self.refs['cases']:
   r=LimitReferencePrice(c['value'],c['kind'],c['source_ref'],c['trading_day'],c['rule_snapshot_id']); a=evaluate_price_validity(c['value'],s,r,c['trading_day']); self.assertTrue(a.valid); self.assertEqual(a.reference_price_kind,c['kind'])
 def test_trading_calendar_fixture_is_explicit(self):
  c=TradingCalendar(self.cal['calendar_id'],self.cal['exchange'],tuple(self.cal['trading_days']),self.cal['source_ref']); self.assertEqual(c.next_trading_day('2026-07-10'),'2026-07-13')
 def test_deterministic_receipt_recomputes(self):
  recomputed=deterministic_replay_receipt(self.receipt['payload']); self.assertEqual(recomputed['receipt_hash'],self.receipt['receipt_hash']); self.assertEqual(recomputed['receipt_hash'],self.adv['receipt_hash'])
 def test_stale_rule_mutation_is_real_failure(self):
  s=DEFAULT_RULE_RESOLVER.resolve('SSE','MAIN','RISK_WARNING','2026-07-06'); bad=replace(s,price_limit_pct=.99)
  with self.assertRaisesRegex(RuleGateError,'STALE_RULE_MUTATION'): bad.verify_integrity()
 def test_zero_impact_is_only_baseline_assumption(self): self.assertEqual(self.adv['retained']['zero_market_impact'],'EXPLICIT_BASELINE_ASSUMPTION')


if __name__=='__main__': unittest.main()
