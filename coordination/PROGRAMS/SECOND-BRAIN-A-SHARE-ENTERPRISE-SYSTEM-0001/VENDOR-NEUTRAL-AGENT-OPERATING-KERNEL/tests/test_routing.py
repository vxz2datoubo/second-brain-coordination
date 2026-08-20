from __future__ import annotations

from dataclasses import replace
import unittest

from _support import capability, meta, with_display_name
from vendor_neutral_agent_kernel.canonical import seal_contract
from vendor_neutral_agent_kernel.contracts import (
    CapabilityAvailability,
    SideEffectClass,
)
from vendor_neutral_agent_kernel.routing import CapabilityRequest, route_capability


class RoutingTests(unittest.TestCase):
    def request(self, **changes):
        values = {
            "capability_id": "market.snapshot",
            "required_semantics": ("snapshot", "source_time"),
            "maximum_freshness_ms": 1000,
            "maximum_latency_ms": 500,
            "minimum_quota_remaining": 1,
            "maximum_cost_units": 5.0,
            "allowed_side_effects": (SideEffectClass.READ_ONLY,),
        }
        values.update(changes)
        return CapabilityRequest(**values)

    def test_selects_higher_evidence_route(self):
        result = route_capability(
            meta("route"),
            self.request(),
            (
                capability("provider-a", quality=0.6, reliability=0.7),
                capability("provider-b", quality=0.95, reliability=0.95),
            ),
        )
        self.assertEqual(result.selected_provider_id, "provider-b")

    def test_display_brand_name_does_not_change_route_hash_or_score(self):
        original = capability("stable-provider-id", display_name="Brand Alpha")
        renamed = seal_contract(
            with_display_name(original, "Completely Different Brand")
        )
        left = route_capability(meta("route-left"), self.request(), (original,))
        right = route_capability(meta("route-right"), self.request(), (renamed,))
        self.assertEqual(left.decision_hash, right.decision_hash)
        self.assertEqual(left.candidates[0].score, right.candidates[0].score)

    def test_missing_semantics_is_rejected(self):
        result = route_capability(
            meta("route"),
            self.request(),
            (capability("provider-a", semantics=("snapshot",)),),
        )
        self.assertIsNone(result.selected_provider_id)
        self.assertTrue(any(item.startswith("MISSING_SEMANTICS") for item in result.candidates[0].rejection_reasons))

    def test_stale_provider_falls_back(self):
        result = route_capability(
            meta("route"),
            self.request(),
            (
                capability("stale", freshness_ms=5000),
                capability("fresh", freshness_ms=100),
            ),
        )
        self.assertEqual(result.selected_provider_id, "fresh")
        stale = next(item for item in result.candidates if item.provider_id == "stale")
        self.assertIn("STALE", stale.rejection_reasons)

    def test_rate_limited_provider_falls_back(self):
        result = route_capability(
            meta("route"),
            self.request(),
            (
                capability("limited", availability=CapabilityAvailability.RATE_LIMITED),
                capability("available"),
            ),
        )
        self.assertEqual(result.selected_provider_id, "available")

    def test_disallowed_side_effect_is_rejected(self):
        result = route_capability(
            meta("route"),
            self.request(),
            (capability("writer", side_effect=SideEffectClass.EXTERNAL_REVERSIBLE),),
        )
        self.assertIsNone(result.selected_provider_id)
        self.assertIn("SIDE_EFFECT_NOT_ALLOWED", result.candidates[0].rejection_reasons)

    def test_insufficient_quota_is_rejected(self):
        result = route_capability(
            meta("route"),
            self.request(minimum_quota_remaining=2),
            (capability("empty", quota=1),),
        )
        self.assertIsNone(result.selected_provider_id)
        self.assertIn("QUOTA_INSUFFICIENT", result.candidates[0].rejection_reasons)

    def test_excess_cost_is_rejected(self):
        result = route_capability(
            meta("route"),
            self.request(maximum_cost_units=1.0),
            (capability("expensive", cost=2.0),),
        )
        self.assertIsNone(result.selected_provider_id)
        self.assertIn("COST_EXCEEDED", result.candidates[0].rejection_reasons)

    def test_excess_latency_is_rejected(self):
        result = route_capability(
            meta("route"),
            self.request(maximum_latency_ms=10),
            (capability("slow", latency_ms=100),),
        )
        self.assertIsNone(result.selected_provider_id)
        self.assertIn("LATENCY_EXCEEDED", result.candidates[0].rejection_reasons)

    def test_all_rejected_returns_explicit_no_selection(self):
        result = route_capability(
            meta("route"),
            self.request(),
            (
                capability("unknown", availability=CapabilityAvailability.UNKNOWN),
                capability("wrong", semantics=("different",)),
            ),
        )
        self.assertIsNone(result.selected_provider_id)
        self.assertEqual(result.fallback_order, ())

    def test_descriptor_input_order_does_not_change_selected_route(self):
        first = capability("provider-a", quality=0.8)
        second = capability("provider-b", quality=0.9)
        left = route_capability(meta("left"), self.request(), (first, second))
        right = route_capability(meta("right"), self.request(), (second, first))
        self.assertEqual(left.selected_provider_id, right.selected_provider_id)
        self.assertEqual(left.decision_hash, right.decision_hash)

    def test_capability_request_rejects_duplicate_semantics(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_SEMANTIC"):
            self.request(required_semantics=("snapshot", "snapshot"))


if __name__ == "__main__":
    unittest.main()
