from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import unittest

import jsonschema
import yaml

from offline_research.market_semantics import (
    CanonicalDirection,
    CapabilityEvidenceClass,
    DriftKind,
    MarketSemanticFieldSpec,
    MissingState,
    PriceSemantic,
    ProviderCapabilityObservation,
    SemanticValidationError,
    TimeSemantic,
    append_capability_observation,
    assert_direction_contract,
    capability_digest,
    classify_value,
    detect_capability_drift,
    detect_field_drift,
    explicit_unit_convert,
    map_direction,
    normalize_to_tick,
    parse_fixed_decimal,
    require_capability,
    require_point_in_time,
    semantic_digest,
    validate_tick_aligned,
)


def price_spec(**overrides):
    base = dict(
        semantic_field_id="TRADE.PRICE.V1",
        semantic_version="1.0",
        source_system="SYNTHETIC",
        source_version="1",
        source_field_name="Price",
        canonical_field_ref="trade.price",
        primitive_type="DECIMAL_STRING",
        unit_kind="CURRENCY",
        unit_symbol="CNY",
        unit_scale="1",
        fixed_scale="0.01",
        tick_size="0.01",
        price_semantic=PriceSemantic.RAW_TRADE_PRICE,
        adjustment_state="RAW",
        evidence_ref="synthetic:test",
        last_verified_at="2026-09-01T00:00:00+08:00",
    )
    base.update(overrides)
    return MarketSemanticFieldSpec(**base)


def direction_spec(**overrides):
    base = dict(
        semantic_field_id="TRADE.DIRECTION.V1",
        semantic_version="1.0",
        source_system="TDXQUANT_DOC",
        source_version="DOC_2026_09_01",
        source_field_name="BSFlag",
        canonical_field_ref="trade.aggressor_direction",
        primitive_type="ENUM_STRING",
        unit_kind="ENUM",
        unit_symbol="NONE",
        source_enum_map={"0": "BUY", "1": "SELL", "2": "UNKNOWN"},
        evidence_ref="official-doc:get_tick_data",
        last_verified_at="2026-09-01T00:00:00+08:00",
    )
    base.update(overrides)
    return MarketSemanticFieldSpec(**base)


def documented_capability(**overrides):
    base = dict(
        observation_id="tdx-doc-2026-09-01",
        provider="TDX",
        product="TdxQuant",
        capability_id="GET_TICK_DATA",
        method="get_tick_data",
        evidence_class=CapabilityEvidenceClass.OFFICIAL_DOCUMENTED,
        observed_at="2026-09-01T00:00:00+08:00",
        local_runtime_observed=False,
        documented_fields=("Time", "Price", "Volume", "BSFlag"),
        documentation_version="DOC_CURRENT_2026_09_01",
        runtime_version=None,
        observed_fields=(),
        entitlement_state="UNVERIFIED",
        semantic_field_refs=("TRADE.PRICE.V1", "TRADE.DIRECTION.V1"),
        evidence_refs=("official:https://help.tdx.com.cn/quant/",),
        invalidation_conditions=("documentation_change", "runtime_upgrade"),
        next_verification_action="A/B reconcile installed runtime against current documentation",
    )
    base.update(overrides)
    return ProviderCapabilityObservation(**base)


class NumericSemanticsTests(unittest.TestCase):
    def test_binary_float_is_rejected(self):
        with self.assertRaisesRegex(SemanticValidationError, "BINARY_FLOAT_FORBIDDEN"):
            parse_fixed_decimal(0.05)

    def test_decimal_string_is_exact(self):
        self.assertEqual(parse_fixed_decimal("0.05"), Decimal("0.05"))

    def test_fraction_to_percent_requires_explicit_factor(self):
        with self.assertRaisesRegex(SemanticValidationError, "EXPLICIT_CONVERSION_FACTOR_REQUIRED"):
            explicit_unit_convert("0.05", from_unit="FRACTION", to_unit="PERCENT", factor=None)
        self.assertEqual(
            explicit_unit_convert("0.05", from_unit="FRACTION", to_unit="PERCENT", factor="100"),
            Decimal("5.00"),
        )

    def test_percent_to_fraction_is_explicit(self):
        self.assertEqual(
            explicit_unit_convert("5", from_unit="PERCENT", to_unit="FRACTION", factor="0.01"),
            Decimal("0.05"),
        )

    def test_shares_vs_lots_cannot_convert_implicitly(self):
        with self.assertRaisesRegex(SemanticValidationError, "EXPLICIT_CONVERSION_FACTOR_REQUIRED"):
            explicit_unit_convert("1000", from_unit="SHARES", to_unit="LOTS", factor=None)

    def test_yuan_vs_ten_thousand_yuan_cannot_convert_implicitly(self):
        with self.assertRaisesRegex(SemanticValidationError, "EXPLICIT_CONVERSION_FACTOR_REQUIRED"):
            explicit_unit_convert("10000", from_unit="CNY", to_unit="TEN_THOUSAND_CNY", factor=None)

    def test_display_price_cannot_be_canonical(self):
        with self.assertRaisesRegex(SemanticValidationError, "DISPLAY_PRICE_CANNOT_BE_CANONICAL"):
            price_spec(price_semantic=PriceSemantic.DISPLAY_PRICE, canonical_persistable=True)

    def test_off_tick_price_fails(self):
        with self.assertRaisesRegex(SemanticValidationError, "PRICE_NOT_TICK_ALIGNED"):
            validate_tick_aligned("10.005", price_spec())

    def test_on_tick_price_passes(self):
        self.assertEqual(validate_tick_aligned("10.05", price_spec()), Decimal("10.05"))

    def test_rule_bound_tick_requires_resolution(self):
        spec = price_spec(tick_size=None, tick_size_ref="AShareRuleSnapshot.tick_size")
        with self.assertRaisesRegex(SemanticValidationError, "TICK_SIZE_RULE_RESOLUTION_REQUIRED"):
            validate_tick_aligned("10.05", spec)

    def test_explicit_tick_normalization_carries_original_and_policy(self):
        receipt = normalize_to_tick("10.005", "0.01")
        self.assertEqual(receipt.original, Decimal("10.005"))
        self.assertEqual(receipt.normalized, Decimal("10.00"))
        self.assertEqual(receipt.policy, "ROUND_HALF_EVEN_EXPLICIT")


