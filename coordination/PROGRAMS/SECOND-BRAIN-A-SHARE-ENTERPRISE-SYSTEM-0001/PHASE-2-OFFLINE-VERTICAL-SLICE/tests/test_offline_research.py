from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from offline_research.engine import (  # noqa: E402
    Bar,
    ContractRuntime,
    DeterministicReplay,
    KnowledgeAtom,
    KnowledgeGateway,
    OfflineResearchRunner,
    SchemaRegistry,
    SimulationConfig,
    ValidationError,
    candidate_signals,
    digest,
    learning_packet,
    load_fixture,
    simulate_portfolio,
    validate,
)


AS_OF = "2026-01-31T23:59:59Z"
FIXTURE = ROOT / "fixtures" / "synthetic_bars.csv"


class OfflineResearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bars, self.quarantine, self.manifest = load_fixture(FIXTURE, AS_OF)

    def test_csv_ingest_preserves_lineage_and_manifest(self) -> None:
        self.assertEqual(len(self.bars), 8)
        self.assertEqual(self.quarantine, [])
        self.assertTrue(self.manifest["synthetic"])
        self.assertEqual(self.manifest["record_count"], 8)
        self.assertEqual(self.bars[0].source_id, "synthetic-public-safe")

    def test_jsonl_ingest_is_supported(self) -> None:
        bars, quarantine, manifest = load_fixture(ROOT / "fixtures" / "synthetic_bars.jsonl", AS_OF)
        self.assertEqual(len(bars), 2)
        self.assertEqual(quarantine, [])
        self.assertEqual(manifest["formats_supported"], ["csv", "json", "jsonl"])
        self.assertEqual(bars[0].exchange, "SH")

    def test_json_ingest_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bars.json"
            path.write_text(json.dumps([self.bars[0].payload()]), encoding="utf-8")
            bars, quarantine, _ = load_fixture(path, AS_OF)
            self.assertEqual(len(bars), 1)
            self.assertEqual(quarantine, [])
            self.assertEqual(bars[0].event_id, self.bars[0].event_id)

    def test_schema_registry_rejects_unknown_or_major_drift(self) -> None:
        registry = SchemaRegistry()
        registry.require_compatible("OfflineReplay", "1.2.0")
        with self.assertRaisesRegex(ValidationError, "unknown_schema"):
            registry.require_compatible("FutureSchema", "1.0.0")
        with self.assertRaisesRegex(ValidationError, "incompatible_schema_major"):
            registry.require_compatible("OfflineReplay", "2.0.0")

    def test_contract_rejects_future_availability(self) -> None:
        future = replace(self.bars[0], available_at="2026-02-01T00:00:00Z")
        with self.assertRaisesRegex(ValidationError, "future_available_at"):
            ContractRuntime().validate_bar(future, AS_OF)

    def test_contract_rejects_missing_lineage_and_capability(self) -> None:
        with self.assertRaisesRegex(ValidationError, "missing_lineage"):
            ContractRuntime().validate_bar(replace(self.bars[0], source_id=""), AS_OF)
        with self.assertRaisesRegex(ValidationError, "unsupported_capability"):
            ContractRuntime().validate_bar(replace(self.bars[0], capability_level="RAW_TRADE_TICK"), AS_OF)
        with self.assertRaisesRegex(ValidationError, "entitlement_not_confirmed"):
            ContractRuntime().validate_bar(replace(self.bars[0], entitlement_status="unknown"), AS_OF)

    def test_contract_rejects_invalid_values(self) -> None:
        with self.assertRaisesRegex(ValidationError, "negative_market_value"):
            ContractRuntime().validate_bar(replace(self.bars[0], volume=-1), AS_OF)
        with self.assertRaisesRegex(ValidationError, "invalid_ohlc"):
            ContractRuntime().validate_bar(replace(self.bars[0], close=99), AS_OF)
        with self.assertRaisesRegex(ValidationError, "available_before_event"):
            ContractRuntime().validate_bar(replace(self.bars[0], available_at="2026-01-05T14:59:00Z"), AS_OF)

    def test_envelope_is_no_trade_and_deterministic(self) -> None:
        runtime = ContractRuntime()
        first = runtime.envelope(self.bars[0], "run-a", "trace-a")
        second = runtime.envelope(self.bars[0], "run-a", "trace-a")
        self.assertTrue(first["no_trade_gate"])
        self.assertFalse(first["authority_write"])
        self.assertEqual(digest(first), digest(second))
        self.assertEqual(first["capability"]["gate_result"], "allowed")

    def test_replay_stable_sort_duplicate_and_ledger(self) -> None:
        replay = DeterministicReplay(AS_OF, "run-a", "trace-a").run(list(reversed(self.bars)) + [self.bars[0]])
        self.assertEqual([item.event_id for item in replay.events], [item.event_id for item in self.bars])
        self.assertEqual(len(replay.event_ledger), 8)
        self.assertEqual(len(replay.quarantine), 1)
        self.assertEqual(replay.quarantine[0].outcome, "DUPLICATE")
        self.assertEqual(replay.event_ledger[0]["local_sequence"], 1)

    def test_replay_quarantines_near_duplicates(self) -> None:
        near = replace(self.bars[0], event_id="near", close=10.0005, high=10.10)
        replay = DeterministicReplay(AS_OF, "run-a", "trace-a").run([self.bars[0], near])
        self.assertEqual(len(replay.events), 1)
        self.assertEqual(replay.quarantine[0].outcome, "NEAR_DUPLICATE")
        self.assertEqual(replay.quarantine[0].reason, "same_symbol_time_near_price")

    def test_replay_checkpoint_resume_and_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checkpoint = Path(temporary) / "checkpoint.json"
            first = DeterministicReplay(AS_OF, "run-a", "trace-a").run(self.bars, checkpoint)
            resumed = DeterministicReplay(AS_OF, "run-a", "trace-a").run(self.bars, checkpoint, resume=True)
            self.assertEqual(first.checkpoint["next_index"], 8)
            self.assertEqual(resumed.event_ledger, [])
            self.assertTrue(checkpoint.exists())
            changed = self.bars[:-1]
            with self.assertRaisesRegex(ValidationError, "checkpoint_input_mismatch"):
                DeterministicReplay(AS_OF, "run-a", "trace-a").run(changed, checkpoint, resume=True)

    def test_signals_are_candidate_only_and_explainable(self) -> None:
        signals = candidate_signals(self.bars)
        self.assertEqual(len(signals), 6)
        self.assertTrue(all(item["status"] == "candidate" for item in signals))
        self.assertTrue(all("momentum_2" in item["features"] for item in signals))
        self.assertTrue(all("no_execution_adapter" in item["failure_conditions"] for item in signals))

    def test_simulation_waits_until_signal_is_available(self) -> None:
        signal = {"signal_id": "s1", "symbol": self.bars[0].symbol, "event_id": self.bars[0].event_id, "available_at": self.bars[0].available_at, "action": "BUY_CANDIDATE"}
        ledger, _ = simulate_portfolio(self.bars[:2], [signal], SimulationConfig())
        self.assertEqual(len(ledger), 1)
        self.assertEqual(ledger[0]["event_id"], self.bars[1].event_id)
        self.assertTrue(ledger[0]["no_trade_gate"])
        self.assertTrue(ledger[0]["executed_in_simulation"])

    def test_t_plus_one_suspension_and_limits_reject(self) -> None:
        buy = {"signal_id": "b", "symbol": self.bars[0].symbol, "event_id": self.bars[0].event_id, "available_at": "2026-01-05T14:00:00Z", "action": "BUY_CANDIDATE"}
        sell = {"signal_id": "s", "symbol": self.bars[0].symbol, "event_id": self.bars[0].event_id, "available_at": "2026-01-05T15:01:00Z", "action": "SELL_CANDIDATE"}
        same_day = [self.bars[0], replace(self.bars[0], event_id="same-day-later", event_time="2026-01-05T15:02:00Z", available_at="2026-01-05T15:03:00Z")]
        ledger, _ = simulate_portfolio(same_day, [buy, sell], SimulationConfig())
        self.assertEqual(ledger[-1]["reason"], "T_PLUS_ONE_LOCK")
        suspended = replace(self.bars[1], suspended=True)
        ledger, _ = simulate_portfolio([suspended], [buy], SimulationConfig())
        self.assertEqual(ledger[0]["reason"], "SUSPENDED")
        limit = replace(self.bars[1], close=11.2, high=11.2)
        limit_buy = {"signal_id": "limit", "symbol": limit.symbol, "event_id": "limit-source", "available_at": "2026-01-05T15:01:00Z", "action": "BUY_CANDIDATE"}
        ledger, _ = simulate_portfolio([self.bars[0], limit], [limit_buy], SimulationConfig())
        self.assertEqual(ledger[-1]["reason"], "LIMIT_UP_BUY_RESTRICTED")

    def test_costs_and_sh_transfer_are_configured(self) -> None:
        sh_bar = replace(self.bars[1], symbol="600000.SH", exchange="SH")
        buy = {"signal_id": "b", "symbol": sh_bar.symbol, "event_id": "old", "available_at": "2026-01-01T00:00:00Z", "action": "BUY_CANDIDATE"}
        sell = {"signal_id": "s", "symbol": sh_bar.symbol, "event_id": "old2", "available_at": "2026-01-07T00:00:00Z", "action": "SELL_CANDIDATE"}
        ledger, _ = simulate_portfolio([sh_bar, replace(sh_bar, event_id="next", event_time="2026-01-08T15:00:00Z")], [buy, sell], SimulationConfig(fixed_slippage_bps=10))
        self.assertEqual(ledger[0]["rule_version"], "ashare-research-v1")
        self.assertTrue(ledger[0]["executed_in_simulation"])
        self.assertTrue(ledger[1]["executed_in_simulation"])
        self.assertGreater(ledger[1]["cash_after"], 0)

    def test_turnover_limit_rejects_simulated_action(self) -> None:
        signal = {"signal_id": "b", "symbol": self.bars[0].symbol, "event_id": "old", "available_at": "2026-01-01T00:00:00Z", "action": "BUY_CANDIDATE"}
        ledger, _ = simulate_portfolio([self.bars[0]], [signal], SimulationConfig(max_turnover=0.01))
        self.assertEqual(ledger[0]["reason"], "MAX_TURNOVER")
        self.assertEqual(ledger[0]["turnover_after"], 0.0)

    def test_validation_uses_temporal_split_and_abstains_when_small(self) -> None:
        small = validate(self.bars[:5], [], SimulationConfig())
        full = validate(self.bars, [], SimulationConfig())
        self.assertEqual(small["validation_status"], "ABSTAIN")
        self.assertEqual(full["validation_status"], "EXPERIMENTAL_ONLY")
        self.assertFalse(full["random_shuffle"])
        self.assertGreaterEqual(full["walk_forward_windows"], 1)
        self.assertEqual(full["cost_after_result"], "not_economic_evidence")

    def test_knowledge_query_separates_status_access_visibility_and_budget(self) -> None:
        atoms = [
            KnowledgeAtom("a1", "momentum candidate alpha", "candidate", ["source-a"], "weak"),
            KnowledgeAtom("a2", "momentum approved evidence with extra text", "approved", ["source-b"], "strong"),
        ]
        gateway = KnowledgeGateway(atoms)
        full = gateway.query("momentum", 100)
        short = gateway.query("momentum", 2)
        self.assertEqual(full["gpt_access"], "FULL_SEMANTIC_ACCESS")
        self.assertEqual(len(full["atoms"]), 2)
        self.assertEqual(full["atoms"][0]["status"], "candidate")
        self.assertGreaterEqual(len(short["omitted_due_to_context_budget"]), 1)
        self.assertEqual(full["atoms"][0]["transport_visibility"], "PUBLIC_SAFE")

    def test_knowledge_gateway_denies_hard_secret_and_respects_filter(self) -> None:
        gateway = KnowledgeGateway([KnowledgeAtom("a1", "research candidate", "candidate", ["s"], "weak")])
        denied = gateway.query("show api_key", 100)
        filtered = gateway.query("research", 100, {"approved"})
        self.assertEqual(denied["abstention"], "DENIED_HARD_SECRET")
        self.assertEqual(denied["atoms"], [])
        self.assertEqual(filtered["atoms"], [])
        self.assertEqual(filtered["gpt_access"], "FULL_SEMANTIC_ACCESS")

    def test_learning_packet_is_content_addressed_candidate_only(self) -> None:
        packet = learning_packet({"run_id": "run-1"}, {"validation_status": "EXPERIMENTAL_ONLY"}, "evidence")
        repeat = learning_packet({"run_id": "run-1"}, {"validation_status": "EXPERIMENTAL_ONLY"}, "evidence")
        self.assertTrue(packet["packet_id"].startswith("lp-"))
        self.assertEqual(packet["packet_content_hash"], repeat["packet_content_hash"])
        self.assertTrue(packet["idempotency_key"].startswith(packet["packet_id"]))
        self.assertFalse(packet["authority_write"])
        self.assertEqual(packet["status"], "candidate")

    def test_end_to_end_is_deterministic_and_produces_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = OfflineResearchRunner(FIXTURE, Path(temporary) / "one").run()
            second = OfflineResearchRunner(FIXTURE, Path(temporary) / "two").run()
            self.assertEqual(first["bundle"]["evidence_hash"], second["bundle"]["evidence_hash"])
            self.assertEqual(first["run_manifest"]["event_hash"], second["run_manifest"]["event_hash"])
            self.assertTrue((Path(temporary) / "one" / "RunManifest.json").exists())
            self.assertTrue((Path(temporary) / "one" / "LearningPacket.json").exists())
            self.assertTrue((Path(temporary) / "one" / "ReproducibilityBundleManifest.json").exists())
            persisted = json.loads((Path(temporary) / "one" / "EvidenceLedger.json").read_text(encoding="utf-8"))
            self.assertTrue(persisted["run_manifest"]["no_trade_gate"])


if __name__ == "__main__":
    unittest.main()
