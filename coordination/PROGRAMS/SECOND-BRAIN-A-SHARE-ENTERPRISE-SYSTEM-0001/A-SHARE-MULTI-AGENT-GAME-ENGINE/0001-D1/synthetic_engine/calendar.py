"""Closed synthetic session state machine."""
from .types import SessionPhase

_NEXT = {
    SessionPhase.PREOPEN: (SessionPhase.CALL_AUCTION, SessionPhase.SUSPENDED),
    SessionPhase.CALL_AUCTION: (SessionPhase.AUCTION_FREEZE, SessionPhase.SUSPENDED),
    SessionPhase.AUCTION_FREEZE: (SessionPhase.CONTINUOUS_AM, SessionPhase.SUSPENDED),
    SessionPhase.CONTINUOUS_AM: (SessionPhase.MIDDAY_BREAK, SessionPhase.SUSPENDED),
    SessionPhase.MIDDAY_BREAK: (SessionPhase.CONTINUOUS_PM, SessionPhase.SUSPENDED),
    SessionPhase.CONTINUOUS_PM: (SessionPhase.CLOSING_AUCTION, SessionPhase.SUSPENDED),
    SessionPhase.CLOSING_AUCTION: (SessionPhase.CLOSED, SessionPhase.SUSPENDED),
    SessionPhase.CLOSED: (SessionPhase.PREOPEN,), SessionPhase.SUSPENDED: (SessionPhase.CLOSED,),
}

def transition(current: SessionPhase, target: SessionPhase) -> SessionPhase:
    if target not in _NEXT.get(current, ()):
        raise ValueError("UNSUPPORTED_SESSION_TRANSITION")
    return target

def accepts_orders(phase: SessionPhase) -> bool:
    return phase in (SessionPhase.CALL_AUCTION, SessionPhase.CONTINUOUS_AM, SessionPhase.CONTINUOUS_PM, SessionPhase.CLOSING_AUCTION)
