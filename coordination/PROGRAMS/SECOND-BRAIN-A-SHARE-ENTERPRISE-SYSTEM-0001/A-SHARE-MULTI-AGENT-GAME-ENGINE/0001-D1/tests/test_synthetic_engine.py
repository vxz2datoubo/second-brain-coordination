import json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from synthetic_engine.calendar import transition
from synthetic_engine.engine import reduce_order
from synthetic_engine.fixtures import FIXTURES, INVENTORY, INFO, RULE, market, order
from synthetic_engine.inventory import advance_settlement_day, apply_buy, cancel_pending, sellable_quantity
from synthetic_engine.rules import validate
from synthetic_engine.types import *

class Rules(unittest.TestCase):
 def test_named_fixtures(self):
  self.assertEqual(12,len(FIXTURES))
  for name,s,i,o,expected in FIXTURES:
   with self.subTest(name=name): self.assertEqual(expected,reduce_order(s,i,o).status)
 def test_invariants(self):
  a=reduce_order(market(),INVENTORY,order('x',mode=MatchMode.PARTIAL,partial=1)); b=reduce_order(market(),INVENTORY,order('x',mode=MatchMode.PARTIAL,partial=1))
  self.assertEqual(a,b); self.assertGreaterEqual(a.filled_quantity,0); self.assertLessEqual(a.filled_quantity,2); self.assertEqual(1,a.unfilled_quantity); self.assertEqual(1,a.inventory.lots[-1].quantity)
  self.assertEqual(4,reduce_order(market(),INVENTORY,order('sell',side=OrderSide.SELL,qty=1)).inventory.lots[0].quantity)
  carried=reduce_order(market(SessionPhase.CLOSING_AUCTION),INVENTORY,order('carry',mode=MatchMode.NO_FILL_CARRY)); self.assertEqual(2,carried.inventory.pending_buy_quantity)
  self.assertEqual(INVENTORY,reduce_order(market(),INVENTORY,order('cancel',mode=MatchMode.NO_FILL_CANCEL)).inventory)
  self.assertEqual(reduce_order(market(SessionPhase.PREOPEN),INVENTORY,order('bad')),reduce_order(market(SessionPhase.PREOPEN),INVENTORY,order('bad')))
  self.assertFalse(validate(market(info=InformationSet(None,100)),INVENTORY,order('cap')).accepted); self.assertFalse(validate(market(info=InformationSet('SYNTHETIC_RESEARCH_ONLY',None)),INVENTORY,order('time')).accepted); self.assertFalse(validate(market(),INVENTORY,order('future',available=101)).accepted)
  self.assertFalse(validate(market(rule=None),INVENTORY,order('rule')).accepted); self.assertFalse(validate(market(rule=SyntheticRuleSnapshot('', 'S','B','2026-07-26',1,10,'p','q',(SessionPhase.CONTINUOUS_AM,),True,'x','1')),INVENTORY,order('mal')).accepted); self.assertFalse(validate(market(rule=SyntheticRuleSnapshot('x','S','B','2026-07-26',1,10,None,'q',(SessionPhase.CONTINUOUS_AM,),True,'x','1')),INVENTORY,order('unit')).accepted)
  self.assertFalse(validate(market(status=SecurityStatus.UNKNOWN),INVENTORY,order('status')).accepted); self.assertFalse(validate(market(status=SecurityStatus.SUSPENDED),INVENTORY,order('halt')).accepted); self.assertFalse(validate(market(),INVENTORY,order('limit',price=11)).accepted); self.assertFalse(validate(market(),INVENTORY,order('qty',qty=0)).accepted)
  self.assertEqual(0,sellable_quantity(InventoryState((SyntheticLot('locked','2026-07-25',1,1),)),'2026-07-26',True)); self.assertEqual(2,advance_settlement_day(apply_buy(InventoryState(()),'2026-07-26',2,'b')).lots[0].quantity)
  with self.assertRaises(ValueError): transition(SessionPhase.PREOPEN,SessionPhase.CLOSED)
  with self.assertRaises(ValueError): advance_settlement_day(carried.inventory)
  self.assertEqual(0,cancel_pending(carried.inventory).pending_buy_quantity); self.assertEqual(OutcomeStatus.UNKNOWN_OUTCOME,reduce_order(market(),INVENTORY,order('unknown',mode=MatchMode.UNKNOWN)).status)

if __name__=='__main__':
 if '--normalized' in sys.argv:
  summary=[(n,reduce_order(s,i,o).status.value) for n,s,i,o,_ in FIXTURES]; print(json.dumps(summary,sort_keys=True,separators=(',',':')))
 else: unittest.main()
