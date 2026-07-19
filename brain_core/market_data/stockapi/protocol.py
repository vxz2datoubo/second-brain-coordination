"""Protocol constants and command builders for StockAPI TCP V2.

The command builders return bytes but never log credentials. Runtime callers
must inject account/password through environment variables or a local secret
provider. This module is offline-safe and performs no network I/O.
"""

from __future__ import annotations

from enum import Enum
from typing import Final


class StreamType(str, Enum):
    MARKET = "Market"
    ORDER = "Order"
    QUEUE = "Queue"
    TRAN = "Tran"


class SessionState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    WAIT_GREETING = "WAIT_GREETING"
    LOGIN_SENT = "LOGIN_SENT"
    AUTHENTICATED = "AUTHENTICATED"
    SUBSCRIBE_SENT = "SUBSCRIBE_SENT"
    STREAMING = "STREAMING"
    BACKOFF = "BACKOFF"
    KICKED = "KICKED"
    STOPPING = "STOPPING"


ON_DEMAND_PORTS: Final[dict[int, StreamType]] = {
    18100: StreamType.MARKET,
    18103: StreamType.ORDER,
    18104: StreamType.QUEUE,
    18105: StreamType.TRAN,
}

FULL_PUSH_PORTS: Final[dict[int, StreamType]] = {
    28100: StreamType.MARKET,
    28103: StreamType.ORDER,
    28104: StreamType.QUEUE,
    28105: StreamType.TRAN,
}

CONNECTION_MODES: Final[tuple[str, ...]] = ("on_demand", "full_push")
MAX_ON_DEMAND_SYMBOLS: Final[int] = 50
CONTROL_MESSAGES: Final[set[str]] = {"HeartBeat", "Market", "Order", "Tran", "Queue"}


def _frame(command: str) -> bytes:
    return f"<{command}>".encode("utf-8")


def build_login_command(account: str, password: str) -> bytes:
    return _frame(f"DL,{account},{password}")


def build_subscribe_command(account: str, password: str, symbol: str) -> bytes:
    return _frame(f"DY2,{account},{password},{symbol}")


def build_unsubscribe_command(account: str, password: str, symbol: str) -> bytes:
    return _frame(f"QXDY2,{account},{password},{symbol}")


def build_query_subscribe_command(account: str, password: str) -> bytes:
    return _frame(f"CXDY2,{account},{password}")


def redact_command(command: bytes | str) -> str:
    text = command.decode("utf-8", errors="replace") if isinstance(command, bytes) else str(command)
    if text.startswith("<DL,") or text.startswith("<DY2,") or text.startswith("<QXDY2,") or text.startswith("<CXDY2,"):
        parts = text.strip("<>").split(",")
        if len(parts) >= 3:
            parts[1] = "***"
            parts[2] = "***"
        return "<" + ",".join(parts) + ">"
    return text

