"""Small deterministic research-only vertical slice; it has no network or order adapter."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


class ValidationError(ValueError):
    """A governed record is invalid, unavailable, or must abstain."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise ValidationError(f"invalid_timestamp:{value}") from error
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class Bar:
    event_id: str
    symbol: str
    exchange: str
    event_time: str
    available_at: str
    observed_at: str
    receive_time: str
    entered_system_at: str
    as_of: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    suspended: bool | None = False
    is_st: bool | None = False
    adjusted: bool = False
    adjustment_method: str = "none"
    limit_rule_version: str = "ashare-v1"
    source_id: str = "synthetic-public-safe"
    dataset_version: str = "1.0.0"
    license: str = "CC0-1.0"
    capability_level: str = "HISTORICAL_BAR"
    entitlement_status: str = "confirmed"
    corporate_action_note: str = "none"

    @property
    def trading_day(self) -> date:
        return parse_time(self.event_time).date()

    def payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GateRecord:
    event_id: str
    outcome: str
    reason: str | None = None


@dataclass
class ReplayResult:
    events: list[Bar]
    event_ledger: list[dict[str, Any]]
    quarantine: list[GateRecord]
    checkpoint: dict[str, Any]

    @property
    def core_hash(self) -> str:
        return digest([entry["event_id"] for entry in self.event_ledger])


@dataclass
class SimulationConfig:
    initial_cash: float = 100_000.0
    max_position_weight: float = 0.25
    max_turnover: float = 1.0
    commission_bps: float = 2.5
    min_commission: float = 5.0
    stamp_duty_bps_sell: float = 5.0
    transfer_fee_bps_sh: float = 0.1
    fixed_slippage_bps: float = 5.0
    volume_impact_bps: float = 0.0
    rule_version: str = "ashare-research-v1"
    no_trade_gate: bool = True


class ContractRuntime:
    """Cross-field guards that complement the frozen P1 JSON Schemas."""

    ALLOWED_CAPABILITIES = {"HISTORICAL_BAR", "FIVE_LEVEL_SNAPSHOT", "TEN_LEVEL_SNAPSHOT", "L2_AGGREGATE"}

    def validate_bar(self, bar: Bar, requested_as_of: str) -> None:
        if not bar.symbol or not bar.exchange:
            raise ValidationError("missing_identity")
        if bar.capability_level not in self.ALLOWED_CAPABILITIES:
            raise ValidationError("unsupported_capability")
        if bar.entitlement_status != "confirmed":
            raise ValidationError("entitlement_not_confirmed")
        if bar.capability_level != "HISTORICAL_BAR":
            raise ValidationError("capability_not_permitted_for_fixture")
        if not bar.source_id or not bar.dataset_version or not bar.license:
            raise ValidationError("missing_lineage")
        if parse_time(bar.available_at) > parse_time(requested_as_of):
            raise ValidationError("future_available_at")
        if parse_time(bar.event_time) > parse_time(bar.available_at):
            raise ValidationError("available_before_event")
        numeric_values = (bar.open, bar.high, bar.low, bar.close)
        if any(value < 0 for value in numeric_values) or (bar.volume is not None and bar.volume < 0):
            raise ValidationError("negative_market_value")
        if bar.suspended not in {True, False, None} or bar.is_st not in {True, False, None}:
            raise ValidationError("invalid_market_state_semantics")
        if not (bar.low <= bar.open <= bar.high and bar.low <= bar.close <= bar.high):
            raise ValidationError("invalid_ohlc")

    def envelope(self, bar: Bar, run_id: str, trace_id: str) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "object_id": bar.event_id,
            "record_type": "PriceBar",
            "run_id": run_id,
            "trace_id": trace_id,
            "no_trade_gate": True,
            "authority_write": False,
            "lineage": {"source_refs": [bar.source_id], "artifact_refs": [digest(bar.payload())]},
            "temporal": {key: getattr(bar, key) for key in ("event_time", "available_at", "observed_at", "receive_time", "entered_system_at", "as_of")},
            "capability": {"level": bar.capability_level, "entitlement_status": bar.entitlement_status, "gate_result": "allowed"},
        }


