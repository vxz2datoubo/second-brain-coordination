from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "event_coverage.py"
SPEC = importlib.util.spec_from_file_location("w5_event_coverage", MODULE_PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def registry():
    return {
        "schema_version": "SourceRegistry/v1",
        "sources": [
            {
                "source_id": "official-core",
                "source_class": "OFFICIAL_PRIMARY",
                "source_grade": "A1",
                "coverage_roles": ["FIRST_PARTY", "COMPANY_DISCLOSURE", "POLICY_REGULATORY"],
                "enabled": True,
            },
            {
                "source_id": "market-wire",
                "source_class": "PROFESSIONAL_MARKET_SOURCE",
                "source_grade": "B2",
                "coverage_roles": ["MARKET_WIRE"],
                "enabled": True,
            },
            {
                "source_id": "tech-primary",
                "source_class": "INSTITUTIONAL_PRIMARY",
                "source_grade": "B1",
                "coverage_roles": ["TECHNOLOGY_RELEASE"],
                "enabled": True,
            },
            {
                "source_id": "proxy-primary",
                "source_class": "INSTITUTIONAL_PRIMARY",
                "source_grade": "B1",
                "coverage_roles": ["OVERSEAS_PROXY"],
                "enabled": True,
            },
        ],
    }


def intent(*, kind="MARKET_ATTRIBUTION", grade="B", anomaly=True):
    return {
        "intent_class": kind,
        "target_symbols": ["SZ300058"],
        "proxy_symbols": ["DEEPSEEK"],
        "previous_close_at": "2026-08-13T15:00:00+08:00",
        "anomaly_or_query_at": "2026-08-14T10:00:00+08:00",
        "data_grade": grade,
        "price_anomaly_unexplained": anomaly,
    }


def scanned_sources(*, include_tech=True, include_proxy=False):
    values = ["official-core", "market-wire"]
    if include_tech:
        values.append("tech-primary")
    if include_proxy:
        values.append("proxy-primary")
    return values


def event(
    event_id="deepseek-harness",
    *,
    source_id="tech-primary",
    source_chain_id="deepseek-harness-primary",
    available_at="2026-08-13T19:56:32+08:00",
    target_symbols=None,
    proxy_symbols=None,
):
    return {
        "event_id": event_id,
        "event_type": "TECHNOLOGY_EVENT",
        "source_id": source_id,
        "source_chain_id": source_chain_id,
        "available_at": available_at,
        "market_effective_at": available_at,
        "target_symbols": [] if target_symbols is None else target_symbols,
        "proxy_symbols": ["DEEPSEEK"] if proxy_symbols is None else proxy_symbols,
        "mechanism": "agent infrastructure -> marketing-agent capability candidate",
        "evidence_refs": [f"public-safe://{event_id}"],
    }


def claim(
    text="Harness is a relevant candidate catalyst, not proven unique cause",
    *,
    claim_id="c1",
    claim_type="MODEL_INFERENCE",
    event_ids=None,
    evidence_refs=None,
    causal=False,
    participant=False,
):
    return {
        "claim_id": claim_id,
        "claim_type": claim_type,
        "text": text,
        "evidence_event_ids": ["deepseek-harness"] if event_ids is None else event_ids,
        "evidence_refs": ["public-safe://cross-sectional-check"] if evidence_refs is None else evidence_refs,
        "causal_identification_evidence": causal,
        "participant_intent_evidence": participant,
    }


class EventCoverageGateTests(unittest.TestCase):
    def run_gate(
        self,
        *,
        intent_value=None,
        scanned=None,
        proxies=None,
        events=None,
        claims=None,
    ):
        return mod.run_event_coverage_gate(
            intent=intent() if intent_value is None else intent_value,
            source_registry=registry(),
            scanned_source_ids=scanned_sources() if scanned is None else scanned,
            scanned_proxy_symbols=["DEEPSEEK"] if proxies is None else proxies,
            events=[event()] if events is None else events,
            claims=[claim()] if claims is None else claims,
        )

    def test_01_harness_is_point_in_time_candidate_but_not_unique_cause(self):
        result = self.run_gate(
            claims=[
                claim(
                    text="DeepSeek Harness 就是因为蓝标上涨的唯一原因",
                    claim_type="CAUSAL_HYPOTHESIS",
                    causal=False,
                )
            ]
        )
        report = result["event_coverage_report"]
        row = result["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(report["disposition"], "READY_FOR_SYNTHESIS")
        self.assertEqual(report["candidate_event_ids"], ["deepseek-harness"])
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertIn("UNIQUE_CAUSAL_CLAIM_UNSUPPORTED", row["reason_codes"])
        self.assertEqual(result["disposition"], "ABSTAIN")

    def test_02_complete_no_news_scan_preserves_unknown(self):
        result = self.run_gate(
            events=[],
            claims=[
                claim(
                    text="公开事件原因仍未知",
                    claim_type="UNKNOWN",
                    event_ids=[],
                    evidence_refs=[],
                )
            ],
        )
        report = result["event_coverage_report"]
        self.assertEqual(report["disposition"], "PRICE_ANOMALY_UNRESOLVED")
        self.assertTrue(report["event_backfill_required"])
        self.assertEqual(report["candidate_event_ids"], [])
        self.assertEqual(result["disposition"], "PRICE_ANOMALY_UNRESOLVED")

    def test_03_data_grade_c_blocks_microstructure_and_participant_intent(self):
        result = self.run_gate(
            intent_value=intent(grade="C"),
            claims=[
                claim(
                    text="主力出货，CVD 与盘口意图确认",
                    claim_type="MODEL_INFERENCE",
                    participant=False,
                )
            ],
        )
        row = result["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertIn("MICROSTRUCTURE_TERM_EXCEEDS_DATA_GRADE", row["reason_codes"])
        self.assertIn("PARTICIPANT_INTENT_UNSUPPORTED", row["reason_codes"])

    def test_04_future_event_cannot_satisfy_point_in_time_evidence(self):
        future = event(available_at="2026-08-14T10:30:00+08:00")
        result = self.run_gate(
            events=[future],
            claims=[claim(claim_type="CAUSAL_HYPOTHESIS")],
        )
        report = result["event_coverage_report"]
        row = result["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(report["candidate_event_ids"], [])
        self.assertEqual(report["future_event_ids_ignored"], ["deepseek-harness"])
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertIn("EVIDENCE_NOT_POINT_IN_TIME_RELEVANT_OR_INDEPENDENT", row["reason_codes"])

    def test_05_syndicated_copies_count_as_one_independent_chain(self):
        first = event(event_id="wire-copy-1", source_id="market-wire", source_chain_id="same-origin")
        second = event(
            event_id="wire-copy-2",
            source_id="tech-primary",
            source_chain_id="same-origin",
            available_at="2026-08-13T20:00:00+08:00",
        )
        result = self.run_gate(events=[first, second], claims=[])
        report = result["event_coverage_report"]
        self.assertEqual(report["independent_source_chain_count"], 1)
        self.assertEqual(len(report["candidate_event_ids"]), 1)
        self.assertEqual(report["candidate_event_ids"], ["wire-copy-1"])

    def test_06_missing_mandatory_source_role_is_incomplete_not_no_event(self):
        result = self.run_gate(scanned=scanned_sources(include_tech=False), events=[], claims=[])
        report = result["event_coverage_report"]
        self.assertEqual(report["disposition"], "EVENT_COVERAGE_INCOMPLETE")
        self.assertIn("TECHNOLOGY_RELEASE", report["unresolved_source_gaps"])
        self.assertEqual(report["coverage_grade"], "INCOMPLETE")

    def test_07_portfolio_latest_requires_explicit_proxy_scan(self):
        result = self.run_gate(
            intent_value=intent(kind="PORTFOLIO_LATEST", anomaly=False),
            scanned=scanned_sources(include_proxy=True),
            proxies=[],
            claims=[],
        )
        report = result["event_coverage_report"]
        self.assertEqual(report["disposition"], "EVENT_COVERAGE_INCOMPLETE")
        self.assertEqual(report["unresolved_proxy_gaps"], ["DEEPSEEK"])
        self.assertEqual(report["window_start"], "2026-08-13T02:00:00Z")

    def test_08_portfolio_latest_complete_proxy_scan_can_reach_ready(self):
        result = self.run_gate(
            intent_value=intent(kind="PORTFOLIO_LATEST", anomaly=False),
            scanned=scanned_sources(include_proxy=True),
            proxies=["DEEPSEEK"],
            claims=[],
        )
        self.assertEqual(result["event_coverage_report"]["disposition"], "READY_FOR_SYNTHESIS")

    def test_09_supply_demand_language_is_downgraded_at_grade_c(self):
        result = self.run_gate(
            intent_value=intent(grade="C", anomaly=False),
            claims=[claim(text="高位抛压很大", claim_type="MODEL_INFERENCE")],
        )
        row = result["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "DOWNGRADE")
        self.assertIn("SUPPLY_DEMAND_LANGUAGE_REQUIRES_PRICE_BEHAVIOR_DOWNGRADE", row["reason_codes"])

    def test_10_deterministic_replay_has_stable_digest(self):
        first = self.run_gate()
        second = self.run_gate()
        self.assertEqual(first, second)
        self.assertEqual(first["result_digest"], second["result_digest"])

    def test_11_all_authority_flags_remain_false(self):
        result = self.run_gate()
        for authority in (
            result["authority"],
            result["event_coverage_report"]["authority"],
            result["claim_evidence_ledger"]["authority"],
        ):
            self.assertTrue(authority)
            self.assertTrue(all(value is False for value in authority.values()))

    def test_12_empty_required_roles_cannot_be_caller_selected(self):
        malformed = dict(intent())
        malformed["required_coverage_roles"] = []
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(intent_value=malformed)
        self.assertEqual(ctx.exception.code, "INTENT_FIELDS_INVALID")

    def test_13_unknown_or_disabled_scanned_source_fails_closed(self):
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(scanned=["official-core", "market-wire", "tech-primary", "fake-source"])
        self.assertEqual(ctx.exception.code, "SCANNED_SOURCE_UNKNOWN_OR_DISABLED")

    def test_14_event_source_grade_is_derived_from_registry(self):
        result = self.run_gate()
        self.assertEqual(result["event_coverage_report"]["candidate_event_ids"], ["deepseek-harness"])
        bad = event()
        bad["source_grade"] = "A1"
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(events=[bad])
        self.assertEqual(ctx.exception.code, "EVENT_FIELDS_INVALID")

    def test_15_causal_claim_cannot_run_before_coverage_complete(self):
        result = self.run_gate(
            scanned=scanned_sources(include_tech=False),
            claims=[claim(text="Harness 可能是候选催化", claim_type="CAUSAL_HYPOTHESIS", causal=False)],
        )
        row = result["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertIn("CAUSAL_CLAIM_BEFORE_COVERAGE_READY", row["reason_codes"])

    def test_16_timezone_naive_query_time_fails_closed(self):
        malformed = intent()
        malformed["anomaly_or_query_at"] = "2026-08-14T10:00:00"
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(intent_value=malformed)
        self.assertEqual(ctx.exception.code, "QUERY_TIME_INVALID_TIMEZONE_REQUIRED")

    def test_17_duplicate_event_id_fails_closed(self):
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(events=[event(), event()])
        self.assertEqual(ctx.exception.code, "EVENT_ID_DUPLICATE")

    def test_18_fake_event_evidence_id_cannot_support_claim(self):
        result = self.run_gate(
            claims=[claim(event_ids=["fabricated-event-id"], claim_type="CAUSAL_HYPOTHESIS")]
        )
        row = result["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertEqual(row["rejected_evidence_event_ids"], ["fabricated-event-id"])

    def test_19_empty_claims_do_not_invent_findings(self):
        result = self.run_gate(claims=[])
        ledger = result["claim_evidence_ledger"]
        self.assertEqual(ledger["claims"], [])
        self.assertFalse(ledger["has_blocking_claim"])
        self.assertFalse(ledger["has_downgrade_claim"])
        self.assertEqual(result["disposition"], "READY_FOR_SYNTHESIS")

    def test_20_future_copy_cannot_displace_past_same_chain_evidence(self):
        past = event(event_id="past-primary", source_chain_id="same-origin")
        future = event(
            event_id="future-copy",
            source_id="market-wire",
            source_chain_id="same-origin",
            available_at="2026-08-14T10:30:00+08:00",
        )
        result = self.run_gate(events=[future, past], claims=[])
        report = result["event_coverage_report"]
        self.assertEqual(report["candidate_event_ids"], ["past-primary"])
        self.assertEqual(report["future_event_ids_ignored"], ["future-copy"])
        self.assertEqual(report["independent_source_chain_count"], 1)


if __name__ == "__main__":
    unittest.main()
