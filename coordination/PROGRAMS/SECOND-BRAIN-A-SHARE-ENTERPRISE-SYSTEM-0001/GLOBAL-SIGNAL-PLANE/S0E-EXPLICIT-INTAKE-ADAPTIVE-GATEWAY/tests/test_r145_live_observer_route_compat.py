"""R145 regression for R137 live-observer current route identity schema."""
from __future__ import annotations

import unittest

from global_signal_gateway.gateway import GatewayError
from global_signal_gateway.live_observation_provider import _route_binding


class CurrentRouteBindingCompatibilityTests(unittest.TestCase):
    def test_legacy_top_level_route_binding_is_retained(self):
        self.assertEqual(("TASK", 137), _route_binding({"task_id": "TASK", "route_epoch": 137}))

    def test_current_nested_binding_is_accepted_without_weakening_identity(self):
        self.assertEqual(("TASK", 144), _route_binding({"binding": {"task_id": "TASK", "route_epoch": 144}}))

    def test_dual_representations_must_agree(self):
        self.assertEqual(("TASK", 145), _route_binding({
            "task_id": "TASK", "route_epoch": 145,
            "binding": {"task_id": "TASK", "route_epoch": 145},
        }))
        with self.assertRaises(GatewayError):
            _route_binding({
                "task_id": "TASK-A", "route_epoch": 145,
                "binding": {"task_id": "TASK-B", "route_epoch": 145},
            })
        with self.assertRaises(GatewayError):
            _route_binding({
                "task_id": "TASK", "route_epoch": 145,
                "binding": {"task_id": "TASK", "route_epoch": 146},
            })

    def test_missing_or_malformed_binding_fails_closed(self):
        for value in ({}, {"binding": []}, {"binding": {"task_id": "TASK"}}, {"binding": {"route_epoch": 145}}):
            with self.subTest(value=value), self.assertRaises(GatewayError):
                _route_binding(value)


if __name__ == "__main__":
    unittest.main()
