"""Named synthetic fixtures; they are not data samples."""
from .types import *

RULE = SyntheticRuleSnapshot("synthetic-v1", "SYNTH", "BOARD", "2026-07-26", 1, 10, "synthetic-price", "synthetic-quantity", (SessionPhase.CALL_AUCTION, SessionPhase.CONTINUOUS_AM, SessionPhase.CONTINUOUS_PM, SessionPhase.CLOSING_AUCTION), True, "block", "1")
INFO = InformationSet("SYNTHETIC_RESEARCH_ONLY", 100)
INVENTORY = InventoryState((SyntheticLot("seasoned", "2026-07-25", 5),))

def market(phase=SessionPhase.CONTINUOUS_AM, status=SecurityStatus.ACTIVE, rule=RULE, info=INFO): return MarketState(phase, "2026-07-26", status, rule, info)
def order(name, side=OrderSide.BUY, qty=2, price=5, mode=MatchMode.FULL, partial=None, available=100): return SyntheticOrder(name, side, qty, price, available, mode, partial)

FIXTURES = (
 ("F01_preopen_rejected", market(SessionPhase.PREOPEN), INVENTORY, order("F01"), OutcomeStatus.INVALID_OR_BLOCKED),
 ("F02_call_auction_fill", market(SessionPhase.CALL_AUCTION), INVENTORY, order("F02"), OutcomeStatus.FILLED),
 ("F03_auction_freeze_rejected", market(SessionPhase.AUCTION_FREEZE), INVENTORY, order("F03"), OutcomeStatus.INVALID_OR_BLOCKED),
 ("F04_continuous_am_partial", market(), INVENTORY, order("F04", mode=MatchMode.PARTIAL, partial=1), OutcomeStatus.PARTIALLY_FILLED),
 ("F05_midday_break_rejected", market(SessionPhase.MIDDAY_BREAK), INVENTORY, order("F05"), OutcomeStatus.INVALID_OR_BLOCKED),
 ("F06_continuous_pm_cancel", market(SessionPhase.CONTINUOUS_PM), INVENTORY, order("F06", mode=MatchMode.NO_FILL_CANCEL), OutcomeStatus.UNFILLED_CANCELLED),
 ("F07_closing_carry", market(SessionPhase.CLOSING_AUCTION), INVENTORY, order("F07", mode=MatchMode.NO_FILL_CARRY), OutcomeStatus.UNFILLED_CARRIED),
 ("F08_suspended_rejected", market(status=SecurityStatus.SUSPENDED), INVENTORY, order("F08"), OutcomeStatus.INVALID_OR_BLOCKED),
 ("F09_price_limit_rejected", market(), INVENTORY, order("F09", price=11), OutcomeStatus.INVALID_OR_BLOCKED),
 ("F10_fresh_t1_sell_rejected", market(), InventoryState((SyntheticLot("fresh", "2026-07-26", 2),)), order("F10", side=OrderSide.SELL, qty=1), OutcomeStatus.INVALID_OR_BLOCKED),
 ("F11_seasoned_sell_fill", market(), INVENTORY, order("F11", side=OrderSide.SELL, qty=1), OutcomeStatus.FILLED),
 ("F12_unknown_match_abstains", market(), INVENTORY, order("F12", mode=MatchMode.UNKNOWN), OutcomeStatus.UNKNOWN_OUTCOME),
)
