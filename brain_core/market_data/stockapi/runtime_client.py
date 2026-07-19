"""Read-only runtime client skeleton for StockAPI TCP V2.

The class is intentionally inert unless `allow_network=True`. Tests and Codex
tasks must keep it disabled; WorkBuddy owns real credentials and runtime probes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import random
from typing import Any

from .protocol import (
    FULL_PUSH_PORTS,
    MAX_ON_DEMAND_SYMBOLS,
    ON_DEMAND_PORTS,
    SessionState,
    StreamType,
    build_login_command,
    build_query_subscribe_command,
    build_subscribe_command,
    redact_command,
)


@dataclass
class RuntimeClientConfig:
    host: str = ""
    mode: str = "on_demand"
    symbols: list[str] = field(default_factory=list)
    account_env: str = "STOCKAPI_ACCOUNT"
    password_env: str = "STOCKAPI_PASSWORD"
    allow_network: bool = False
    max_queue_size: int = 10_000
    min_backoff_seconds: float = 5.0
    max_backoff_seconds: float = 300.0
    max_reconnects_per_hour: int = 12


class StockApiRuntimeClient:
    def __init__(self, config: RuntimeClientConfig) -> None:
        self.config = config
        self.state = SessionState.DISCONNECTED
        self.last_redacted_command = ""
        self.reconnect_attempts = 0

    def validate_config(self) -> None:
        if self.config.mode not in {"on_demand", "full_push"}:
            raise ValueError("mode must be on_demand or full_push")
        if self.config.mode == "on_demand" and len(self.config.symbols) > MAX_ON_DEMAND_SYMBOLS:
            raise ValueError("on_demand mode supports at most 50 symbols")
        if self.config.allow_network and not self.config.host:
            raise ValueError("host is required when allow_network=True")

    def credentials_from_env(self) -> tuple[str, str]:
        account = os.environ.get(self.config.account_env, "")
        password = os.environ.get(self.config.password_env, "")
        if self.config.allow_network and (not account or not password):
            raise RuntimeError("StockAPI credentials are required for live runtime; values are not logged")
        return account, password

    def port_map(self) -> dict[int, StreamType]:
        return ON_DEMAND_PORTS if self.config.mode == "on_demand" else FULL_PUSH_PORTS

    def build_startup_commands(self, *, symbol: str) -> list[bytes]:
        account, password = self.credentials_from_env()
        commands = [build_login_command(account, password)]
        if self.config.mode == "on_demand":
            commands.append(build_subscribe_command(account, password, symbol))
            commands.append(build_query_subscribe_command(account, password))
        self.last_redacted_command = redact_command(commands[-1])
        return commands

    def on_greeting(self) -> SessionState:
        if self.state not in {SessionState.CONNECTING, SessionState.WAIT_GREETING}:
            self.state = SessionState.WAIT_GREETING
        return self.state

    def on_login_sent(self) -> SessionState:
        self.state = SessionState.LOGIN_SENT
        return self.state

    def on_login_response(self, payload: str) -> SessionState:
        text = str(payload or "")
        if text.startswith("DL,") and ("OK" in text.upper() or "SUCCESS" in text.upper() or "1" in text.split(",")):
            self.state = SessionState.AUTHENTICATED
        else:
            self.state = SessionState.BACKOFF
        return self.state

    def can_subscribe(self) -> bool:
        return self.state == SessionState.AUTHENTICATED

    def on_subscribe_sent(self) -> SessionState:
        if not self.can_subscribe():
            raise RuntimeError("subscribe is blocked until login success is verified")
        self.state = SessionState.SUBSCRIBE_SENT
        return self.state

    def on_streaming_data(self) -> SessionState:
        if self.state in {SessionState.AUTHENTICATED, SessionState.SUBSCRIBE_SENT, SessionState.STREAMING}:
            self.state = SessionState.STREAMING
        return self.state

    def on_kick(self) -> SessionState:
        self.state = SessionState.KICKED
        return self.state

    def next_backoff_seconds(self) -> float:
        self.reconnect_attempts += 1
        base = min(self.config.max_backoff_seconds, self.config.min_backoff_seconds * (2 ** max(0, self.reconnect_attempts - 1)))
        return base + random.uniform(0.0, min(1.0, self.config.min_backoff_seconds))

    def connect(self) -> None:
        self.validate_config()
        if not self.config.allow_network:
            raise RuntimeError("Network is disabled for this hardened adapter skeleton")
        raise NotImplementedError("WorkBuddy-owned runtime implementation must supply real socket loop")

    def runtime_capability_descriptor(self) -> dict[str, Any]:
        return {
            "adapter_name": "StockApiTcpV2HardenedAdapter",
            "implementation_status": "Implemented_Experimental",
            "runtime_status": "SkeletonOnly",
            "network_enabled": bool(self.config.allow_network),
            "supported_streams": [item.value for item in self.port_map().values()],
            "governance": {
                "research_only": True,
                "live_trading_enabled": False,
                "raw_l2_gate_cleared": False,
                "requires_workbuddy_runtime_samples": True,
            },
        }

