from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "event_coverage.py"
SPEC = importlib.util.spec_from_file_location("w5_event_coverage", MODULE_PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def registry(*, forged=False):
    roles = [
        "FIRST_PARTY",
        "MARKET_WIRE",
        "COMPANY_DISCLOSURE",
        "TECHNOLOGY_RELEASE",
        "POLICY_REGULATORY",
        "OVERSEAS_PROXY",
    ] if forged else ["FIRST_PARTY"]
    grade = "A1" if forged else "D"
    return {
        "schema_version": "SourceRegistry/v1",
        "sources": [
            {
                "source_id": "caller-source",
                "source_class": "OFFICIAL_PRIMARY",
                "source_grade": grade,
                "coverage_roles": roles,
                "enabled": True,
            }
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


def event(event_id="e1", *, available_at="2026-08-13T19:56:32+08:00", chain="chain1"):
    return {
        "event_id": event_id,
        "event_type": "TECHNOLOGY_EVENT",
        "source_id": "caller-source",
        "source_chain_id": chain,
        "available_at": available_at,
        "market_effective_at": available_at,
        "target_symbols": [],
        "proxy_symbols": ["DEEPSEEK"],
        "mechanism": "candidate catalyst evidence",
        "evidence_refs": [f"public-safe://{event_id}"],
    }


def claim(text="candidate catalyst", *, claim_type="MODEL_INFERENCE", event_ids=None, extra=None):
    out = {
        "claim_id": "c1",
        "claim_type": claim_type,
        "text": text,
        "evidence_event_ids": ["e1"] if event_ids is None else event_ids,
        "evidence_refs": ["public-safe://cross-sectional-check"],
    }
    if extra:
        out.update(extra)
    return out


class EventCoverageGateTests(unittest.TestCase):
    def run_gate(self, *, intent_value=None, registry_value=None, scanned=None, proxies=None, events=None, claims=None):
        return mod.run_event_coverage_gate(
            intent=intent() if intent_value is None else intent_value,
            source_registry=registry() if registry_value is None else registry_value,
            scanned_source_ids=["caller-source"] if scanned is None else scanned,
            scanned_proxy_symbols=["DEEPSEEK"] if proxies is None else proxies,
            events=[event()] if events is None else events,
            claims=[claim()] if claims is None else claims,
        )

    def test_01_fabricated_all_role_registry_cannot_mint_complete_coverage(self):
        result = self.run_gate(registry_value=registry(forged=True))
        report = result["event_coverage_report"]
        self.assertEqual(report["source_authority_state"], "CANONICAL_SOURCE_REGISTRY_NOT_ASSEMBLED")
        self.assertEqual(report["observed_coverage_roles"], [])
        self.assertEqual(set(report["unresolved_source_gaps"]), set(mod.MANDATORY_ROLES["MARKET_ATTRIBUTION"]))
        self.assertEqual(report["disposition"], "EVENT_COVERAGE_INCOMPLETE")
        self.assertNotEqual(result["disposition"], "READY_FOR_SYNTHESIS")

    def test_02_grade_escalation_is_not_coverage_authority(self):
        low = self.run_gate(registry_value=registry(forged=False), claims=[])
        high = self.run_gate(registry_value=registry(forged=True), claims=[])
        for result in (low, high):
            self.assertEqual(result["event_coverage_report"]["observed_coverage_roles"], [])
            self.assertEqual(result["event_coverage_report"]["coverage_grade"], "INCOMPLETE")

    def test_03_candidate_registry_is_explicitly_evidence_only(self):
        normalized = mod.validate_source_registry(registry(forged=True))
        self.assertEqual(normalized["trust_class"], "CALLER_CANDIDATE_EVIDENCE_ONLY")
        self.assertTrue(all(value is False for value in normalized["authority"].values()))

    def test_04_scanned_unknown_candidate_source_fails(self):
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(scanned=["forged-id"])
        self.assertEqual(ctx.exception.code, "SCANNED_SOURCE_NOT_IN_CALLER_CANDIDATE_SET")

    def test_05_caller_causal_boolean_is_rejected_not_trusted(self):
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(claims=[claim("唯一原因", claim_type="CAUSAL_HYPOTHESIS", extra={"causal_identification_evidence": True})])
        self.assertEqual(ctx.exception.code, "CALLER_CLAIM_AUTHORITY_FLAG_FORBIDDEN")

    def test_06_caller_participant_boolean_is_rejected_not_trusted(self):
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(claims=[claim("主力出货", extra={"participant_intent_evidence": True})])
        self.assertEqual(ctx.exception.code, "CALLER_CLAIM_AUTHORITY_FLAG_FORBIDDEN")

    def test_07_unique_causal_language_blocks_without_typed_authority(self):
        result = self.run_gate(claims=[claim("这个事件就是因为股价上涨的唯一原因", claim_type="CAUSAL_HYPOTHESIS")])
        row = result["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertIn("CANONICAL_CAUSAL_IDENTIFICATION_AUTHORITY_UNAVAILABLE", row["reason_codes"])

    def test_08_participant_intent_blocks_even_at_grade_a(self):
        result = self.run_gate(intent_value=intent(grade="A"), claims=[claim("主力吸筹确认")])
        row = result["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertIn("CANONICAL_PARTICIPANT_INTENT_AUTHORITY_UNAVAILABLE", row["reason_codes"])

    def test_09_future_event_excluded_point_in_time(self):
        result = self.run_gate(events=[event(available_at="2026-08-14T10:30:00+08:00")], claims=[claim(event_ids=["e1"])])
        report = result["event_coverage_report"]
        row = result["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(report["candidate_event_ids"], [])
        self.assertEqual(report["future_event_ids_ignored"], ["e1"])
        self.assertEqual(row["outcome"], "BLOCK")

    def test_10_syndicated_copies_count_as_one_chain(self):
        result = self.run_gate(events=[event("a", chain="x"), event("b", chain="x")], claims=[])
        report = result["event_coverage_report"]
        self.assertEqual(report["independent_source_chain_count"], 1)
        self.assertEqual(report["candidate_event_ids"], ["a"])

    def test_11_price_anomaly_no_news_requires_backfill_and_source_gap_remains(self):
        result = self.run_gate(events=[], claims=[])
        report = result["event_coverage_report"]
        self.assertTrue(report["event_backfill_required"])
        self.assertEqual(report["disposition"], "EVENT_COVERAGE_INCOMPLETE")

    def test_12_portfolio_proxy_gap_is_retained(self):
        result = self.run_gate(intent_value=intent(kind="PORTFOLIO_LATEST"), proxies=[], claims=[])
        self.assertEqual(result["event_coverage_report"]["unresolved_proxy_gaps"], ["DEEPSEEK"])

    def test_13_grade_c_microstructure_claim_blocks(self):
        result = self.run_gate(intent_value=intent(grade="C"), claims=[claim("CVD 与盘口意图确认")])
        self.assertIn("MICROSTRUCTURE_TERM_EXCEEDS_DATA_GRADE", result["claim_evidence_ledger"]["claims"][0]["reason_codes"])

    def test_14_grade_c_supply_demand_language_downgrades(self):
        result = self.run_gate(intent_value=intent(grade="C"), claims=[claim("高位抛压很大")])
        self.assertEqual(result["claim_evidence_ledger"]["claims"][0]["outcome"], "DOWNGRADE")

    def test_15_deterministic_replay_has_stable_digest(self):
        self.assertEqual(self.run_gate(), self.run_gate())

    def test_16_all_authority_flags_remain_false(self):
        result = self.run_gate()
        for authority in (result["authority"], result["event_coverage_report"]["authority"], result["claim_evidence_ledger"]["authority"]):
            self.assertTrue(authority)
            self.assertTrue(all(value is False for value in authority.values()))

    def test_17_event_cannot_self_supply_source_grade(self):
        forged = event()
        forged["source_grade"] = "A1"
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(events=[forged])
        self.assertEqual(ctx.exception.code, "EVENT_FIELDS_INVALID")

    def test_18_fake_event_id_cannot_support_claim(self):
        result = self.run_gate(claims=[claim(event_ids=["fabricated-event-id"])])
        self.assertEqual(result["claim_evidence_ledger"]["claims"][0]["outcome"], "BLOCK")

    def test_19_timezone_naive_query_fails_closed(self):
        malformed = intent()
        malformed["anomaly_or_query_at"] = "2026-08-14T10:00:00"
        with self.assertRaises(mod.EventCoverageError):
            self.run_gate(intent_value=malformed)

    def test_20_no_public_ready_path_while_source_authority_is_absent(self):
        for forged in (False, True):
            for grade in ("A", "B", "C"):
                result = self.run_gate(registry_value=registry(forged=forged), intent_value=intent(grade=grade), claims=[])
                self.assertEqual(result["event_coverage_report"]["disposition"], "EVENT_COVERAGE_INCOMPLETE")
                self.assertNotEqual(result["disposition"], "READY_FOR_SYNTHESIS")

    def test_21_causal_hypothesis_cannot_run_before_coverage_is_authoritative(self):
        result = self.run_gate(claims=[claim("可能是候选催化", claim_type="CAUSAL_HYPOTHESIS")])
        row = result["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertIn("CAUSAL_CLAIM_BEFORE_COVERAGE_READY", row["reason_codes"])

    def test_22_empty_claims_do_not_invent_findings(self):
        result = self.run_gate(claims=[])
        ledger = result["claim_evidence_ledger"]
        self.assertEqual(ledger["claims"], [])
        self.assertFalse(ledger["has_blocking_claim"])
        self.assertFalse(ledger["has_downgrade_claim"])
        self.assertEqual(result["disposition"], "EVENT_COVERAGE_INCOMPLETE")

    def test_23_future_copy_cannot_displace_past_same_chain_evidence(self):
        past = event("past-primary", chain="same-origin")
        future = event("future-copy", available_at="2026-08-14T10:30:00+08:00", chain="same-origin")
        result = self.run_gate(events=[future, past], claims=[])
        report = result["event_coverage_report"]
        self.assertEqual(report["candidate_event_ids"], ["past-primary"])
        self.assertEqual(report["future_event_ids_ignored"], ["future-copy"])


if __name__ == "__main__":
    unittest.main()
