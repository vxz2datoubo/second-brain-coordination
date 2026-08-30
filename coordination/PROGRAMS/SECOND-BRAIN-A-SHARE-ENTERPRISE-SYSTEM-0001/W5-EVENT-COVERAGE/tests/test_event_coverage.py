from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "event_coverage.py"
SPEC = importlib.util.spec_from_file_location("w5_event_coverage_r166", MODULE_PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def registry(*, all_roles: bool = False, grade: str = "D", enabled: bool = True):
    roles = [
        "FIRST_PARTY",
        "MARKET_WIRE",
        "COMPANY_DISCLOSURE",
        "TECHNOLOGY_RELEASE",
        "POLICY_REGULATORY",
        "OVERSEAS_PROXY",
    ] if all_roles else ["FIRST_PARTY"]
    return {
        "schema_version": "SourceRegistry/v1",
        "sources": [
            {
                "source_id": "caller-source",
                "source_class": "OFFICIAL_PRIMARY",
                "source_grade": grade,
                "coverage_roles": roles,
                "enabled": enabled,
            }
        ],
    }


def intent(*, kind: str = "MARKET_ATTRIBUTION", grade: str = "B", anomaly: bool = True):
    return {
        "intent_class": kind,
        "target_symbols": ["SZ300058"],
        "proxy_symbols": ["DEEPSEEK"],
        "previous_close_at": "2026-08-13T15:00:00+08:00",
        "anomaly_or_query_at": "2026-08-14T10:00:00+08:00",
        "data_grade": grade,
        "price_anomaly_unexplained": anomaly,
    }


def event(
    event_id: str = "e1",
    *,
    available_at: str = "2026-08-13T19:56:32+08:00",
    market_effective_at: str | None = None,
    chain: str = "chain1",
    targets: list[str] | None = None,
    proxies: list[str] | None = None,
):
    return {
        "event_id": event_id,
        "event_type": "TECHNOLOGY_EVENT",
        "source_id": "caller-source",
        "source_chain_id": chain,
        "available_at": available_at,
        "market_effective_at": market_effective_at or available_at,
        "target_symbols": [] if targets is None else targets,
        "proxy_symbols": ["DEEPSEEK"] if proxies is None else proxies,
        "mechanism": "candidate catalyst evidence",
        "evidence_refs": [f"public-safe://{event_id}"],
    }


def claim(
    text: str = "candidate catalyst",
    *,
    claim_type: str = "MODEL_INFERENCE",
    event_ids: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    extra: dict | None = None,
):
    value = {
        "claim_id": "c1",
        "claim_type": claim_type,
        "text": text,
        "evidence_event_ids": ["e1"] if event_ids is None else event_ids,
        "evidence_refs": ["public-safe://cross-sectional-check"] if evidence_refs is None else evidence_refs,
    }
    if extra:
        value.update(extra)
    return value


class EventCoverageGateTests(unittest.TestCase):
    def run_gate(
        self,
        *,
        intent_value=None,
        registry_value=None,
        scanned=None,
        proxies=None,
        events=None,
        claims=None,
    ):
        return mod.run_event_coverage_gate(
            intent=intent() if intent_value is None else intent_value,
            source_registry=registry() if registry_value is None else registry_value,
            scanned_source_ids=["caller-source"] if scanned is None else scanned,
            scanned_proxy_symbols=["DEEPSEEK"] if proxies is None else proxies,
            events=[event()] if events is None else events,
            claims=[claim()] if claims is None else claims,
        )

    def test_01_fabricated_all_role_registry_cannot_mint_complete_coverage(self):
        result = self.run_gate(registry_value=registry(all_roles=True, grade="A1"))
        report = result["event_coverage_report"]
        self.assertEqual(report["source_authority_state"], mod.SOURCE_AUTHORITY_STATE)
        self.assertEqual(report["observed_coverage_roles"], [])
        self.assertEqual(
            set(report["unresolved_source_gaps"]),
            set(mod.MANDATORY_ROLES["MARKET_ATTRIBUTION"]),
        )
        self.assertEqual(report["coverage_grade"], "INCOMPLETE")
        self.assertEqual(report["disposition"], "EVENT_COVERAGE_INCOMPLETE")
        self.assertNotEqual(result["disposition"], "READY_FOR_SYNTHESIS")

    def test_02_caller_grade_escalation_is_not_source_authority(self):
        for source_grade in ("A1", "A2", "B1", "B2", "C1", "C2", "D"):
            report = self.run_gate(
                registry_value=registry(all_roles=True, grade=source_grade), claims=[]
            )["event_coverage_report"]
            self.assertEqual(report["observed_coverage_roles"], [], source_grade)
            self.assertEqual(report["coverage_grade"], "INCOMPLETE", source_grade)

    def test_03_candidate_registry_is_evidence_only(self):
        normalized = mod.validate_source_registry(registry(all_roles=True, grade="A1"))
        self.assertEqual(normalized["trust_class"], "CALLER_CANDIDATE_EVIDENCE_ONLY")
        self.assertRegex(normalized["registry_digest"], r"^[0-9a-f]{64}$")
        self.assertTrue(all(value is False for value in normalized["authority"].values()))

    def test_04_unknown_scanned_source_fails_closed(self):
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(scanned=["forged-id"])
        self.assertEqual(ctx.exception.code, "SCANNED_SOURCE_NOT_IN_CALLER_CANDIDATE_SET")

    def test_05_caller_causal_boolean_is_rejected(self):
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(
                claims=[
                    claim(
                        "唯一原因",
                        claim_type="CAUSAL_HYPOTHESIS",
                        extra={"causal_identification_evidence": True},
                    )
                ]
            )
        self.assertEqual(ctx.exception.code, "CALLER_CLAIM_AUTHORITY_FLAG_FORBIDDEN")

    def test_06_caller_participant_boolean_is_rejected(self):
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(
                claims=[claim("主力出货", extra={"participant_intent_evidence": True})]
            )
        self.assertEqual(ctx.exception.code, "CALLER_CLAIM_AUTHORITY_FLAG_FORBIDDEN")

    def test_07_unique_causal_language_blocks(self):
        row = self.run_gate(
            claims=[claim("这个事件就是因为股价上涨的唯一原因", claim_type="CAUSAL_HYPOTHESIS")]
        )["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertIn(
            "CANONICAL_CAUSAL_IDENTIFICATION_AUTHORITY_UNAVAILABLE", row["reason_codes"]
        )

    def test_08_known_participant_intent_blocks_even_data_grade_a(self):
        row = self.run_gate(
            intent_value=intent(grade="A"), claims=[claim("主力吸筹确认")]
        )["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertIn(
            "CANONICAL_PARTICIPANT_INTENT_AUTHORITY_UNAVAILABLE", row["reason_codes"]
        )

    def test_09_future_event_is_excluded_before_claim_consumption(self):
        result = self.run_gate(
            events=[event(available_at="2026-08-14T10:30:00+08:00")],
            claims=[claim(event_ids=["e1"])],
        )
        report = result["event_coverage_report"]
        self.assertEqual(report["candidate_event_ids"], [])
        self.assertEqual(report["future_event_ids_ignored"], ["e1"])
        self.assertEqual(result["claim_evidence_ledger"]["claims"][0]["outcome"], "BLOCK")

    def test_10_syndicated_copies_count_as_one_source_chain(self):
        report = self.run_gate(
            events=[event("a", chain="same-origin"), event("b", chain="same-origin")],
            claims=[],
        )["event_coverage_report"]
        self.assertEqual(report["independent_source_chain_count"], 1)
        self.assertEqual(report["candidate_event_ids"], ["a"])

    def test_11_no_news_keeps_backfill_required_and_coverage_incomplete(self):
        report = self.run_gate(events=[], claims=[])["event_coverage_report"]
        self.assertTrue(report["event_backfill_required"])
        self.assertEqual(report["disposition"], "EVENT_COVERAGE_INCOMPLETE")

    def test_12_portfolio_proxy_gap_is_retained(self):
        report = self.run_gate(
            intent_value=intent(kind="PORTFOLIO_LATEST"), proxies=[], claims=[]
        )["event_coverage_report"]
        self.assertEqual(report["unresolved_proxy_gaps"], ["DEEPSEEK"])

    def test_13_grade_c_microstructure_language_blocks(self):
        row = self.run_gate(
            intent_value=intent(grade="C"), claims=[claim("CVD 与盘口意图确认")]
        )["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertIn("MICROSTRUCTURE_TERM_EXCEEDS_DATA_GRADE", row["reason_codes"])

    def test_14_grade_c_supply_demand_language_downgrades(self):
        row = self.run_gate(
            intent_value=intent(grade="C"), claims=[claim("高位抛压很大")]
        )["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "DOWNGRADE")
        self.assertIn(
            "SUPPLY_DEMAND_LANGUAGE_REQUIRES_PRICE_BEHAVIOR_DOWNGRADE",
            row["reason_codes"],
        )

    def test_15_gate_is_byte_deterministic_for_same_inputs(self):
        first = self.run_gate()
        second = self.run_gate()
        self.assertEqual(first, second)
        self.assertEqual(first["result_digest"], second["result_digest"])

    def test_16_every_emitted_authority_flag_is_false(self):
        result = self.run_gate()
        surfaces = (
            mod.AUTHORITY,
            result["authority"],
            result["event_coverage_report"]["authority"],
            result["claim_evidence_ledger"]["authority"],
        )
        for authority in surfaces:
            self.assertTrue(authority)
            self.assertTrue(all(value is False for value in authority.values()))

    def test_17_event_cannot_self_supply_source_grade(self):
        forged = event()
        forged["source_grade"] = "A1"
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(events=[forged])
        self.assertEqual(ctx.exception.code, "EVENT_FIELDS_INVALID")

    def test_18_fake_event_reference_blocks_claim(self):
        row = self.run_gate(claims=[claim(event_ids=["fabricated-event-id"])])[
            "claim_evidence_ledger"
        ]["claims"][0]
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertEqual(row["rejected_evidence_event_ids"], ["fabricated-event-id"])

    def test_19_timezone_naive_query_fails_closed(self):
        malformed = intent()
        malformed["anomaly_or_query_at"] = "2026-08-14T10:00:00"
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(intent_value=malformed)
        self.assertEqual(ctx.exception.code, "QUERY_TIME_INVALID_TIMEZONE_REQUIRED")

    def test_20_no_public_ready_path_exists_in_r166(self):
        for all_roles in (False, True):
            for source_grade in ("A1", "D"):
                for data_grade in ("A", "B", "C"):
                    result = self.run_gate(
                        registry_value=registry(all_roles=all_roles, grade=source_grade),
                        intent_value=intent(grade=data_grade),
                        claims=[],
                    )
                    self.assertNotEqual(result["disposition"], "READY_FOR_SYNTHESIS")

    def test_21_causal_hypothesis_before_coverage_ready_blocks(self):
        row = self.run_gate(
            claims=[claim("可能是候选催化", claim_type="CAUSAL_HYPOTHESIS")]
        )["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "BLOCK")
        self.assertIn("CAUSAL_CLAIM_BEFORE_COVERAGE_READY", row["reason_codes"])

    def test_22_empty_claims_do_not_invent_claim_rows(self):
        ledger = self.run_gate(claims=[])["claim_evidence_ledger"]
        self.assertEqual(ledger["claims"], [])
        self.assertFalse(ledger["has_blocking_claim"])
        self.assertFalse(ledger["has_downgrade_claim"])

    def test_23_future_copy_cannot_displace_past_member_of_same_chain(self):
        report = self.run_gate(
            events=[
                event(
                    "future-copy",
                    available_at="2026-08-14T10:30:00+08:00",
                    chain="same-origin",
                ),
                event("past-primary", chain="same-origin"),
            ],
            claims=[],
        )["event_coverage_report"]
        self.assertEqual(report["candidate_event_ids"], ["past-primary"])

    def test_24_blacklist_evasion_paraphrase_never_allows(self):
        text = "大资金正在持续收集流通筹码"
        self.assertIsNone(mod._PARTICIPANT_INTENT_LITERAL.search(text))
        row = self.run_gate(intent_value=intent(grade="A"), claims=[claim(text)])[
            "claim_evidence_ledger"
        ]["claims"][0]
        self.assertEqual(row["outcome"], "DOWNGRADE")
        self.assertIn("UNTYPED_FREE_TEXT_SEMANTICS_UNVERIFIED", row["reason_codes"])

    def test_25_second_blacklist_evasion_paraphrase_never_allows(self):
        text = "大型资金账户正在主动减少市场流通筹码"
        self.assertIsNone(mod._PARTICIPANT_INTENT_LITERAL.search(text))
        row = self.run_gate(intent_value=intent(grade="A"), claims=[claim(text)])[
            "claim_evidence_ledger"
        ]["claims"][0]
        self.assertNotEqual(row["outcome"], "ALLOW")
        self.assertIn("UNTYPED_FREE_TEXT_SEMANTICS_UNVERIFIED", row["reason_codes"])

    def test_26_caller_claim_type_relabel_cannot_mint_free_text_authority(self):
        text = "大资金正在持续收集流通筹码"
        for claim_type in ("OBSERVED_FACT", "SOURCE_CLAIM", "MODEL_INFERENCE", "UNKNOWN"):
            row = self.run_gate(
                intent_value=intent(grade="A"),
                claims=[claim(text, claim_type=claim_type)],
            )["claim_evidence_ledger"]["claims"][0]
            self.assertEqual(row["outcome"], "DOWNGRADE", claim_type)
            self.assertIn("UNTYPED_FREE_TEXT_SEMANTICS_UNVERIFIED", row["reason_codes"])

    def test_27_generic_untyped_text_is_non_authoritative(self):
        row = self.run_gate(claims=[claim("candidate catalyst")])[
            "claim_evidence_ledger"
        ]["claims"][0]
        self.assertEqual(row["outcome"], "DOWNGRADE")
        self.assertFalse(mod.TYPED_FREE_TEXT_SEMANTIC_AUTHORITY_AVAILABLE)
        self.assertIn("CANONICAL_SOURCE_INSTANCE_AUTHORITY_UNAVAILABLE", row["reason_codes"])
        self.assertIn("UNTYPED_FREE_TEXT_SEMANTICS_UNVERIFIED", row["reason_codes"])

    def test_28_disabled_caller_source_cannot_be_used_by_event(self):
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(registry_value=registry(enabled=False))
        self.assertEqual(ctx.exception.code, "EVENT_SOURCE_NOT_IN_CALLER_CANDIDATE_SET")

    def test_29_registry_rejects_extra_authority_field(self):
        forged = registry()
        forged["sources"][0]["trusted"] = True
        with self.assertRaises(mod.EventCoverageError) as ctx:
            mod.validate_source_registry(forged)
        self.assertEqual(ctx.exception.code, "SOURCE_FIELDS_INVALID")

    def test_30_market_effective_time_cannot_precede_public_availability(self):
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(
                events=[
                    event(
                        available_at="2026-08-13T19:56:32+08:00",
                        market_effective_at="2026-08-13T19:00:00+08:00",
                    )
                ]
            )
        self.assertEqual(ctx.exception.code, "MARKET_EFFECTIVE_BEFORE_AVAILABLE")

    def test_31_outside_window_event_is_not_candidate_evidence(self):
        report = self.run_gate(
            events=[event(available_at="2026-08-13T14:00:00+08:00")], claims=[]
        )["event_coverage_report"]
        self.assertEqual(report["candidate_event_ids"], [])
        self.assertEqual(report["outside_window_event_ids_ignored"], ["e1"])

    def test_32_irrelevant_symbol_event_is_not_candidate_evidence(self):
        report = self.run_gate(
            events=[event(targets=["SH600000"], proxies=[])], claims=[]
        )["event_coverage_report"]
        self.assertEqual(report["candidate_event_ids"], [])
        self.assertEqual(report["irrelevant_event_ids_ignored"], ["e1"])

    def test_33_source_claim_without_any_evidence_is_downgraded(self):
        row = self.run_gate(
            claims=[
                claim(
                    "public claim",
                    claim_type="SOURCE_CLAIM",
                    event_ids=[],
                    evidence_refs=[],
                )
            ]
        )["claim_evidence_ledger"]["claims"][0]
        self.assertEqual(row["outcome"], "DOWNGRADE")
        self.assertIn("EVIDENCE_REFS_MISSING", row["reason_codes"])

    def test_34_duplicate_source_ids_fail_closed(self):
        forged = registry()
        forged["sources"].append(dict(forged["sources"][0]))
        with self.assertRaises(mod.EventCoverageError) as ctx:
            mod.validate_source_registry(forged)
        self.assertEqual(ctx.exception.code, "SOURCE_ID_DUPLICATE")

    def test_35_duplicate_event_ids_fail_closed(self):
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(events=[event("dup"), event("dup")])
        self.assertEqual(ctx.exception.code, "EVENT_ID_DUPLICATE")

    def test_36_portfolio_latest_requires_proxy_symbols(self):
        malformed = intent(kind="PORTFOLIO_LATEST")
        malformed["proxy_symbols"] = []
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(intent_value=malformed)
        self.assertEqual(ctx.exception.code, "PORTFOLIO_PROXY_SYMBOLS_REQUIRED")

    def test_37_previous_close_after_query_fails_closed(self):
        malformed = intent()
        malformed["previous_close_at"] = "2026-08-14T11:00:00+08:00"
        with self.assertRaises(mod.EventCoverageError) as ctx:
            self.run_gate(intent_value=malformed)
        self.assertEqual(ctx.exception.code, "PREVIOUS_CLOSE_AFTER_QUERY")

    def test_38_scanned_source_role_metadata_never_populates_observed_roles(self):
        report = self.run_gate(
            registry_value=registry(all_roles=True, grade="A1"),
            scanned=["caller-source"],
            claims=[],
        )["event_coverage_report"]
        self.assertEqual(report["scanned_source_ids"], ["caller-source"])
        self.assertEqual(report["observed_coverage_roles"], [])
        self.assertEqual(report["source_authority_state"], mod.SOURCE_AUTHORITY_STATE)

    def test_39_result_digest_changes_when_evidence_changes(self):
        first = self.run_gate()
        second = self.run_gate(events=[event("e1", chain="different-chain")])
        self.assertNotEqual(first["result_digest"], second["result_digest"])

    def test_40_blocking_claim_forces_abstain(self):
        result = self.run_gate(claims=[claim("主力正在出货")])
        self.assertEqual(result["claim_evidence_ledger"]["disposition"], "ABSTAIN")
        self.assertEqual(result["disposition"], "ABSTAIN")


if __name__ == "__main__":
    unittest.main()
