from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import unittest

SLICE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SLICE_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    import jsonschema
except ModuleNotFoundError:
    jsonschema = None
import yaml

from offline_research.market_semantics import (
    MARKET_SEMANTIC_FIELD_SCHEMA_DIGEST_V1,
    PROVIDER_CAPABILITY_SCHEMA_DIGEST_V1,
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
    require_governed_semantic_spec,
    require_point_in_time,
    semantic_digest,
    semantic_identity_digest_from_mapping,
    validate_governed_tick_aligned,
    validate_tick_aligned,
)


def _jsonable_field_value(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, tuple):
        return [x.value if hasattr(x, "value") else x for x in value]
    return value


def _raw_spec(spec):
    return {
        name: _jsonable_field_value(getattr(spec, name))
        for name in MarketSemanticFieldSpec.__dataclass_fields__
    }


def _build_spec(**overrides):
    raw = dict(
        semantic_field_id="SYNTHETIC.TRADE.PRICE.V1",
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
        tick_size_ref=None,
        rounding_policy="EXACT_NO_IMPLICIT_ROUNDING",
        price_semantic="RAW_TRADE_PRICE",
        time_semantic=None,
        adjustment_state="RAW",
        source_enum_map={},
        allowed_missing_states=["PRESENT", "UNKNOWN"],
        canonical_persistable=True,
        valid_from=None,
        valid_until=None,
        source_ref="synthetic:source",
        evidence_ref="synthetic:evidence",
        schema_digest=MARKET_SEMANTIC_FIELD_SCHEMA_DIGEST_V1,
        observed_at="2026-09-01T00:00:00+08:00",
        last_verified_at="2026-09-01T00:00:00+08:00",
    )
    raw.update(overrides)
    raw["semantic_digest"] = semantic_identity_digest_from_mapping(raw)
    return MarketSemanticFieldSpec(**raw)


def _mutate_spec(spec, **changes):
    raw = _raw_spec(spec)
    raw.update(changes)
    raw["semantic_digest"] = semantic_identity_digest_from_mapping(raw)
    return MarketSemanticFieldSpec(**raw)


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
        semantic_field_refs=("TDXQUANT.TICK.PRICE.DOCREF.V1",),
        evidence_refs=("official:https://help.tdx.com.cn/quant/",),
        invalidation_conditions=("documentation_change", "runtime_upgrade"),
        next_verification_action="A/B reconcile installed runtime under separate authority",
    )
    base.update(overrides)
    return ProviderCapabilityObservation(**base)


class FixtureMixin:
    @classmethod
    def setUpClass(cls):
        cls.fixture = yaml.safe_load(
            (SLICE_ROOT / "fixtures" / "market-semantic-fields.synthetic.yaml").read_text(
                encoding="utf-8"
            )
        )

    def fixture_spec(self, source_field_name):
        item = next(
            row for row in self.fixture["field_specs"]
            if row["source_field_name"] == source_field_name
        )
        return MarketSemanticFieldSpec(**item)