class SchemaRegistry:
    """Minimal explicit P1/P2 compatibility gate; unknown major versions are rejected."""

    def __init__(self) -> None:
        self.known = {"FoundationSharedEnvelope": "1.0.0", "TemporalSemantics": "1.0.0", "OfflineReplay": "1.0.0"}

    def require_compatible(self, name: str, version: str) -> None:
        if name not in self.known:
            raise ValidationError("unknown_schema")
        if version.split(".", 1)[0] != self.known[name].split(".", 1)[0]:
            raise ValidationError("incompatible_schema_major")


def _coerce_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def load_fixture(path: Path, requested_as_of: str) -> tuple[list[Bar], list[GateRecord], dict[str, Any]]:
    """Load CSV, JSON, or JSONL without modifying source files."""
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".csv":
        rows = list(csv.DictReader(text.splitlines()))
    elif suffix == ".jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    elif suffix == ".json":
        parsed = json.loads(text)
        rows = parsed["records"] if isinstance(parsed, dict) else parsed
    else:
        raise ValidationError("unsupported_fixture_format")
    bars: list[Bar] = []
    quarantine: list[GateRecord] = []
    runtime = ContractRuntime()
    for index, row in enumerate(rows):
        try:
            normalized = dict(row)
            for key in ("open", "high", "low", "close", "volume"):
                normalized[key] = float(normalized[key])
            for key in ("suspended", "is_st", "adjusted"):
                normalized[key] = _coerce_bool(normalized.get(key, False))
            normalized.setdefault("event_id", f"{normalized.get('symbol', 'unknown')}:{index}")
            bar = Bar(**normalized)
            runtime.validate_bar(bar, requested_as_of)
            bars.append(bar)
        except (KeyError, TypeError, ValidationError, ValueError) as error:
            quarantine.append(GateRecord(str(row.get("event_id", f"row:{index}")), "QUARANTINED", str(error)))
    manifest = {
        "dataset_id": path.stem,
        "dataset_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "record_count": len(bars),
        "quarantine_count": len(quarantine),
        "license": "CC0-1.0 synthetic fixture",
        "synthetic": True,
        "formats_supported": ["csv", "json", "jsonl"],
    }
    return bars, quarantine, manifest


class DeterministicReplay:
    def __init__(self, requested_as_of: str, run_id: str, trace_id: str) -> None:
        self.requested_as_of = requested_as_of
        self.run_id = run_id
        self.trace_id = trace_id
        self.runtime = ContractRuntime()

    def run(self, bars: Iterable[Bar], checkpoint_path: Path | None = None, resume: bool = False) -> ReplayResult:
        seen: set[str] = set()
        near_seen: dict[tuple[str, str], Bar] = {}
        quarantine: list[GateRecord] = []
        accepted: list[Bar] = []
        for bar in bars:
            try:
                self.runtime.validate_bar(bar, self.requested_as_of)
                fingerprint = digest(bar.payload())
                if bar.event_id in seen or fingerprint in seen:
                    quarantine.append(GateRecord(bar.event_id, "DUPLICATE", "idempotency_key_seen"))
                    continue
                near_key = (bar.symbol, bar.event_time)
                if near_key in near_seen and abs(near_seen[near_key].close - bar.close) <= 0.001:
                    quarantine.append(GateRecord(bar.event_id, "NEAR_DUPLICATE", "same_symbol_time_near_price"))
                    continue
                seen.update({bar.event_id, fingerprint})
                near_seen[near_key] = bar
                accepted.append(bar)
            except ValidationError as error:
                quarantine.append(GateRecord(bar.event_id, "QUARANTINED", str(error)))
        ordered = sorted(accepted, key=lambda item: (parse_time(item.event_time), item.symbol, item.event_id))
        start = 0
        if resume and checkpoint_path and checkpoint_path.exists():
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            if checkpoint.get("input_hash") != digest([bar.payload() for bar in ordered]):
                raise ValidationError("checkpoint_input_mismatch")
            start = int(checkpoint["next_index"])
        ledger: list[dict[str, Any]] = []
        for index, bar in enumerate(ordered):
            if index < start:
                continue
            ledger.append({"local_sequence": index + 1, "event_id": bar.event_id, "event_time": bar.event_time, "available_at": bar.available_at, "envelope": self.runtime.envelope(bar, self.run_id, self.trace_id)})
            if checkpoint_path:
                snapshot = {"next_index": index + 1, "input_hash": digest([item.payload() for item in ordered]), "last_event_id": bar.event_id, "run_id": self.run_id}
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                checkpoint_path.write_text(canonical(snapshot), encoding="utf-8")
        checkpoint = {"next_index": len(ordered), "input_hash": digest([item.payload() for item in ordered]), "run_id": self.run_id}
        return ReplayResult(ordered, ledger, quarantine, checkpoint)


