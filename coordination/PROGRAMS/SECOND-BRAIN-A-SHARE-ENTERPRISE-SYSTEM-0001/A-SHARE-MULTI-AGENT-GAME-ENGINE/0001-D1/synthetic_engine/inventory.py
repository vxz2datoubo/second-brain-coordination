"""Synthetic T+1 lots; no portfolio/account integration."""
from datetime import date
from dataclasses import replace
from .types import InventoryState, SyntheticLot

def _valid_nonnegative_integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0

def inventory_error(inventory: InventoryState):
    if not _valid_nonnegative_integer(inventory.pending_buy_quantity) or not _valid_nonnegative_integer(inventory.pending_sell_quantity): return "INVALID_PENDING_QUANTITY"
    lot_ids=set()
    for lot in inventory.lots:
        if not isinstance(lot.lot_id, str) or not lot.lot_id or lot.lot_id in lot_ids: return "INVALID_OR_DUPLICATE_LOT_ID"
        lot_ids.add(lot.lot_id)
        if not _valid_nonnegative_integer(lot.quantity) or not _valid_nonnegative_integer(lot.locked_quantity) or lot.locked_quantity > lot.quantity: return "INVALID_LOT_QUANTITY"
        try: date.fromisoformat(lot.acquired_trade_date)
        except (TypeError, ValueError): return "INVALID_LOT_TRADE_DATE"
    if inventory.settled_trade_date is not None:
        try: date.fromisoformat(inventory.settled_trade_date)
        except (TypeError, ValueError): return "INVALID_SETTLED_TRADE_DATE"
    return None

def known(inventory: InventoryState) -> bool:
    return inventory_error(inventory) is None

def sellable_quantity(inventory: InventoryState, trade_date: str, t_plus_one: bool) -> int:
    error=inventory_error(inventory)
    if error: raise ValueError(error)
    total = 0
    for lot in inventory.lots:
        if lot.quantity < 0 or lot.locked_quantity < 0 or lot.locked_quantity > lot.quantity: raise ValueError("MALFORMED_INVENTORY")
        if not t_plus_one or lot.acquired_trade_date < trade_date: total += lot.quantity - lot.locked_quantity
    return total - inventory.pending_sell_quantity

def apply_buy(inventory: InventoryState, trade_date: str, quantity: int, order_id: str) -> InventoryState:
    return replace(inventory, lots=inventory.lots + (SyntheticLot("buy:" + order_id, trade_date, quantity),))

def apply_sell(inventory: InventoryState, trade_date: str, quantity: int, t_plus_one: bool) -> InventoryState:
    remaining, lots = quantity, []
    for lot in inventory.lots:
        available = lot.quantity - lot.locked_quantity if (not t_plus_one or lot.acquired_trade_date < trade_date) else 0
        take = min(available, remaining); lots.append(replace(lot, quantity=lot.quantity - take)); remaining -= take
    if remaining: raise ValueError("INSUFFICIENT_SEASONED_INVENTORY")
    return replace(inventory, lots=tuple(lot for lot in lots if lot.quantity > 0))

def carry(inventory: InventoryState, side: str, quantity: int) -> InventoryState:
    key = "pending_buy_quantity" if side == "BUY" else "pending_sell_quantity"
    return replace(inventory, **{key: getattr(inventory, key) + quantity})

def cancel_pending(inventory: InventoryState) -> InventoryState:
    if not known(inventory): raise ValueError("UNKNOWN_INVENTORY")
    return replace(inventory, pending_buy_quantity=0, pending_sell_quantity=0)

def advance_settlement_day(inventory: InventoryState, current_trade_date: str, next_trade_date: str) -> InventoryState:
    error=inventory_error(inventory)
    if error: raise ValueError(error)
    try: current=date.fromisoformat(current_trade_date); next_day=date.fromisoformat(next_trade_date)
    except (TypeError, ValueError): raise ValueError("INVALID_SETTLEMENT_DATE")
    if next_day <= current: raise ValueError("INVALID_SETTLEMENT_TRANSITION")
    if inventory.pending_buy_quantity or inventory.pending_sell_quantity: raise ValueError("PENDING_INTENTS_REQUIRE_EXPLICIT_CANCELLATION")
    return replace(inventory, settled_trade_date=next_trade_date)