class NumericSemanticsTests(unittest.TestCase):
    def test_binary_float_is_rejected(self):
        with self.assertRaisesRegex(SemanticValidationError, "BINARY_FLOAT_FORBIDDEN"):
            parse_fixed_decimal(0.05)

    def test_decimal_string_is_exact(self):
        self.assertEqual(parse_fixed_decimal("0.05"), Decimal("0.05"))

    def test_fraction_to_percent_requires_explicit_factor(self):
        with self.assertRaisesRegex(
            SemanticValidationError, "EXPLICIT_CONVERSION_FACTOR_REQUIRED"
        ):
            explicit_unit_convert(
                "0.05", from_unit="FRACTION", to_unit="PERCENT", factor=None
            )
        self.assertEqual(
            explicit_unit_convert(
                "0.05", from_unit="FRACTION", to_unit="PERCENT", factor="100"
            ),
            Decimal("5.00"),
        )

    def test_percent_to_fraction_is_explicit(self):
        self.assertEqual(
            explicit_unit_convert(
                "5", from_unit="PERCENT", to_unit="FRACTION", factor="0.01"
            ),
            Decimal("0.05"),
        )

    def test_shares_vs_lots_cannot_convert_implicitly(self):
        with self.assertRaisesRegex(
            SemanticValidationError, "EXPLICIT_CONVERSION_FACTOR_REQUIRED"
        ):
            explicit_unit_convert(
                "1000", from_unit="SHARES", to_unit="LOTS", factor=None
            )

    def test_yuan_vs_ten_thousand_yuan_cannot_convert_implicitly(self):
        with self.assertRaisesRegex(
            SemanticValidationError, "EXPLICIT_CONVERSION_FACTOR_REQUIRED"
        ):
            explicit_unit_convert(
                "10000", from_unit="CNY", to_unit="TEN_THOUSAND_CNY", factor=None
            )

    def test_display_price_cannot_be_canonical(self):
        with self.assertRaisesRegex(
            SemanticValidationError, "DISPLAY_PRICE_CANNOT_BE_CANONICAL"
        ):
            _build_spec(price_semantic="DISPLAY_PRICE", canonical_persistable=True)

    def test_off_tick_price_fails(self):
        with self.assertRaisesRegex(
            SemanticValidationError, "PRICE_NOT_TICK_ALIGNED"
        ):
            validate_tick_aligned("10.005", _build_spec())

    def test_on_tick_price_passes(self):
        self.assertEqual(
            validate_tick_aligned("10.05", _build_spec()), Decimal("10.05")
        )

    def test_rule_bound_tick_requires_resolution(self):
        spec = _build_spec(tick_size=None, tick_size_ref="AShareRuleSnapshot.tick_size")
        with self.assertRaisesRegex(
            SemanticValidationError, "TICK_SIZE_RULE_RESOLUTION_REQUIRED"
        ):
            validate_tick_aligned("10.05", spec)

    def test_explicit_tick_normalization_carries_original_and_policy(self):
        receipt = normalize_to_tick("10.005", "0.01")
        self.assertEqual(receipt.original, Decimal("10.005"))
        self.assertEqual(receipt.normalized, Decimal("10.00"))
        self.assertEqual(receipt.policy, "ROUND_HALF_EVEN_EXPLICIT")

    def test_ungoverned_spec_cannot_enter_governed_value_path(self):
        with self.assertRaisesRegex(
            SemanticValidationError, "SEMANTIC_REGISTRY_BINDING_REQUIRED"
        ):
            validate_governed_tick_aligned("10.05", _build_spec())


class DirectionAuthorityTests(FixtureMixin, unittest.TestCase):
    def test_documented_buy_sell_unknown_mapping(self):
        spec = self.fixture_spec("BSFlag")
        self.assertEqual(map_direction("0", spec), CanonicalDirection.BUY)
        self.assertEqual(map_direction("1", spec), CanonicalDirection.SELL)
        self.assertEqual(map_direction("2", spec), CanonicalDirection.UNKNOWN)

    def test_unknown_direction_is_not_coerced(self):
        self.assertIs(
            map_direction(2, self.fixture_spec("BSFlag")),
            CanonicalDirection.UNKNOWN,
        )

    def test_absent_direction_does_not_become_zero(self):
        with self.assertRaisesRegex(SemanticValidationError, "DIRECTION_MISSING"):
            map_direction(None, self.fixture_spec("BSFlag"))

    def test_unmapped_enum_fails_closed(self):
        with self.assertRaisesRegex(SemanticValidationError, "ENUM_VALUE_UNMAPPED"):
            map_direction("9", self.fixture_spec("BSFlag"))

    def test_reversed_mapping_fails_in_normal_consuming_path(self):
        spec = self.fixture_spec("BSFlag")
        forged = _mutate_spec(
            spec, source_enum_map={"0": "SELL", "1": "BUY", "2": "UNKNOWN"}
        )
        with self.assertRaisesRegex(
            SemanticValidationError, "SEMANTIC_REGISTRY_DIGEST_MISMATCH"
        ):
            map_direction("0", forged)

    def test_recomputed_digest_does_not_mint_direction_authority(self):
        spec = self.fixture_spec("BSFlag")
        forged = _mutate_spec(
            spec,
            source_enum_map={"0": "SELL", "1": "BUY", "2": "UNKNOWN"},
            evidence_ref="caller:self-described-new-map",
        )
        self.assertEqual(forged.semantic_digest, semantic_digest(forged))
        with self.assertRaisesRegex(
            SemanticValidationError, "SEMANTIC_REGISTRY_DIGEST_MISMATCH"
        ):
            map_direction("0", forged)

    def test_source_version_drift_forces_revalidation(self):
        spec = self.fixture_spec("BSFlag")
        drifted = _mutate_spec(spec, source_version="CALLER_NEW_VERSION")
        with self.assertRaisesRegex(
            SemanticValidationError, "SEMANTIC_REGISTRY_BINDING_REQUIRED"
        ):
            map_direction("0", drifted)

    def test_optional_assertion_is_not_the_authority(self):
        spec = self.fixture_spec("BSFlag")
        assert_direction_contract(
            spec,
            {"0": CanonicalDirection.BUY,
             "1": CanonicalDirection.SELL,
             "2": CanonicalDirection.UNKNOWN},
        )