class DirectionTests(unittest.TestCase):
    def test_documented_buy_sell_unknown_mapping(self):
        spec = direction_spec()
        self.assertEqual(map_direction("0", spec), CanonicalDirection.BUY)
        self.assertEqual(map_direction("1", spec), CanonicalDirection.SELL)
        self.assertEqual(map_direction("2", spec), CanonicalDirection.UNKNOWN)

    def test_unknown_direction_is_not_coerced_to_buy_or_sell(self):
        self.assertIs(map_direction(2, direction_spec()), CanonicalDirection.UNKNOWN)

    def test_absent_direction_does_not_become_zero(self):
        with self.assertRaisesRegex(SemanticValidationError, "DIRECTION_MISSING"):
            map_direction(None, direction_spec())

    def test_unmapped_enum_fails_closed(self):
        with self.assertRaisesRegex(SemanticValidationError, "ENUM_VALUE_UNMAPPED"):
            map_direction("9", direction_spec())

    def test_reversed_vendor_mapping_fails_expected_contract(self):
        reversed_spec = direction_spec(source_enum_map={"0": "SELL", "1": "BUY", "2": "UNKNOWN"})
        with self.assertRaisesRegex(SemanticValidationError, "DIRECTION_CONTRACT_MISMATCH"):
            assert_direction_contract(
                reversed_spec,
                {"0": CanonicalDirection.BUY, "1": CanonicalDirection.SELL, "2": CanonicalDirection.UNKNOWN},
            )


class TimeAndMissingnessTests(unittest.TestCase):
    def test_available_at_is_required_for_pit(self):
        with self.assertRaisesRegex(SemanticValidationError, "AVAILABLE_AT_REQUIRED"):
            require_point_in_time({"published_at": "2026-09-01T09:30:00+08:00"})

    def test_published_at_cannot_substitute_for_available_at(self):
        with self.assertRaisesRegex(SemanticValidationError, "AVAILABLE_AT_REQUIRED"):
            require_point_in_time({"event_time": "2026-09-01T09:29:59+08:00", "published_at": "2026-09-01T09:30:00+08:00"})

    def test_timezone_is_required(self):
        with self.assertRaisesRegex(SemanticValidationError, "TIMEZONE_REQUIRED"):
            require_point_in_time({"available_at": "2026-09-01T09:30:00"})

    def test_zero_is_present_not_missing(self):
        value, state = classify_value(0, MissingState.PRESENT)
        self.assertEqual(value, 0)
        self.assertEqual(state, MissingState.PRESENT)

    def test_missing_state_requires_null(self):
        with self.assertRaisesRegex(SemanticValidationError, "MISSING_STATE_REQUIRES_NULL_VALUE"):
            classify_value(0, MissingState.SOURCE_MISSING)

    def test_missing_states_remain_distinct(self):
        states = {
            classify_value(None, MissingState.SOURCE_MISSING)[1],
            classify_value(None, MissingState.STALE)[1],
            classify_value(None, MissingState.PERMISSION_OR_ENTITLEMENT_UNVERIFIED)[1],
            classify_value(None, MissingState.UNKNOWN)[1],
        }
        self.assertEqual(len(states), 4)


