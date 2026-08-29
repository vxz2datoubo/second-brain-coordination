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
        "FIRST_PARTY", "MARKET_WIRE", "COMPANY_DISCLOSURE",
        "TECHNOLOGY_RELEASE", "POLICY_REGULATORY", "OVERSEAS_PROXY",
    ] if forged else ["FIRST_PARTY"]
    return {
        "schema_version": "SourceRegistry/v1",
        "sources": [{
            "source_id": "caller-source",
            "source_class": "OFFICIAL_PRIMARY",
            "source_grade": "A1" if forged else "D",
            "coverage_roles": roles,
            "enabled": True,
        }],
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
        for forged in (False, True):
            result = self.run_gate(registry_value=registry(forged=forged), claims=[])
            self.assertEqual(result["event_coverage_report"]["observed_coverage_roles"], [])
            self.assertEqual(result["event_coverage_report"]["coverage_grade"], "INCOMPLETE")

    def test_03_candidate_registry_is_evidence_only(self):
        normalized = mod.validate_source_registry(registry(forged=True))
        self.assertEqual(normalized["trust_class"], "CALLER_CANDIDATE_EVIDENCE_ONLY")
        self.assertTrue(all(v is False for v in normalized["authority"].values()))

    def test_04_unknown_scanned_source_fails(self):
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(scanned=["forged-id"])
        self.assertEqual(ctx.exception.code, "SCANNED_SOURCE_NOT_IN_CALLER_CANDIDATE_SET")

    def test_05_caller_causal_boolean_rejected(self):
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(claims=[claim("唯一原因", claim_type="CAUSAL_HYPOTHESIS", extra={"causal_identification_evidence": True})])
        self.assertEqual(ctx.exception.code, "CALLER_CLAIM_AUTHORITY_FLAG_FORBIDDEN")

    def test_06_caller_participant_boolean_rejected(self):
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(claims=[claim("主力出货", extra={"participant_intent_evidence": True})])
        self.assertEqual(ctx.exception.code, "CALLER_CLAIM_AUTHORITY_FLAG_FORBIDDEN")

    def test_07_unique_causal_language_blocks(self):
        row = self.run_gate(claims=[claim("这个事件就是因为股价上涨的唯一原因", claim_type="CAUSAL_HYPOTHESIS")])["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertIn("CANONICAL_CAUSAL_IDENTIFICATION_AUTHORITY_UNAVAILABLE", row["reason_codes"])

    def test_08_known_participant_intent_blocks_even_grade_a(self):
        row = self.run_gate(intent_value=intent(grade="A"), claims=[claim("主力吸筹确认")])["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertIn("CANONICAL_PARTICIPANT_INTENT_AUTHORITY_UNAVAILABLE", row["reason_codes"])

    def test_09_future_event_excluded(self):
        result = self.run_gate(events=[event(available_at="2026-08-14T10:30:00+08:00")], claims=[claim(event_ids=["e1"])])
        self.assertEqual(result["event_coverage_report"]["candidate_event_ids"], [])
        self.assertEqual(result["event_coverage_report"]["future_event_ids_ignored"], ["e1"])
        self.assertEqual(result["claim_evidence_ledger"]["claims"][0]["outcome"], "BLOCK")

    def test_10_syndicated_copies_count_one_chain(self):
        report = self.run_gate(events=[event("a", chain="x"), event("b", chain="x")], claims=[])["event_coverage_report"]
        self.assertEqual(report["independent_source_chain_count"], 1)
        self.assertEqual(report["candidate_event_ids"], ["a"])

    def test_11_no_news_requires_backfill(self):
        report = self.run_gate(events=[], claims=[])["event_coverage_report"]
        self.assertTrue(report["event_backfill_required"])
        self.assertEqual(report["disposition"], "EVENT_COVERAGE_INCOMPLETE")

    def test_12_portfolio_proxy_gap_retained(self):
        result = self.run_gate(intent_value=intent(kind="PORTFOLIO_LATEST"), proxies=[], claims=[])
        self.assertEqual(result["event_coverage_report"]["unresolved_proxy_gaps"], ["DEEPSEEK"])

    def test_13_grade_c_microstructure_blocks(self):
        row = self.run_gate(intent_value=intent(grade="C"), claims=[claim("CVD 与盘口意图确认")])["claim_evidence_ledger"]["claims"][0]
        self.assertIn("MICROSTRUCTURE_TERM_EXCEEDS_DATA_GRADE", row["reason_codes"])

    def test_14_grade_c_supply_demand_downgrades(self):
        row = self.run_gate(intent_value=intent(grade="C"), claims=[claim("高位抛压很大")])["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "DOWNGRADE")

    def test_15_deterministic_replay(self):
        self.assertEqual(self.run_gate(), self.run_gate())

    def test_16_all_authority_false(self):
        result = self.run_gate()
        for authority in (result["authority"], result["event_coverage_report"]["authority"], result["claim_evidence_ledger"]["authority"]):
            self.assertTrue(all(v is False for v in authority.values()))

    def test_17_event_cannot_self_supply_source_grade(self):
        forged = event(); forged["source_grade"] = "A1"
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(events=[forged])
        self.assertEqual(ctx.exception.code, "EVENT_FIELDS_INVALID")

    def test_18_fake_event_id_blocks(self):
        row = self.run_gate(claims=[claim(event_ids=["fabricated-event-id"])])["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "BLOCK")

    def test_19_timezone_naive_query_fails(self):
        malformed = intent(); malformed["anomaly_or_query_at"] = "2026-08-14T10:00:00"
        with self.assertRaises(mod.EventCoverageError):
            self.run_gate(intent_value=malformed)

    def test_20_no_public_ready_path(self):
        for forged in (False, True):
            for grade in ("A", "B", "C"):
                result = self.run_gate(registry_value=registry(forged=forged), intent_value=intent(grade=grade), claims=[])
                self.assertNotEqual(result["disposition"], "READY_FOR_SYNTHESIS")

    def test_21_causal_hypothesis_before_coverage_blocks(self):
        row = self.run_gate(claims=[claim("可能是候选催化", claim_type="CAUSAL_HYPOTHESIS")])["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertIn("CAUSAL_CLAIM_BEFORE_COVERAGE_READY", row["reason_codes"])

    def test_22_empty_claims_do_not_invent(self):
        ledger = self.run_gate(claims=[])["claim_evidence_ledger"]
        self.assertEqual(ledger["claims"], [])
        self.assertFalse(ledger["has_blocking_claim"])
        self.assertFalse(ledger["has_downgrade_claim"])

    def test_23_future_copy_cannot_displace_past_chain(self):
        result = self.run_gate(events=[event("future-copy", available_at="2026-08-14T10:30:00+08:00", chain="same-origin"), event("past-primary", chain="same-origin")], claims=[])
        self.assertEqual(result["event_coverage_report"]["candidate_event_ids"], ["past-primary"])

    def test_24_zero_blacklist_paraphrase_never_allows(self):
        text = "大资金正在持续收集流通筹码"
        self.assertIsNone(mod._PARTICIPANT_INTENT.search(text))
        row = self.run_gate(intent_value=intent(grade="A"), claims=[claim(text)])["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "DOWNGRADE")
        self.assertIn("UNTYPED_FREE_TEXT_PARTICIPANT_SEMANTICS_UNVERIFIED", row["reason_codes"])

    def test_25_second_zero_blacklist_paraphrase_never_allows(self):
        text = "大型资金账户正在主动减少市场流通筹码"
        self.assertIsNone(mod._PARTICIPANT_INTENT.search(text))
        row = self.run_gate(intent_value=intent(grade="A"), claims=[claim(text)])["claim_evidence_ledger"]["claims"][0]
        self.assertNotEqual(row["outcome"], "ALLOW")

    def test_26_caller_relabel_cannot_mint_participant_semantics(self):
        text = "大资金正在持续收集流通筹码"
        for claim_type in ("OBSERVED_FACT", "SOURCE_CLAIM", "MODEL_INFERENCE", "UNKNOWN"):
            row = self.run_gate(intent_value=intent(grade="A"), claims=[claim(text, claim_type=claim_type)])["claim_evidence_ledger"]["claims"][0]
            self.assertNotEqual(row["outcome"], "ALLOW", claim_type)
            self.assertIn("UNTYPED_FREE_TEXT_PARTICIPANT_SEMANTICS_UNVERIFIED", row["reason_codes"])

    def test_27_generic_untyped_text_non_authoritative(self):
        row = self.run_gate(claims=[claim("candidate catalyst")])["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "DOWNGRADE")
        self.assertFalse(mod.TYPED_FREE_TEXT_SEMANTIC_AUTHORITY_AVAILABLE)


if __name__ == "__main__":
    unittest.main()
