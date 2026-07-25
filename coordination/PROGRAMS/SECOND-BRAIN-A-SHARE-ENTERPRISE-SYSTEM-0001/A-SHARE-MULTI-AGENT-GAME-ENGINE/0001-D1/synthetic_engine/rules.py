"""Fail-closed validation for a declared synthetic rule snapshot."""
from .calendar import accepts_orders
from .inventory import known, sellable_quantity
from .types import OrderSide, SecurityStatus, ValidationResult

SYNTHETIC_CAPABILITY = "SYNTHETIC_RESEARCH_ONLY"

def reject(code: str) -> ValidationResult: return ValidationResult(False, (code,))

def validate(state, inventory, order) -> ValidationResult:
    info = state.information
    if info is None or info.source_capability != SYNTHETIC_CAPABILITY: return reject("UNKNOWN_OR_UNSUPPORTED_CAPABILITY")
    if info.available_at_ns is None or order.available_at_ns is None: return reject("UNKNOWN_AVAILABLE_AT")
    if order.available_at_ns > info.available_at_ns: return reject("FUTURE_INFORMATION")
    rule = state.rule_snapshot
    if rule is None or not all((rule.snapshot_id, rule.exchange, rule.board, rule.trade_date, rule.version)): return reject("MALFORMED_RULE_SNAPSHOT")
    if rule.t_plus_one_enabled is None or rule.price_limit_low is None or rule.price_limit_high is None or not rule.permitted_phases: return reject("UNKNOWN_RULE_SNAPSHOT")
    if not rule.price_unit or not rule.quantity_unit: return reject("UNKNOWN_UNIT")
    if rule.price_limit_low > rule.price_limit_high or state.trade_date != rule.trade_date: return reject("MALFORMED_RULE_SNAPSHOT")
    if state.security_status is None or state.security_status is SecurityStatus.UNKNOWN: return reject("UNKNOWN_SECURITY_STATUS")
    if state.security_status is SecurityStatus.SUSPENDED or state.phase is None or state.phase.name == "SUSPENDED": return reject("SECURITY_SUSPENDED")
    if not accepts_orders(state.phase) or state.phase not in rule.permitted_phases: return reject("ILLEGAL_PHASE")
    if order.side not in (OrderSide.BUY, OrderSide.SELL): return reject("INVALID_SIDE")
    if not isinstance(order.quantity, int) or isinstance(order.quantity, bool) or order.quantity <= 0: return reject("INVALID_QUANTITY")
    if not isinstance(order.limit_price, int) or isinstance(order.limit_price, bool): return reject("INVALID_PRICE")
    if not rule.price_limit_low <= order.limit_price <= rule.price_limit_high: return reject("PRICE_LIMIT_VIOLATION")
    if not known(inventory): return reject("UNKNOWN_INVENTORY")
    if order.side is OrderSide.SELL:
        try: available = sellable_quantity(inventory, state.trade_date, rule.t_plus_one_enabled)
        except ValueError as error: return reject(str(error))
        if order.quantity > available: return reject("T_PLUS_ONE_OR_INSUFFICIENT_INVENTORY")
    return ValidationResult(True, ("SYNTHETIC_VALID",))