class CapabilityEvidenceTests(unittest.TestCase):
    def test_official_documentation_does_not_satisfy_local_runtime_gate(self):
        with self.assertRaisesRegex(SemanticValidationError, "LOCAL_RUNTIME_CAPABILITY_NOT_VERIFIED"):
            require_capability(documented_capability(), require_local_runtime=True)

    def test_official_documentation_cannot_claim_local_runtime(self):
        with self.assertRaisesRegex(
            SemanticValidationError, "DOCUMENTATION_OBSERVATION_CANNOT_CLAIM_LOCAL_RUNTIME"
        ):
            documented_capability(local_runtime_observed=True)

    def test_local_runtime_verified_requires_runtime_version(self):
        with self.assertRaisesRegex(SemanticValidationError, "LOCAL_RUNTIME_VERSION_REQUIRED"):
            ProviderCapabilityObservation(
                observation_id="local-1",
                provider="TDX",
                product="TdxQuant",
                capability_id="GET_TICK_DATA",
                method="get_tick_data",
                evidence_class=CapabilityEvidenceClass.LOCAL_RUNTIME_VERIFIED,
                observed_at="2026-09-01T00:00:00+08:00",
                local_runtime_observed=True,
                runtime_version=None,
                observed_fields=("Time",),
                evidence_refs=("local:test-run",),
            )

    def test_local_runtime_verified_requires_local_evidence_ref(self):
        with self.assertRaisesRegex(SemanticValidationError, "LOCAL_EVIDENCE_REF_REQUIRED"):
            ProviderCapabilityObservation(
                observation_id="local-2",
                provider="TDX",
                product="TdxQuant",
                capability_id="GET_TICK_DATA",
                method="get_tick_data",
                evidence_class=CapabilityEvidenceClass.LOCAL_RUNTIME_VERIFIED,
                observed_at="2026-09-01T00:00:00+08:00",
                local_runtime_observed=True,
                runtime_version="1.2.3",
                observed_fields=("Time",),
                evidence_refs=("official:docs",),
            )

    def test_history_is_append_only(self):
        first = documented_capability()
        history = append_capability_observation((), first)
        second = documented_capability(
            observation_id="tdx-doc-2026-09-02",
            documentation_version="DOC_CURRENT_2026_09_02",
            observed_at="2026-09-02T00:00:00+08:00",
        )
        history = append_capability_observation(history, second)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0], first)

    def test_same_observation_id_cannot_be_overwritten(self):
        first = documented_capability()
        changed = documented_capability(documentation_version="FORGED_CHANGE")
        with self.assertRaisesRegex(SemanticValidationError, "CAPABILITY_OBSERVATION_IMMUTABLE"):
            append_capability_observation((first,), changed)

    def test_identical_reappend_is_idempotent(self):
        first = documented_capability()
        self.assertEqual(append_capability_observation((first,), first), (first,))


class DriftAndDigestTests(unittest.TestCase):
    def test_unit_drift_is_typed(self):
        old = price_spec()
        new = replace(old, unit_symbol="TEN_THOUSAND_CNY")
        self.assertIn(DriftKind.UNIT_DRIFT, detect_field_drift(old, new))

    def test_direction_and_enum_drift_are_typed(self):
        old = direction_spec()
        new = replace(old, source_enum_map={"0": "SELL", "1": "BUY", "2": "UNKNOWN"})
        drift = detect_field_drift(old, new)
        self.assertIn(DriftKind.DIRECTION_DRIFT, drift)
        self.assertIn(DriftKind.ENUM_DRIFT, drift)

    def test_precision_drift_is_typed(self):
        old = price_spec()
        new = replace(old, tick_size=Decimal("0.001"))
        self.assertIn(DriftKind.PRECISION_DRIFT, detect_field_drift(old, new))

    def test_vendor_version_drift_is_typed(self):
        old = price_spec()
        new = replace(old, source_version="2")
        self.assertIn(DriftKind.VENDOR_VERSION_DRIFT, detect_field_drift(old, new))

    def test_time_semantic_drift_is_typed(self):
        old = MarketSemanticFieldSpec(
            semantic_field_id="TRADE.TIME.V1",
            semantic_version="1",
            source_system="X",
            source_version="1",
            source_field_name="Time",
            canonical_field_ref="trade.exchange_time",
            primitive_type="ISO8601",
            unit_kind="TIME",
            unit_symbol="ISO8601",
            time_semantic=TimeSemantic.EXCHANGE_TIME,
        )
        new = replace(old, time_semantic=TimeSemantic.AVAILABLE_AT)
        self.assertIn(DriftKind.TIME_SEMANTIC_DRIFT, detect_field_drift(old, new))

    def test_adjustment_drift_is_typed(self):
        old = price_spec(adjustment_state="RAW")
        new = replace(old, adjustment_state="FORWARD_ADJUSTED")
        self.assertIn(DriftKind.ADJUSTMENT_DRIFT, detect_field_drift(old, new))

    def test_missingness_drift_is_typed(self):
        old = price_spec()
        new = replace(old, allowed_missing_states=(MissingState.PRESENT, MissingState.UNKNOWN))
        self.assertIn(DriftKind.MISSINGNESS_DRIFT, detect_field_drift(old, new))

    def test_capability_evidence_change_is_typed(self):
        old = documented_capability()
        local = ProviderCapabilityObservation(
            observation_id="local",
            provider="TDX",
            product="TdxQuant",
            capability_id="GET_TICK_DATA",
            method="get_tick_data",
            evidence_class=CapabilityEvidenceClass.LOCAL_RUNTIME_VERIFIED,
            observed_at="2026-09-02T00:00:00+08:00",
            local_runtime_observed=True,
            runtime_version="1.2.3",
            observed_fields=("Time", "Price"),
            evidence_refs=("local:runtime-probe-001",),
        )
        self.assertIn(DriftKind.ENTITLEMENT_OR_CAPABILITY_DRIFT, detect_capability_drift(old, local))

    def test_semantic_digest_is_deterministic(self):
        spec = price_spec()
        self.assertEqual(semantic_digest(spec), semantic_digest(spec))
        self.assertEqual(len(semantic_digest(spec)), 64)

    def test_semantic_change_changes_digest(self):
        old = price_spec()
        new = replace(old, unit_symbol="OTHER")
        self.assertNotEqual(semantic_digest(old), semantic_digest(new))

    def test_capability_digest_is_deterministic(self):
        obs = documented_capability()
        self.assertEqual(capability_digest(obs), capability_digest(obs))
        self.assertEqual(len(capability_digest(obs)), 64)


class ContractFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.slice_root = Path(__file__).resolve().parents[1]
        cls.fixture = yaml.safe_load(
            (cls.slice_root / "fixtures" / "market-semantic-fields.synthetic.yaml").read_text(encoding="utf-8")
        )
        cls.field_schema = json.loads(
            (cls.slice_root / "MARKET-SEMANTIC-FIELD-SPEC.schema.json").read_text(encoding="utf-8")
        )
        cls.cap_schema = json.loads(
            (cls.slice_root / "PROVIDER-CAPABILITY-OBSERVATION.schema.json").read_text(encoding="utf-8")
        )

    def test_all_field_fixtures_validate_closed_schema(self):
        for item in self.fixture["field_specs"]:
            jsonschema.Draft202012Validator(self.field_schema).validate(item)

    def test_all_capability_fixtures_validate_closed_schema(self):
        for item in self.fixture["capability_observations"]:
            jsonschema.Draft202012Validator(self.cap_schema).validate(item)

    def test_tdx_volume_unit_remains_unverified_not_guessed(self):
        volume = next(item for item in self.fixture["field_specs"] if item["source_field_name"] == "Volume")
        self.assertEqual(volume["unit_kind"], "SOURCE_UNIT_UNVERIFIED")
        self.assertEqual(volume["unit_symbol"], "UNKNOWN")
        self.assertFalse(volume["canonical_persistable"])

    def test_tdx_documentation_fixture_cannot_mint_local_runtime_truth(self):
        observation = self.fixture["capability_observations"][0]
        self.assertEqual(observation["evidence_class"], "OFFICIAL_DOCUMENTED")
        self.assertFalse(observation["local_runtime_observed"])
        self.assertEqual(observation["observed_fields"], [])

    def test_tdx_bsflag_fixture_preserves_unknown(self):
        spec = next(item for item in self.fixture["field_specs"] if item["source_field_name"] == "BSFlag")
        self.assertEqual(spec["source_enum_map"], {"0": "BUY", "1": "SELL", "2": "UNKNOWN"})

    def test_schemas_forbid_unknown_top_level_authority_fields(self):
        mutated = dict(self.fixture["capability_observations"][0])
        mutated["trade_authorized"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(self.cap_schema).validate(mutated)


class AuthorityBoundaryTests(unittest.TestCase):
    def test_market_semantic_spec_has_no_trade_or_decision_authority_field(self):
        fields = set(MarketSemanticFieldSpec.__dataclass_fields__)
        self.assertFalse(
            fields
            & {
                "trade_authorized",
                "order_authority",
                "position_authority",
                "risk_override_authority",
                "decision_authority",
                "probability_authority",
            }
        )

    def test_capability_observation_has_no_trade_or_rule_authority_field(self):
        fields = set(ProviderCapabilityObservation.__dataclass_fields__)
        self.assertFalse(
            fields
            & {
                "trade_authorized",
                "rule_authority",
                "market_data_system_of_record",
                "probability_authority",
                "mastery_authority",
            }
        )


if __name__ == "__main__":
    unittest.main()
