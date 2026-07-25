"""Single pure reducer for declared synthetic inputs."""
from .inventory import apply_buy, apply_sell, carry
from .matching import resolve
from .rules import validate
from .types import OrderSide, OutcomeStatus, SyntheticMatchOutcome

def reduce_order(state, inventory, order):
    checked = validate(state, inventory, order)
    if not checked.accepted:
        quantity=order.quantity if isinstance(order,object) and isinstance(getattr(order,'quantity',None),int) and not isinstance(getattr(order,'quantity',None),bool) and order.quantity>0 else 0
        return SyntheticMatchOutcome(OutcomeStatus.INVALID_OR_BLOCKED, 0, quantity, inventory, checked.reason_codes)
    status, filled, unfilled, reason = resolve(order)
    if status is OutcomeStatus.UNKNOWN_OUTCOME: return SyntheticMatchOutcome(status, 0, unfilled, inventory, (reason,))
    next_inventory = inventory
    try:
        if filled and order.side is OrderSide.BUY: next_inventory = apply_buy(inventory, state.trade_date, filled, order.order_id)
        elif filled and order.side is OrderSide.SELL: next_inventory = apply_sell(inventory, filled, state.rule_snapshot.t_plus_one_enabled)
        if status is OutcomeStatus.UNFILLED_CARRIED: next_inventory = carry(next_inventory, order.side.value, unfilled)
    except ValueError as error:
        return SyntheticMatchOutcome(OutcomeStatus.INVALID_OR_BLOCKED,0,order.quantity,inventory,(str(error),))
    return SyntheticMatchOutcome(status, filled, unfilled, next_inventory, (reason,))
