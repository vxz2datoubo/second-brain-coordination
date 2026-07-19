from __future__ import annotations

from pathlib import Path
import tempfile
import textwrap
import unittest

from brain_core import SuperBrainV01
from brain_core.foundation_data_governance import (
    DataQualityRecord,
    HistoricalTradeReplayAdapter,
    MockMboAdapter,
    build_data_layer_policies,
    negotiate_capability_requests,
)


SAMPLE_CSV = """\
date,open,high,low,close,volume
2026-07-10,10.0,10.3,9.9,10.2,100000
2026-07-11,10.2,10.5,10.1,10.4,120000
2026-07-14,10.4,10.6,10.2,10.3,90000
"""


class FoundationDataGovernanceTests(unittest.TestCase):
    def make_brain(self) -> tuple[SuperBrainV01, Path]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        sample = root / "replay.csv"
        sample.write_text(textwrap.dedent(SAMPLE_CSV), encoding="utf-8")
        return SuperBrainV01(root), sample

    def test_historical_replay_adapter_preserves_lineage_and_quality(self):
        brain, sample = self.make_brain()
        adapter = HistoricalTradeReplayAdapter(root=brain.root, symbol="300418", timeframe="1d")
        result = adapter.normalize(sample)

        self.assertEqual(result["source_record"]["source_type"], "historical_trade_replay")
        self.assertEqual(result["market_data_record"]["symbol"], "300418")
        self.assertEqual(result["market_data_record"]["metadata"]["lineage"]["raw_path"], str(sample).replace("\\", "/"))
        self.assertEqual(result["lineage_record"]["provider_name"], "local_file")
        self.assertEqual(result["lineage_record"]["raw_ref"], str(sample).replace("\\", "/"))
        self.assertEqual(result["quality_record"]["grade"], "B")
        self.assertFalse(result["quality_record"]["blocking"])
        self.assertTrue(result["price_bars"])
        self.assertEqual(result["price_bars"][0]["metadata"]["effective_at"], "2026-07-10")
        self.assertEqual(result["price_bars"][0]["metadata"]["available_at"], "2026-07-10")

    def test_capability_negotiation_blocks_sequence_sensitive_analysis(self):
        brain, _sample = self.make_brain()
        adapter = MockMboAdapter(root=brain.root, symbol="300418", timeframe="1d")
        quality = DataQualityRecord(
            object_id="quality_1",
            flags=[{"flag": "field_semantics_unverified", "blocking": False}],
            quality_flags=[{"flag": "field_semantics_unverified", "blocking": False}],
            summary="mock sample",
        )
        result = negotiate_capability_requests(
            descriptor=adapter.capability_descriptor(),
            requested_capabilities=["market_by_order", "sequence_no", "cancel_event"],
            quality_record=quality,
        )

        self.assertEqual(result["recommended_output"], "no_signal")
        self.assertEqual(result["allowed_capabilities"], [])
        self.assertTrue(any(item["capability"] == "market_by_order" for item in result["downgraded_capabilities"]))
        self.assertTrue(any(item["capability"] == "sequence_no" for item in result["blocked_capabilities"]))
        self.assertTrue(any("cancel-rate" in note for note in result["notes"]))

    def test_data_layer_policies_map_to_current_runtime_boundaries(self):
        brain, _sample = self.make_brain()
        policies = build_data_layer_policies(brain.root)

        self.assertEqual(set(policies.keys()), {"raw", "normalized", "features", "signals", "reports", "runtime_logs"})
        self.assertTrue(policies["raw"].immutable)
        self.assertFalse(policies["raw"].tracked_in_git)
        self.assertIn("super_brain_v01.sqlite", policies["normalized"].storage_target)
        self.assertTrue(policies["reports"].tracked_in_git)
        self.assertTrue(policies["runtime_logs"].immutable)

    def test_foundation_report_writes_back_into_mother_system(self):
        brain, sample = self.make_brain()
        result = brain.foundation_data_governance_report(
            {
                "symbol": "300418",
                "timeframe": "1d",
                "data_path": str(sample),
            }
        )

        self.assertEqual(result["task_id"], "FOUNDATION-DATA-GOVERNANCE-0001")
        self.assertEqual(result["branch_or_worktree"], "unavailable:not-a-git-repo")
        self.assertTrue(result["confirmation_no_live_trading_changes"])
        self.assertIn("raw", result["data_layers"])
        self.assertIn("historical_trade_replay", result["adapter_catalog"]["implemented"])
        self.assertEqual(
            result["adapter_catalog"]["implemented"]["historical_trade_replay"]["capability_descriptor"]["capabilities"]["historical_replay"]["status"],
            "available",
        )
        self.assertEqual(
            result["adapter_catalog"]["templates"]["tdx_quant"]["implementation_status"],
            "Interface",
        )
        self.assertEqual(
            result["writeback"]["skill_registry_entry"]["skill_name"],
            "mother_system.foundation_data_governance_v2",
        )
        self.assertEqual(
            result["writeback"]["module_status_record"]["module_name"],
            "foundation_data_governance_v2",
        )
        self.assertEqual(
            result["writeback"]["self_evolution_log"]["trigger"],
            "foundation_data_governance_v2_registered",
        )
        self.assertEqual(
            result["writeback"]["bulletin_state_record"]["recent_event"],
            "foundation_data_governance_v2_registered",
        )
        status = brain.status()
        self.assertEqual(status["module_status"]["foundation_data_governance_v2"], "Implemented")
