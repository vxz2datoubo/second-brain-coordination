"""Total, deterministic, fail-closed validation for synthetic inputs."""
from datetime import date
from .calendar import accepts_orders
from .inventory import inventory_error,sellable_quantity
from .types import InformationSet,MarketState,MatchMode,OrderSide,SecurityStatus,SyntheticOrder,SyntheticRuleSnapshot,ValidationResult,NUMERIC_SAFETY_BOUND
SYNTHETIC_CAPABILITY='SYNTHETIC_RESEARCH_ONLY'
def reject(code):return ValidationResult(False,(code,))
def _number(value,positive=False):return isinstance(value,int) and not isinstance(value,bool) and abs(value)<=NUMERIC_SAFETY_BOUND and (value>0 if positive else True)
def _date(value):
 try:return date.fromisoformat(value)
 except (TypeError,ValueError):return None
def validate(state,inventory,order):
 if not isinstance(state,MarketState):return reject('INVALID_MARKET_STATE_OBJECT')
 if not isinstance(order,SyntheticOrder):return reject('INVALID_ORDER_OBJECT')
 if not isinstance(state.information,InformationSet):return reject('INVALID_INFORMATION_SET')
 info=state.information
 if info.source_capability!=SYNTHETIC_CAPABILITY:return reject('UNKNOWN_OR_UNSUPPORTED_CAPABILITY')
 if not _number(info.available_at_ns) or info.available_at_ns<0 or not _number(order.available_at_ns) or order.available_at_ns<0:return reject('INVALID_TIMESTAMP')
 if order.available_at_ns>info.available_at_ns:return reject('FUTURE_INFORMATION')
 if not isinstance(order.order_id,str) or not order.order_id:return reject('INVALID_ORDER_ID')
 if not isinstance(state.rule_snapshot,SyntheticRuleSnapshot):return reject('INVALID_RULE_SNAPSHOT_OBJECT')
 rule=state.rule_snapshot
 if not all(isinstance(v,str) and v for v in (rule.snapshot_id,rule.exchange,rule.board,rule.trade_date,rule.price_unit,rule.quantity_unit,rule.suspension_behavior,rule.version)):return reject('MALFORMED_RULE_SNAPSHOT')
 if _date(rule.trade_date) is None or _date(state.trade_date) is None or rule.trade_date!=state.trade_date:return reject('INVALID_TRADE_DATE')
 if not isinstance(rule.t_plus_one_enabled,bool):return reject('INVALID_T_PLUS_ONE_FLAG')
 if not _number(rule.price_limit_low) or not _number(rule.price_limit_high) or rule.price_limit_low>rule.price_limit_high:return reject('INVALID_RULE_NUMERIC_LIMIT')
 if not isinstance(rule.permitted_phases,tuple) or not rule.permitted_phases or not all(type(x).__name__=='SessionPhase' for x in rule.permitted_phases):return reject('INVALID_PERMITTED_PHASES')
 if not isinstance(state.phase,type(rule.permitted_phases[0])):return reject('INVALID_SESSION_PHASE')
 if not isinstance(state.security_status,SecurityStatus):return reject('INVALID_SECURITY_STATUS')
 if state.security_status is not SecurityStatus.ACTIVE:return reject('SECURITY_UNAVAILABLE')
 if not accepts_orders(state.phase) or state.phase not in rule.permitted_phases:return reject('ILLEGAL_PHASE')
 if not isinstance(order.side,OrderSide):return reject('INVALID_SIDE')
 if not isinstance(order.match_mode,MatchMode) or order.match_mode is MatchMode.UNKNOWN:return reject('UNSUPPORTED_MATCH_MODE')
 if not _number(order.quantity,True):return reject('INVALID_QUANTITY')
 if not _number(order.limit_price) or not rule.price_limit_low<=order.limit_price<=rule.price_limit_high:return reject('INVALID_OR_OUT_OF_LIMIT_PRICE')
 if order.partial_fill_quantity is not None and (not _number(order.partial_fill_quantity,True) or order.partial_fill_quantity>=order.quantity):return reject('INVALID_PARTIAL_FILL_QUANTITY')
 error=inventory_error(inventory)
 if error:return reject(error)
 if order.side is OrderSide.SELL:
  try:available=sellable_quantity(inventory,rule.t_plus_one_enabled)
  except ValueError as error:return reject(str(error))
  if order.quantity>available:return reject('T_PLUS_ONE_OR_INSUFFICIENT_INVENTORY')
 return ValidationResult(True,('SYNTHETIC_VALID',))
