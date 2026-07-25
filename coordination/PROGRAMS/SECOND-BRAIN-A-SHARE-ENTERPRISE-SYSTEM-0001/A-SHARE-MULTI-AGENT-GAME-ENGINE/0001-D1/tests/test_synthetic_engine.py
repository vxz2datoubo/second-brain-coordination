import json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from synthetic_engine.calendar import transition
from synthetic_engine.engine import reduce_order
from synthetic_engine.fixtures import FIXTURES, INVENTORY, INFO, RULE, market, order
from synthetic_engine.inventory import advance_settlement_day, apply_buy, cancel_pending, sellable_quantity
from synthetic_engine.rules import validate
from synthetic_engine.types import *

class Rules(unittest.TestCase):
 def test_named_fixtures(self):
  self.assertEqual(20,len(FIXTURES))
  for name,s,i,o,expected in FIXTURES:
   with self.subTest(name=name): self.assertEqual(expected,reduce_order(s,i,o).status)

def _out(mode=MatchMode.PARTIAL,partial=1): return reduce_order(market(),INVENTORY,order('x',mode=mode,partial=partial))
def _pass(expression):
 def method(self): self.assertTrue(expression())
 return method

_CHECKS={
'I01_deterministic_reduction':lambda: _out()==_out(),
'I02_fixture_order':lambda: [x[0] for x in FIXTURES]==sorted([x[0] for x in FIXTURES]),
'I03_nonnegative_fill':lambda: _out().filled_quantity>=0,
'I04_fill_bound':lambda: _out().filled_quantity<=2,
'I05_lot_nonnegative':lambda: all(l.quantity>=0 for l in _out().inventory.lots),
'I06_sell_conservation':lambda: reduce_order(market(),INVENTORY,order('sell',side=OrderSide.SELL,qty=1)).inventory.lots[0].quantity==4,
'I07_buy_fresh_lot':lambda: _out().inventory.lots[-1].acquired_trade_date=='2026-07-26',
'I08_partial_remainder':lambda: _out().unfilled_quantity==1,
'I09_cancel_preserves':lambda: reduce_order(market(),INVENTORY,order('cancel',mode=MatchMode.NO_FILL_CANCEL)).inventory==INVENTORY,
'I10_carry_pending':lambda: reduce_order(market(SessionPhase.CLOSING_AUCTION),INVENTORY,order('carry',mode=MatchMode.NO_FILL_CARRY)).inventory.pending_buy_quantity==2,
'I11_reject_idempotent':lambda: reduce_order(market(SessionPhase.PREOPEN),INVENTORY,order('bad'))==reduce_order(market(SessionPhase.PREOPEN),INVENTORY,order('bad')),
'I12_unknown_capability':lambda: not validate(market(info=InformationSet(None,100)),INVENTORY,order('cap')).accepted,
'I13_unknown_available_at':lambda: not validate(market(info=InformationSet('SYNTHETIC_RESEARCH_ONLY',None)),INVENTORY,order('time')).accepted,
'I14_future_information':lambda: not validate(market(),INVENTORY,order('future',available=101)).accepted,
'I15_malformed_snapshot':lambda: not validate(market(rule=None),INVENTORY,order('rule')).accepted,
'I16_unknown_unit':lambda: not validate(market(rule=SyntheticRuleSnapshot('x','S','B','2026-07-26',1,10,None,'q',(SessionPhase.CONTINUOUS_AM,),True,'x','1')),INVENTORY,order('unit')).accepted,
'I17_illegal_phase':lambda: not validate(market(SessionPhase.PREOPEN),INVENTORY,order('phase')).accepted,
'I18_suspension':lambda: not validate(market(status=SecurityStatus.SUSPENDED),INVENTORY,order('halt')).accepted,
'I19_price_limit':lambda: not validate(market(),INVENTORY,order('limit',price=11)).accepted,
'I20_t_plus_one':lambda: not validate(market(),InventoryState((SyntheticLot('fresh','2026-07-26',1),)),order('fresh',side=OrderSide.SELL,qty=1)).accepted,
'I21_locked_lot':lambda: sellable_quantity(InventoryState((SyntheticLot('locked','2026-07-25',1,1),)),'2026-07-26',True)==0,
'I22_settlement':lambda: _settlement_proof(),
'I23_transition':lambda: _transition_proof(),
'I24_unknown_match':lambda: reduce_order(market(),INVENTORY,order('unknown',mode=MatchMode.UNKNOWN)).status is OutcomeStatus.INVALID_OR_BLOCKED,
}
def _settlement_proof():
 inv=apply_buy(InventoryState(()),'2026-07-26',2,'b')
 if sellable_quantity(inv,'2026-07-26',True)!=0:return False
 matured=advance_settlement_day(inv,'2026-07-26','2026-07-27')
 return matured.settled_trade_date=='2026-07-27' and sellable_quantity(matured,'2026-07-27',True)==2
def _transition_proof():
 try: transition(SessionPhase.PREOPEN,SessionPhase.CLOSED)
 except ValueError:return True
 return False
for _id,_check in _CHECKS.items(): setattr(Rules,'test_'+_id,_pass(_check))

if __name__=='__main__':
 if '--normalized' in sys.argv:
  print(json.dumps({'fixtures':[(n,reduce_order(s,i,o).status.value) for n,s,i,o,_ in FIXTURES],'invariant_ids':sorted(_CHECKS)},sort_keys=True,separators=(',',':')))
 else: unittest.main(verbosity=2)
