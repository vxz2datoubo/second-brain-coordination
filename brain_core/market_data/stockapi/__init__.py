"""StockAPI TCP V2 offline/hardened adapter.

This package is a production-before-readonly candidate. It does not connect to
StockAPI by default, does not hold credentials, and does not clear raw L2 gates.
"""

from .framing import ByteFrameParser, FrameRecord
from .gap_detector import GapDetector
from .http_backfill import BackfillRequest, MockHttpBackfillClient
from .parser import StockApiPayloadParser
from .protocol import (
    CONNECTION_MODES,
    FULL_PUSH_PORTS,
    ON_DEMAND_PORTS,
    SessionState,
    StreamType,
    build_login_command,
    build_query_subscribe_command,
    build_subscribe_command,
    build_unsubscribe_command,
)
from .raw_writer import AppendOnlyRawWriter
from .runtime_client import RuntimeClientConfig, StockApiRuntimeClient

__all__ = [
    "AppendOnlyRawWriter",
    "BackfillRequest",
    "ByteFrameParser",
    "CONNECTION_MODES",
    "FULL_PUSH_PORTS",
    "FrameRecord",
    "GapDetector",
    "MockHttpBackfillClient",
    "ON_DEMAND_PORTS",
    "RuntimeClientConfig",
    "SessionState",
    "StockApiPayloadParser",
    "StockApiRuntimeClient",
    "StreamType",
    "build_login_command",
    "build_query_subscribe_command",
    "build_subscribe_command",
    "build_unsubscribe_command",
]

