"""Bounded synthetic inventory and settlement transitions."""
from datetime import date
from dataclasses import replace
from .types import InventoryState, SyntheticLot, NUMERIC_SAFETY_BOUND

def _number(value): return isinstance(value,int) and not isinstance(value,bool) and 0 <= value <= NUMERIC_SAFETY_BOUND
def _date(value):
 try: return date.fromisoformat(value)
 except (TypeError,ValueError): return None

def inventory_error(inventory):
 if not isinstance(inventory,InventoryState): return 'INVALID_INVENTORY_OBJECT'
 if not _number(inventory.pending_buy_quantity) or not _number(inventory.pending_sell_quantity): return 'INVALID_PENDING_QUANTITY'
 settled=_date(inventory.settled_trade_date) if inventory.settled_trade_date is not None else None
 if inventory.settled_trade_date is not None and settled is None:return 'INVALID_SETTLED_TRADE_DATE'
 if not isinstance(inventory.lots,tuple):return 'INVALID_LOT_COLLECTION'
 ids=set()
 for lot in inventory.lots:
  if not isinstance(lot,SyntheticLot):return 'INVALID_LOT_OBJECT'
  if not isinstance(lot.lot_id,str) or not lot.lot_id or lot.lot_id in ids:return 'INVALID_OR_DUPLICATE_LOT_ID'
  ids.add(lot.lot_id)
  if not _number(lot.quantity) or not _number(lot.locked_quantity) or lot.locked_quantity>lot.quantity:return 'INVALID_LOT_QUANTITY'
  acquired=_date(lot.acquired_trade_date)
  if acquired is None:return 'INVALID_LOT_TRADE_DATE'
  if settled is not None and acquired>settled:return 'LOT_AFTER_SETTLEMENT'
 return None

def sellable_quantity(inventory,t_plus_one):
 error=inventory_error(inventory)
 if error:raise ValueError(error)
 if not isinstance(t_plus_one,bool):raise ValueError('INVALID_T_PLUS_ONE_FLAG')
 total=0
 for lot in inventory.lots:
  mature=(not t_plus_one) or (inventory.settled_trade_date is not None and lot.acquired_trade_date < inventory.settled_trade_date)
  if mature: total+=lot.quantity-lot.locked_quantity
 return total-inventory.pending_sell_quantity

def apply_buy(inventory,trade_date,quantity,order_id):
 error=inventory_error(inventory)
 if error:raise ValueError(error)
 if _date(trade_date) is None or not _number(quantity) or quantity==0 or not isinstance(order_id,str) or not order_id:return (_ for _ in ()).throw(ValueError('INVALID_BUY_INPUT'))
 lot_id='buy:'+order_id
 if any(lot.lot_id==lot_id for lot in inventory.lots):raise ValueError('DUPLICATE_ORDER_OR_LOT_ID')
 if inventory.settled_trade_date is None: inventory=replace(inventory,settled_trade_date=trade_date)
 if _date(inventory.settled_trade_date)<_date(trade_date):raise ValueError('SETTLEMENT_BEHIND_TRADE_DATE')
 return replace(inventory,lots=inventory.lots+(SyntheticLot(lot_id,trade_date,quantity),))

def apply_sell(inventory,quantity,t_plus_one):
 if not _number(quantity) or quantity==0:raise ValueError('INVALID_SELL_QUANTITY')
 if quantity>sellable_quantity(inventory,t_plus_one):raise ValueError('INSUFFICIENT_MATURE_INVENTORY')
 remaining,lots=quantity,[]
 for lot in inventory.lots:
  mature=(not t_plus_one) or (inventory.settled_trade_date is not None and lot.acquired_trade_date<inventory.settled_trade_date)
  take=min(lot.quantity-lot.locked_quantity,remaining) if mature else 0
  lots.append(replace(lot,quantity=lot.quantity-take));remaining-=take
 return replace(inventory,lots=tuple(lot for lot in lots if lot.quantity))

def carry(inventory,side,quantity):
 error=inventory_error(inventory)
 if error:raise ValueError(error)
 if side not in ('BUY','SELL') or not _number(quantity) or quantity==0:raise ValueError('INVALID_CARRY_INPUT')
 key='pending_buy_quantity' if side=='BUY' else 'pending_sell_quantity';result=getattr(inventory,key)+quantity
 if result>NUMERIC_SAFETY_BOUND:raise ValueError('NUMERIC_BOUND_EXCEEDED')
 return replace(inventory,**{key:result})

def cancel_pending(inventory):
 error=inventory_error(inventory)
 if error:raise ValueError(error)
 return replace(inventory,pending_buy_quantity=0,pending_sell_quantity=0)

def advance_settlement_day(inventory,current_trade_date,next_trade_date):
 error=inventory_error(inventory)
 if error:raise ValueError(error)
 current,next_day=_date(current_trade_date),_date(next_trade_date)
 if current is None or next_day is None:raise ValueError('INVALID_SETTLEMENT_DATE')
 if next_day<=current:raise ValueError('INVALID_SETTLEMENT_TRANSITION')
 if inventory.pending_buy_quantity or inventory.pending_sell_quantity:raise ValueError('PENDING_INTENTS_REQUIRE_EXPLICIT_CANCELLATION')
 if inventory.settled_trade_date is not None and _date(inventory.settled_trade_date)!=current:raise ValueError('SETTLEMENT_STATE_MISMATCH')
 return replace(inventory,settled_trade_date=next_trade_date)
