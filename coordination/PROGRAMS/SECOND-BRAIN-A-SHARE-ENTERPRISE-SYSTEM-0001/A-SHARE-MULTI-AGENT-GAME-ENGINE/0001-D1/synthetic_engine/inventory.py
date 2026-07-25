"""Synthetic T+1 lots; no portfolio/account integration."""
from dataclasses import replace
from .types import InventoryState, SyntheticLot

def known(inventory: InventoryState) -> bool:
    return inventory.pending_buy_quantity is not None and inventory.pending_sell_quantity is not None and all(
        lot.acquired_trade_date is not None and lot.quantity is not None and lot.locked_quantity is not None for lot in inventory.lots)

def sellable_quantity(inventory: InventoryState, trade_date: str, t_plus_one: bool) -> int:
    if not known(inventory): raise ValueError("UNKNOWN_INVENTORY")
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

def advance_settlement_day(inventory: InventoryState) -> InventoryState:
    if not known(inventory): raise ValueError("UNKNOWN_INVENTORY")
    if inventory.pending_buy_quantity or inventory.pending_sell_quantity: raise ValueError("PENDING_INTENTS_REQUIRE_EXPLICIT_CANCELLATION")
    return inventory