class ProvenanceIdentityTests(FixtureMixin, unittest.TestCase):
    def test_all_fixture_specs_are_registry_bound(self):
        for row in self.fixture["field_specs"]:
            spec = MarketSemanticFieldSpec(**row)
            self.assertIs(require_governed_semantic_spec(spec), spec)

    def test_schema_digest_is_bound_to_actual_schema_bytes(self):
        parsed = json.loads(
            (SLICE_ROOT / "MARKET-SEMANTIC-FIELD-SPEC.schema.json").read_text(encoding="utf-8")
        )
        actual = hashlib.sha256(
            json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        self.assertEqual(actual, MARKET_SEMANTIC_FIELD_SCHEMA_DIGEST_V1)

    def test_capability_schema_digest_constant_matches_file(self):
        parsed = json.loads(
            (SLICE_ROOT / "PROVIDER-CAPABILITY-OBSERVATION.schema.json").read_text(encoding="utf-8")
        )
        actual = hashlib.sha256(
            json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        self.assertEqual(actual, PROVIDER_CAPABILITY_SCHEMA_DIGEST_V1)

    def test_wrong_schema_digest_fails_before_consumption(self):
        raw = dict(self.fixture["field_specs"][0])
        raw["schema_digest"] = "0" * 64
        raw["semantic_digest"] = semantic_identity_digest_from_mapping(raw)
        with self.assertRaisesRegex(
            SemanticValidationError, "SCHEMA_DIGEST_MISMATCH"
        ):
            MarketSemanticFieldSpec(**raw)

    def test_content_tamper_with_stale_digest_fails(self):
        raw = dict(self.fixture["field_specs"][0])
        raw["unit_symbol"] = "USD"
        with self.assertRaisesRegex(
            SemanticValidationError, "SEMANTIC_DIGEST_CONTENT_MISMATCH"
        ):
            MarketSemanticFieldSpec(**raw)

    def test_content_tamper_with_fresh_digest_still_not_governed(self):
        spec = self.fixture_spec("Price")
        forged = _mutate_spec(spec, unit_symbol="USD")
        self.assertEqual(forged.semantic_digest, semantic_digest(forged))
        with self.assertRaisesRegex(
            SemanticValidationError, "SEMANTIC_REGISTRY_DIGEST_MISMATCH"
        ):
            require_governed_semantic_spec(forged)

    def test_evidence_ref_tamper_with_fresh_digest_still_not_governed(self):
        spec = self.fixture_spec("Price")
        forged = _mutate_spec(spec, evidence_ref="caller:alternate-evidence")
        with self.assertRaisesRegex(
            SemanticValidationError, "SEMANTIC_REGISTRY_DIGEST_MISMATCH"
        ):
            require_governed_semantic_spec(forged)

    def test_observed_at_is_part_of_semantic_identity(self):
        spec = self.fixture_spec("Price")
        changed = _mutate_spec(spec, observed_at="2026-09-02T00:00:00-05:00")
        self.assertNotEqual(spec.semantic_digest, changed.semantic_digest)
        with self.assertRaisesRegex(
            SemanticValidationError, "SEMANTIC_REGISTRY_DIGEST_MISMATCH"
        ):
            require_governed_semantic_spec(changed)


class TimeAndMissingnessTests(unittest.TestCase):
    def test_available_at_is_required_for_pit(self):
        with self.assertRaisesRegex(SemanticValidationError, "AVAILABLE_AT_REQUIRED"):
            require_point_in_time(
                {"published_at": "2026-09-01T09:30:00+08:00"}
            )

    def test_published_at_cannot_substitute_for_available_at(self):
        with self.assertRaisesRegex(SemanticValidationError, "AVAILABLE_AT_REQUIRED"):
            require_point_in_time(
                {
                    "event_time": "2026-09-01T09:29:59+08:00",
                    "published_at": "2026-09-01T09:30:00+08:00",
                }
            )

    def test_timezone_is_required(self):
        with self.assertRaisesRegex(SemanticValidationError, "TIMEZONE_REQUIRED"):
            require_point_in_time({"available_at": "2026-09-01T09:30:00"})

    def test_zero_is_present_not_missing(self):
        value, state = classify_value(0, MissingState.PRESENT)
        self.assertEqual(value, 0)
        self.assertEqual(state, MissingState.PRESENT)

    def test_missing_state_requires_null(self):
        with self.assertRaisesRegex(
            SemanticValidationError, "MISSING_STATE_REQUIRES_NULL_VALUE"
        ):
            classify_value(0, MissingState.SOURCE_MISSING)

    def test_missing_states_remain_distinct(self):
        states = {
            classify_value(None, MissingState.SOURCE_MISSING)[1],
            classify_value(None, MissingState.STALE)[1],
            classify_value(
                None, MissingState.PERMISSION_OR_ENTITLEMENT_UNVERIFIED
            )[1],
            classify_value(None, MissingState.UNKNOWN)[1],
        }
        self.assertEqual(len(states), 4)


class CapabilityEvidenceTests(unittest.TestCase):
    def test_official_documentation_does_not_satisfy_local_runtime_gate(self):
        with self.assertRaisesRegex(
            SemanticValidationError, "LOCAL_RUNTIME_CAPABILITY_NOT_VERIFIED"
        ):
            require_capability(
                documented_capability(), require_local_runtime=True
            )

    def test_official_documentation_cannot_claim_local_runtime(self):
        with self.assertRaisesRegex(
            SemanticValidationError,
            "DOCUMENTATION_OBSERVATION_CANNOT_CLAIM_LOCAL_RUNTIME",
        ):
            documented_capability(local_runtime_observed=True)

    def test_caller_cannot_mint_local_runtime_verified_with_local_prefix(self):
        with self.assertRaisesRegex(
            SemanticValidationError, "EXTERNAL_LOCAL_RUNTIME_AUTHORITY_REQUIRED"
        ):
            ProviderCapabilityObservation(
                observation_id="caller-minted",
                provider="TDX",
                product="TdxQuant",
                capability_id="GET_TICK_DATA",
                method="get_tick_data",
                evidence_class=CapabilityEvidenceClass.LOCAL_RUNTIME_VERIFIED,
                observed_at="2026-09-02T00:00:00+08:00",
                local_runtime_observed=True,
                runtime_version="9.9.9-caller",
                observed_fields=("Time", "Price", "Volume", "BSFlag"),
                entitlement_state="CALLER_SAYS_OK",
                evidence_refs=("local:anything",),
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
        with self.assertRaisesRegex(
            SemanticValidationError, "CAPABILITY_OBSERVATION_IMMUTABLE"
        ):
            append_capability_observation((first,), changed)

    def test_identical_reappend_is_idempotent(self):
        first = documented_capability()
        self.assertEqual(
            append_capability_observation((first,), first), (first,)
        )


class DriftAndDigestTests(FixtureMixin, unittest.TestCase):
    def test_unit_drift_is_typed(self):
        old = self.fixture_spec("Price")
        new = _mutate_spec(old, unit_symbol="USD")
        self.assertIn(DriftKind.UNIT_DRIFT, detect_field_drift(old, new))

    def test_direction_and_enum_drift_are_typed(self):
        old = self.fixture_spec("BSFlag")
        new = _mutate_spec(
            old, source_enum_map={"0": "SELL", "1": "BUY", "2": "UNKNOWN"}
        )
        drift = detect_field_drift(old, new)
        self.assertIn(DriftKind.DIRECTION_DRIFT, drift)
        self.assertIn(DriftKind.ENUM_DRIFT, drift)

    def test_precision_drift_is_typed(self):
        old = self.fixture_spec("Price")
        new = _mutate_spec(old, tick_size="0.001", tick_size_ref=None)
        self.assertIn(DriftKind.PRECISION_DRIFT, detect_field_drift(old, new))

    def test_vendor_version_drift_is_typed(self):
        old = self.fixture_spec("Price")
        new = _mutate_spec(old, source_version="2")
        self.assertIn(DriftKind.VENDOR_VERSION_DRIFT, detect_field_drift(old, new))

    def test_time_semantic_drift_is_typed(self):
        old = self.fixture_spec("Time")
        new = _mutate_spec(old, time_semantic="AVAILABLE_AT")
        self.assertIn(
            DriftKind.TIME_SEMANTIC_DRIFT, detect_field_drift(old, new)
        )

    def test_adjustment_drift_is_typed(self):
        old = self.fixture_spec("Price")
        new = _mutate_spec(old, adjustment_state="FORWARD_ADJUSTED")
        self.assertIn(DriftKind.ADJUSTMENT_DRIFT, detect_field_drift(old, new))

    def test_missingness_drift_is_typed(self):
        old = self.fixture_spec("Price")
        new = _mutate_spec(
            old, allowed_missing_states=["PRESENT", "UNKNOWN"]
        )
        self.assertIn(
            DriftKind.MISSINGNESS_DRIFT, detect_field_drift(old, new)
        )

    def test_capability_evidence_change_is_typed_without_minting_verified(self):
        old = documented_capability()
        attempted = documented_capability(
            observation_id="local-attempt",
            evidence_class=CapabilityEvidenceClass.LOCAL_RUNTIME_NOT_VERIFIED,
            documentation_version=None,
            documented_fields=(),
            runtime_version="1.2.3",
            observed_fields=("Time", "Price"),
            evidence_refs=("local-probe-request:001",),
        )
        self.assertIn(
            DriftKind.ENTITLEMENT_OR_CAPABILITY_DRIFT,
            detect_capability_drift(old, attempted),
        )

    def test_semantic_digest_is_deterministic(self):
        spec = self.fixture_spec("Price")
        self.assertEqual(semantic_digest(spec), semantic_digest(spec))
        self.assertEqual(len(semantic_digest(spec)), 64)

    def test_semantic_change_changes_digest(self):
        old = self.fixture_spec("Price")
        new = _mutate_spec(old, unit_symbol="USD")
        self.assertNotEqual(semantic_digest(old), semantic_digest(new))

    def test_capability_digest_is_deterministic(self):
        obs = documented_capability()
        self.assertEqual(capability_digest(obs), capability_digest(obs))
        self.assertEqual(len(capability_digest(obs)), 64)


class ContractFixtureTests(FixtureMixin, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.field_schema = json.loads(
            (SLICE_ROOT / "MARKET-SEMANTIC-FIELD-SPEC.schema.json").read_text(
                encoding="utf-8"
            )
        )
        cls.cap_schema = json.loads(
            (
                SLICE_ROOT / "PROVIDER-CAPABILITY-OBSERVATION.schema.json"
            ).read_text(encoding="utf-8")
        )

    @unittest.skipUnless(
        jsonschema is not None, "jsonschema is exercised by dedicated R182 CI"
    )
    def test_all_field_fixtures_validate_closed_schema(self):
        validator = jsonschema.Draft202012Validator(
            self.field_schema, format_checker=jsonschema.FormatChecker()
        )
        for item in self.fixture["field_specs"]:
            validator.validate(item)

    @unittest.skipUnless(
        jsonschema is not None, "jsonschema is exercised by dedicated R182 CI"
    )
    def test_all_capability_fixtures_validate_closed_schema(self):
        validator = jsonschema.Draft202012Validator(
            self.cap_schema, format_checker=jsonschema.FormatChecker()
        )
        for item in self.fixture["capability_observations"]:
            validator.validate(item)

    @unittest.skipUnless(
        jsonschema is not None, "jsonschema is exercised by dedicated R182 CI"
    )
    def test_schema_rejects_caller_minted_local_runtime_verified(self):
        mutated = dict(self.fixture["capability_observations"][0])
        mutated.update(
            evidence_class="LOCAL_RUNTIME_VERIFIED",
            local_runtime_observed=True,
            runtime_version="caller-version",
            observed_fields=["Time"],
            evidence_refs=["local:anything"],
        )
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(self.cap_schema).validate(mutated)

    @unittest.skipUnless(
        jsonschema is not None, "jsonschema is exercised by dedicated R182 CI"
    )
    def test_schema_requires_provenance_identity_fields(self):
        mutated = dict(self.fixture["field_specs"][0])
        del mutated["semantic_digest"]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(self.field_schema).validate(mutated)

    def test_tdx_volume_unit_remains_unverified_not_guessed(self):
        volume = next(
            item for item in self.fixture["field_specs"]
            if item["source_field_name"] == "Volume"
        )
        self.assertEqual(volume["unit_kind"], "SOURCE_UNIT_UNVERIFIED")
        self.assertEqual(volume["unit_symbol"], "UNKNOWN")
        self.assertFalse(volume["canonical_persistable"])

    def test_tdx_documentation_fixture_cannot_mint_local_runtime_truth(self):
        observation = self.fixture["capability_observations"][0]
        self.assertEqual(observation["evidence_class"], "OFFICIAL_DOCUMENTED")
        self.assertFalse(observation["local_runtime_observed"])
        self.assertEqual(observation["observed_fields"], [])

    def test_tdx_bsflag_fixture_preserves_unknown(self):
        spec = next(
            item for item in self.fixture["field_specs"]
            if item["source_field_name"] == "BSFlag"
        )
        self.assertEqual(
            spec["source_enum_map"],
            {"0": "BUY", "1": "SELL", "2": "UNKNOWN"},
        )

    @unittest.skipUnless(
        jsonschema is not None, "jsonschema is exercised by dedicated R182 CI"
    )
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
