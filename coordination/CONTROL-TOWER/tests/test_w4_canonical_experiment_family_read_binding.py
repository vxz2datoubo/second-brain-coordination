"""Compatibility entry point for control-tower test discovery.

The authoritative tests live at repository root as required by R190.
"""
from tests.test_w4_canonical_experiment_family_read_binding import CanonicalReadBindingTests


__all__ = ["CanonicalReadBindingTests"]
