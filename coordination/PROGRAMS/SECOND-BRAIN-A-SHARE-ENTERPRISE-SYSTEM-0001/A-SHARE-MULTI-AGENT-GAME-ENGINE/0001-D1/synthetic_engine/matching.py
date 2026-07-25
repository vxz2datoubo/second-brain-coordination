"""Declared synthetic match modes only; no market matching inference."""
from .types import MatchMode, OutcomeStatus

def resolve(order):
    if order.match_mode is MatchMode.UNKNOWN: return OutcomeStatus.UNKNOWN_OUTCOME, 0, order.quantity, "UNKNOWN_SYNTHETIC_MATCH"
    if order.match_mode is MatchMode.FULL: return OutcomeStatus.FILLED, order.quantity, 0, "SYNTHETIC_FULL_FILL"
    if order.match_mode is MatchMode.PARTIAL:
        filled = order.partial_fill_quantity
        if not isinstance(filled, int) or filled <= 0 or filled >= order.quantity: return OutcomeStatus.INVALID_OR_BLOCKED, 0, order.quantity, "INVALID_PARTIAL_FILL_QUANTITY"
        return OutcomeStatus.PARTIALLY_FILLED, filled, order.quantity-filled, "SYNTHETIC_PARTIAL_FILL"
    if order.match_mode is MatchMode.NO_FILL_CARRY: return OutcomeStatus.UNFILLED_CARRIED, 0, order.quantity, "SYNTHETIC_NO_FILL_CARRY"
    return OutcomeStatus.UNFILLED_CANCELLED, 0, order.quantity, "SYNTHETIC_NO_FILL_CANCEL"