def candidate_signals(events: list[Bar]) -> list[dict[str, Any]]:
    """Three transparent candidates, usable only after the emitting bar is available."""
    result: list[dict[str, Any]] = []
    history: list[Bar] = []
    for bar in events:
        if len(history) >= 2:
            semantic_window = (history[-2], history[-1], bar)
            unknown_fields = sorted({
                field_name
                for item in semantic_window
                for field_name in ("volume", "suspended", "is_st")
                if getattr(item, field_name) is None
            })
            if unknown_fields:
                result.append({
                    "signal_id": f"signal:{bar.event_id}",
                    "symbol": bar.symbol,
                    "event_id": bar.event_id,
                    "available_at": bar.available_at,
                    "action": "ABSTAIN",
                    "confidence": 0.0,
                    "features": {"momentum_2": None, "volume_ratio_2": None, "breakout_2": None},
                    "status": "candidate",
                    "reason": "REQUIRED_MARKET_SEMANTICS_UNKNOWN",
                    "unknown_fields": unknown_fields,
                    "failure_conditions": ["required_market_semantics_unknown", "no_execution_adapter"],
                })
                history.append(bar)
                continue
        if len(history) >= 2 and bar.suspended is False:
            momentum = (bar.close / history[-2].close) - 1.0
            volume_ratio = bar.volume / max(1.0, (history[-1].volume + history[-2].volume) / 2.0)
            breakout = bar.close > max(history[-1].high, history[-2].high)
            score = (1 if momentum > 0 else -1) + (1 if volume_ratio >= 1.0 else 0) + (1 if breakout else 0)
            action = "BUY_CANDIDATE" if score >= 2 else "SELL_CANDIDATE" if score <= -1 else "ABSTAIN"
            result.append({"signal_id": f"signal:{bar.event_id}", "symbol": bar.symbol, "event_id": bar.event_id, "available_at": bar.available_at, "action": action, "confidence": round(min(0.9, 0.35 + abs(score) * 0.15), 2), "features": {"momentum_2": round(momentum, 6), "volume_ratio_2": round(volume_ratio, 6), "breakout_2": breakout}, "status": "candidate", "failure_conditions": ["synthetic_dataset", "historical_bar_only", "no_execution_adapter"]})
        history.append(bar)
    return result


def _limit_pct(bar: Bar) -> float:
    if bar.is_st is None:
        raise ValidationError("st_status_unknown")
    return 0.05 if bar.is_st else 0.10


