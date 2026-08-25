"""R147 integration guard for the bounded historical merge-anchor proof."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve()
PLANE = HERE.parents[2]
S0E = PLANE / "S0E-EXPLICIT-INTAKE-ADAPTIVE-GATEWAY"
sys.path.insert(0, str(S0E / "src"))

from global_signal_gateway.gateway import GatewayError  # noqa: E402
from global_signal_gateway.live_observation_provider import (  # noqa: E402
    TARGET_REPOSITORY,
    LiveObservationProvider,
    _ANCESTRY_COMPARE_QUERY,
    _CANONICAL_MERGE_ANCHORS,
)


class R147BoundedAnchorAncestryTests(unittest.TestCase):
    def test_r147_nullable_merge_fallback_uses_only_bounded_compare_surface(self) -> None:
        _, _, merge_sha, _, _ = _CANONICAL_MERGE_ANCHORS[0]
        current_main = "a" * 40
        self.assertEqual("?per_page=1&page=2", _ANCESTRY_COMPARE_QUERY)
        with self.assertRaises(GatewayError) as caught:
            LiveObservationProvider()._get_json(
                f"/repos/{TARGET_REPOSITORY}/compare/{merge_sha}...{current_main}"
            )
        self.assertEqual("GITHUB_ENDPOINT_FORBIDDEN", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
