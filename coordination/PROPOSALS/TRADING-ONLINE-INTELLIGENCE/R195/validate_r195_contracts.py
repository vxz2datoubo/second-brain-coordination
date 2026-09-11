from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parent
PACKET_SCHEMA = json.loads((ROOT / "ONLINE-TRADING-EVIDENCE-PACKET.schema.json").read_text(encoding="utf-8"))
ENVELOPE_SCHEMA = json.loads((ROOT / "CONNECTED-PROVIDER-OBSERVATION.schema.json").read_text(encoding="utf-8"))
EXAMPLE = json.loads((ROOT / "ONLINE-TRADING-EVIDENCE-PACKET.example.json").read_text(encoding="utf-8"))
FORMAT = FormatChecker()


def validator(schema: dict) -> Draft202012Validator:
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FORMAT)


def expect_valid(name: str, instance: dict, schema: dict) -> None:
    validator(schema).validate(instance)
    print(f"PASS valid: {name}")


def expect_invalid(name: str, instance: dict, schema: dict) -> None:
    try:
        validator(schema).validate(instance)
    except ValidationError:
        print(f"PASS rejected: {name}")
        return
    raise AssertionError(f"expected rejection but schema accepted: {name}")


def minimal_envelope() -> dict:
    return {
        "observation_id": "R195-TEST-OBS",
        "provider": "test-provider",
        "product": "test-product",
        "capability_id": "quote",
        "transport_class": "CHATGPT_PLUGIN",
        "evidence_class": "CONNECTED_ONLINE_RUNTIME_OBSERVED",
        "observed_at": "2026-09-10T00:00:00Z",
        "connected_online_runtime_observed": True,
        "local_runtime_observed": False,
        "entitlement_state": "OBSERVED",
        "observed_fields": ["last"],
        "semantic_field_refs": [],
        "source_refs": ["test-source"],
        "freshness_state": "FRESH",
        "missingness_state": "PRESENT",
        "ambiguity_flags": ["NONE"],
        "invalidation_conditions": ["provider changes"],
        "next_verification_action": "recheck",
    }


def main() -> None:
    expect_valid("example evidence packet", EXAMPLE, PACKET_SCHEMA)

    widened = copy.deepcopy(EXAMPLE)
    widened["authority_boundary"]["place_order"] = True
    expect_invalid("place_order authority widening", widened, PACKET_SCHEMA)

    local = minimal_envelope()
    local["local_runtime_observed"] = True
    expect_invalid("connected observation masquerades as local runtime", local, ENVELOPE_SCHEMA)

    minted = minimal_envelope()
    minted["evidence_class"] = "LOCAL_RUNTIME_VERIFIED"
    expect_invalid("connected envelope mints LOCAL_RUNTIME_VERIFIED", minted, ENVELOPE_SCHEMA)

    not_observed = minimal_envelope()
    not_observed["connected_online_runtime_observed"] = False
    expect_invalid("OBSERVED class without connected-runtime observation", not_observed, ENVELOPE_SCHEMA)

    ambiguous_fact = copy.deepcopy(EXAMPLE)
    ambiguous_fact["normalized_market_facts"] = [{
        "fact_id": "AMBIGUOUS-MARKETCAP",
        "subject": "301689.SZ",
        "field": "marketcap",
        "value": 50106812328,
        "semantic_field_ref": "unverified-made-up-ref",
        "provider": "Longbridge",
        "source_timestamp": None,
        "observed_at": "2026-09-10T23:20:04Z",
    }]
    expect_invalid("ambiguous fact without normalization gate", ambiguous_fact, PACKET_SCHEMA)

    verified_shape = copy.deepcopy(EXAMPLE)
    verified_shape["normalized_market_facts"] = [{
        "fact_id": "SHAPE-ONLY-VERIFIED-FACT",
        "subject": "300418.SZ",
        "field": "last_price",
        "value": "44.26",
        "semantic_field_ref": "MarketSemanticFieldSpec/example",
        "semantic_field_digest": "0" * 64,
        "semantic_verification_state": "VERIFIED",
        "unit_semantics_state": "RESOLVED",
        "ambiguity_flags": [],
        "source_observation_ref": "R195-TEST-OBS",
        "provider": "Longbridge",
        "source_timestamp": "2026-09-10T07:00:00Z",
        "observed_at": "2026-09-10T23:46:56Z",
    }]
    expect_valid("normalized fact verified structural gate", verified_shape, PACKET_SCHEMA)

    pit_false_upgrade = copy.deepcopy(EXAMPLE)
    pit_false_upgrade["candidate_funnel_state"]["pit_identity_state"] = "VERIFIED"
    pit_false_upgrade["candidate_funnel_state"]["market_data_as_of"] = None
    pit_false_upgrade["candidate_funnel_state"]["market_session_date"] = None
    expect_invalid("PIT VERIFIED without bound market-data identity", pit_false_upgrade, PACKET_SCHEMA)

    print("PASS: R195 deterministic contract checks complete")
    print("NOTE: semantic_field_ref/digest referential integrity requires runtime verification against canonical W2; JSON Schema only enforces the structural gate.")


if __name__ == "__main__":
    main()