def simulate_portfolio(events: list[Bar], signals: list[dict[str, Any]], config: SimulationConfig) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Research ledger. Candidate actions cannot reach a broker or external transport."""
    ordered_signals = sorted(signals, key=lambda item: (parse_time(item["available_at"]), item["signal_id"]))
    signal_index = 0
    eligible: dict[str, dict[str, Any]] = {}
    cash = config.initial_cash
    turnover = 0.0
    positions: dict[str, dict[str, Any]] = {}
    ledger: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    prior_close: dict[str, float] = {}
    for bar in events:
        # A feature emitted after a close can only be acted on by a later event.
        while signal_index < len(ordered_signals) and parse_time(ordered_signals[signal_index]["available_at"]) <= parse_time(bar.event_time):
            candidate = ordered_signals[signal_index]
            eligible[candidate["symbol"]] = candidate
            signal_index += 1
        signal = eligible.pop(bar.symbol, None)
        if not signal or signal["action"] == "ABSTAIN":
            prior_close[bar.symbol] = bar.close
            continue
        action = signal["action"]
        reason: str | None = None
        executed = False
        quantity = 0
        if bar.volume is None or bar.suspended is None or bar.is_st is None:
            reason = "REQUIRED_MARKET_SEMANTICS_UNKNOWN"
        elif bar.suspended:
            reason = "SUSPENDED"
        else:
            change = (bar.close / prior_close[bar.symbol] - 1.0) if bar.symbol in prior_close else 0.0
            if action == "BUY_CANDIDATE" and change >= _limit_pct(bar):
                reason = "LIMIT_UP_BUY_RESTRICTED"
            elif action == "SELL_CANDIDATE" and change <= -_limit_pct(bar):
                reason = "LIMIT_DOWN_SELL_RESTRICTED"
            elif action == "BUY_CANDIDATE":
                budget = min(cash, config.initial_cash * config.max_position_weight)
                fill = bar.close * (1 + (config.fixed_slippage_bps + config.volume_impact_bps) / 10_000)
                quantity = int(budget // fill)
                fee = max(config.min_commission, quantity * fill * config.commission_bps / 10_000) if quantity else 0.0
                if quantity <= 0 or quantity * fill + fee > cash:
                    reason = "INSUFFICIENT_CASH"
                elif turnover + quantity * fill / config.initial_cash > config.max_turnover:
                    reason = "MAX_TURNOVER"
                else:
                    cash -= quantity * fill + fee
                    turnover += quantity * fill / config.initial_cash
                    position = positions.setdefault(bar.symbol, {"quantity": 0, "sellable": 0, "acquired_day": bar.trading_day.isoformat()})
                    position["quantity"] += quantity
                    position["acquired_day"] = bar.trading_day.isoformat()
                    executed = True
            elif action == "SELL_CANDIDATE":
                position = positions.get(bar.symbol, {"quantity": 0, "sellable": 0, "acquired_day": None})
                if position["quantity"] <= 0:
                    reason = "NO_POSITION"
                elif position["acquired_day"] == bar.trading_day.isoformat():
                    reason = "T_PLUS_ONE_LOCK"
                else:
                    quantity = position["quantity"]
                    fill = bar.close * (1 - (config.fixed_slippage_bps + config.volume_impact_bps) / 10_000)
                    fee = max(config.min_commission, quantity * fill * config.commission_bps / 10_000)
                    fee += quantity * fill * config.stamp_duty_bps_sell / 10_000
                    if bar.exchange == "SH":
                        fee += quantity * fill * config.transfer_fee_bps_sh / 10_000
                    cash += quantity * fill - fee
                    turnover += quantity * fill / config.initial_cash
                    position["quantity"] = 0
                    executed = True
        decision = {"event_id": bar.event_id, "symbol": bar.symbol, "action": action, "research_only": True, "no_trade_gate": config.no_trade_gate, "executed_in_simulation": executed, "reason": reason, "quantity": quantity}
        decisions.append(decision)
        ledger.append({**decision, "cash_after": round(cash, 2), "position_after": positions.get(bar.symbol, {}).get("quantity", 0), "turnover_after": round(turnover, 6), "rule_version": config.rule_version})
        prior_close[bar.symbol] = bar.close
    return ledger, decisions


def validate(events: list[Bar], portfolio_ledger: list[dict[str, Any]], config: SimulationConfig) -> dict[str, Any]:
    unknown_fields = sorted({
        field_name
        for bar in events
        for field_name in ("volume", "suspended", "is_st")
        if getattr(bar, field_name) is None
    })
    if unknown_fields:
        return {
            "validation_status": "ABSTAIN",
            "reason": "required_market_semantics_unknown",
            "unknown_fields": unknown_fields,
            "executed_simulated_actions": 0,
            "cost_proxy": 0.0,
            "research_only": True,
        }
    if len(events) < 6:
        return {"validation_status": "ABSTAIN", "reason": "insufficient_temporal_observations", "research_only": True}
    ordered = sorted(events, key=lambda item: parse_time(item.event_time))
    n = len(ordered)
    split = {"train": [ordered[0].event_id, ordered[n // 2 - 1].event_id], "validation": [ordered[n // 2].event_id, ordered[(3 * n) // 4 - 1].event_id], "test": [ordered[(3 * n) // 4].event_id, ordered[-1].event_id]}
    executed = [entry for entry in portfolio_ledger if entry["executed_in_simulation"]]
    rejected = [entry for entry in portfolio_ledger if not entry["executed_in_simulation"]]
    total_cost_proxy = len(executed) * config.min_commission
    return {"validation_status": "EXPERIMENTAL_ONLY", "time_split": split, "walk_forward_windows": max(1, n - 4), "random_shuffle": False, "executed_simulated_actions": len(executed), "abstentions_or_rejections": len(rejected), "cost_proxy": total_cost_proxy, "cost_before_result": "not_economic_evidence", "cost_after_result": "not_economic_evidence", "robustness": "not_proven_on_synthetic_fixture", "research_only": True}


@dataclass
class KnowledgeAtom:
    atom_id: str
    content: str
    status: str
    source_refs: list[str]
    evidence_quality: str
    gpt_access: str = "FULL_SEMANTIC_ACCESS"
    transport_visibility: str = "PUBLIC_SAFE"
    relations: list[dict[str, str]] = field(default_factory=list)


class KnowledgeGateway:
    HARD_SECRET_MARKERS = ("api_key", "token=", "password", "private_key", "cookie")

    def __init__(self, atoms: list[KnowledgeAtom], revision: str = "synthetic-r1") -> None:
        self.atoms = atoms
        self.revision = revision

    def query(self, text: str, budget: int, statuses: set[str] | None = None) -> dict[str, Any]:
        if any(marker in text.lower() for marker in self.HARD_SECRET_MARKERS):
            return {"query_id": digest(text)[:16], "abstention": "DENIED_HARD_SECRET", "atoms": [], "omitted_due_to_context_budget": [], "knowledge_revision": self.revision}
        allowed = statuses or {"candidate", "approved"}
        tokens = {token.lower() for token in text.split()}
        chosen: list[dict[str, Any]] = []
        omitted: list[str] = []
        used = 0
        for atom in sorted(self.atoms, key=lambda item: item.atom_id):
            if atom.status not in allowed or atom.gpt_access != "FULL_SEMANTIC_ACCESS":
                continue
            relevance = bool(tokens.intersection(atom.content.lower().split()))
            if not relevance:
                continue
            cost = max(1, len(atom.content) // 4)
            if used + cost > budget:
                omitted.append(atom.atom_id)
                continue
            chosen.append(asdict(atom))
            used += cost
        return {"query_id": digest({"text": text, "budget": budget})[:16], "knowledge_revision": self.revision, "atoms": chosen, "relations": [relation for atom in chosen for relation in atom["relations"]], "conflicts": [], "unknowns": [], "source_lineage": [source for atom in chosen for source in atom["source_refs"]], "omitted_due_to_context_budget": omitted, "context_budget_report": {"budget": budget, "used": used}, "gpt_access": "FULL_SEMANTIC_ACCESS"}


def learning_packet(run_manifest: dict[str, Any], validation_report: dict[str, Any], evidence_hash: str) -> dict[str, Any]:
    packet = {"packet_id": "lp-" + digest({"run": run_manifest["run_id"], "evidence": evidence_hash})[:16], "packet_content_hash": "", "idempotency_key": "", "base_knowledge_revision": "synthetic-r1", "processor_version": "p2-offline-1.0.0", "status": "candidate", "authority_write": False, "facts": ["offline synthetic replay completed"], "constraints": ["research_only", "NO_TRADE", "synthetic_not_market_evidence"], "validation": validation_report, "evidence_refs": [evidence_hash], "evidence_quality": "synthetic_fixture", "relations": [{"type": "evidence:SUPPORTS", "target": run_manifest["run_id"]}]}
    packet["packet_content_hash"] = digest({key: value for key, value in packet.items() if key not in {"packet_content_hash", "idempotency_key"}})
    packet["idempotency_key"] = packet["packet_id"] + "-" + packet["packet_content_hash"][:12]
    return packet


class OfflineResearchRunner:
    def __init__(self, fixture: Path, output_dir: Path, requested_as_of: str = "2026-01-31T23:59:59Z") -> None:
        self.fixture = fixture
        self.output_dir = output_dir
        self.requested_as_of = requested_as_of
        self.run_id = "run-" + digest({"fixture": fixture.name, "as_of": requested_as_of})[:16]
        self.trace_id = "trace-" + self.run_id[-12:]

    def run(self, resume: bool = False) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        bars, ingest_quarantine, dataset_manifest = load_fixture(self.fixture, self.requested_as_of)
        replay = DeterministicReplay(self.requested_as_of, self.run_id, self.trace_id).run(bars, self.output_dir / "checkpoint.json", resume)
        signals = candidate_signals(replay.events)
        portfolio, decisions = simulate_portfolio(replay.events, signals, SimulationConfig())
        report = validate(replay.events, portfolio, SimulationConfig())
        knowledge = KnowledgeGateway([KnowledgeAtom("atom-signal", "candidate momentum volume breakout signal from synthetic replay", "candidate", [dataset_manifest["dataset_hash"]], "synthetic_fixture"), KnowledgeAtom("atom-risk", "T+1 suspension limit and cost constraints remain research only", "candidate", ["ashare-research-v1"], "synthetic_fixture")])
        context = knowledge.query("momentum volume T+1", 200)
        run_manifest = {"run_id": self.run_id, "trace_id": self.trace_id, "research_only": True, "no_trade_gate": True, "fixture": str(self.fixture.name), "dataset_hash": dataset_manifest["dataset_hash"], "event_hash": replay.core_hash, "code_version": "p2-offline-1.0.0"}
        evidence = {"run_manifest": run_manifest, "dataset_manifest": dataset_manifest, "capability_decisions": [asdict(item) for item in ingest_quarantine + replay.quarantine], "replay_event_ledger": replay.event_ledger, "research_decision_ledger": decisions, "portfolio_ledger": portfolio, "validation_report": report, "context_bundle": context, "unknowns": ["Synthetic fixture is not a real-market evidence source", "No private/local knowledge gateway is implemented in public repository"]}
        evidence_hash = digest(evidence)
        packet = learning_packet(run_manifest, report, evidence_hash)
        artifacts = {"RunManifest.json": run_manifest, "DatasetManifest.json": dataset_manifest, "ConfigurationSnapshot.json": asdict(SimulationConfig()), "CapabilityDecisionLog.json": evidence["capability_decisions"], "ReplayEventLedger.json": replay.event_ledger, "ResearchDecisionLedger.json": decisions, "PortfolioLedger.json": portfolio, "ValidationReport.json": report, "EvidenceLedger.json": evidence, "ContextBundle.json": context, "LearningPacket.json": packet}
        hashes = {}
        for name, payload in artifacts.items():
            text = canonical(payload)
            (self.output_dir / name).write_text(text + "\n", encoding="utf-8")
            hashes[name] = digest(payload)
        bundle = {"run_id": self.run_id, "content_hashes": hashes, "evidence_hash": evidence_hash, "rollback": "delete output directory; no external state changed", "status": "CANDIDATE_RESEARCH_ONLY"}
        (self.output_dir / "ReproducibilityBundleManifest.json").write_text(canonical(bundle) + "\n", encoding="utf-8")
        return {"run_manifest": run_manifest, "validation_report": report, "bundle": bundle, "packet": packet, "output_dir": str(self.output_dir)}
