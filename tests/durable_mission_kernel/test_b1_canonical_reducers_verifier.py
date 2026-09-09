"""B1 tests — deterministic reducers, JCS canonicalization, SHA-256 hash chain, verifier."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.durable_mission_kernel import canonical, reducers, verifier  # noqa: E402
from tools.durable_mission_kernel.schemas import EventType, MissionState, WaitState  # noqa: E402


# Golden vectors (fixed input -> fixed output, computed once and frozen).
GOLDEN_GENESIS_HASH = "a563409ca9f311474b6012094bc7528228c9e8aeb889d570fdccfe48e90ab2be"
GOLDEN_PLAN_STARTED = "e12f5595a3405b7a54565cdfcb98fde447be60d4f10456177f1d898011f26a10"
GOLDEN_PLAN_COMPLETED = "fbc190bf85dae1c0dad50ed80d9f01453960980872ca8a76c8c7449d6287ee14"
GOLDEN_JCS_1 = '{"a":{"b":"c"},"f":false,"m":null,"n":3,"pi":3.14,"t":true,"z":[1,2]}'
GOLDEN_JCS_2 = '{"f":2,"i":42,"neg":-7}'


def _genesis(**overrides):
    kw = dict(mission_id="MISSION-GOLDEN-001", run_id="RUN-GOLDEN-001",
              actor="WORKBUDDY", timestamp_iso="2026-09-09T01:58:00Z",
              payload={"phase": "B", "mode": "SYNTHETIC_AND_DISPOSABLE_FIXTURE_ONLY"})
    kw.update(overrides)
    return verifier.build_genesis_event(**kw)


class B1CanonicalTests(unittest.TestCase):
    def test_jcs_sorts_keys_and_omits_whitespace(self):
        self.assertEqual(
            canonical.jcs_dumps({"z": [1, 2], "a": {"b": "c"}, "m": None,
                                "f": False, "t": True, "n": 3, "pi": 3.14}),
            GOLDEN_JCS_1,
        )

    def test_jcs_integral_float_and_int(self):
        self.assertEqual(canonical.jcs_dumps({"i": 42, "f": 2.0, "neg": -7}), GOLDEN_JCS_2)

    def test_jcs_escapes_control_and_quote(self):
        self.assertEqual(canonical.jcs_dumps({"s": 'a"\nb'}), '{"s":"a\\"\\nb"}')

    def test_jcs_bytes_are_utf8(self):
        self.assertEqual(canonical.jcs_bytes({"k": "值"}), b'{"k":"\xe5\x80\xbc"}')


class B1ReducerTests(unittest.TestCase):
    def test_legal_transition_path(self):
        self.assertEqual(reducers.reduce_state(MissionState.CREATED.value, EventType.PLAN_STARTED.value), MissionState.PLANNING.value)
        self.assertEqual(reducers.reduce_state(MissionState.PLANNING.value, EventType.PLAN_COMPLETED.value), MissionState.READY.value)
        self.assertEqual(reducers.reduce_state(MissionState.READY.value, EventType.EPISODE_STARTED.value), MissionState.EPISODE_RUNNING.value)

    def test_illegal_transition_raises(self):
        with self.assertRaises(reducers.ReducerError):
            reducers.reduce_state(MissionState.CREATED.value, EventType.CANONICALIZATION_COMPLETED.value)

    def test_pause_from_active_state(self):
        self.assertEqual(reducers.reduce_state(MissionState.EPISODE_RUNNING.value, EventType.PAUSED_OWNER_GATE.value), WaitState.PAUSED_OWNER_GATE.value)

    def test_pause_from_wait_state_rejected(self):
        with self.assertRaises(reducers.ReducerError):
            reducers.reduce_state(WaitState.BLOCKED.value, EventType.PAUSED_OWNER_GATE.value)


class B1HashChainTests(unittest.TestCase):
    def test_golden_genesis_hash(self):
        gen = _genesis()
        self.assertEqual(gen["event_hash"], GOLDEN_GENESIS_HASH)

    def test_golden_plan_chain(self):
        gen = _genesis()
        h1 = canonical.event_hash(
            gen["event_hash"], mission_id="MISSION-GOLDEN-001", run_id="RUN-GOLDEN-001",
            state_seq=1, event_type=EventType.PLAN_STARTED.value, actor="WORKBUDDY",
            timestamp_iso="2026-09-09T01:58:00Z", payload={"plan": "durable-mission-kernel"},
        )
        h2 = canonical.event_hash(
            h1, mission_id="MISSION-GOLDEN-001", run_id="RUN-GOLDEN-001",
            state_seq=2, event_type=EventType.PLAN_COMPLETED.value, actor="WORKBUDDY",
            timestamp_iso="2026-09-09T01:58:00Z", payload={"spec_version": "1.0"},
        )
        self.assertEqual(h1, GOLDEN_PLAN_STARTED)
        self.assertEqual(h2, GOLDEN_PLAN_COMPLETED)

    def test_verify_valid_chain(self):
        gen = _genesis()
        ev1 = {
            "mission_id": "MISSION-GOLDEN-001", "run_id": "RUN-GOLDEN-001", "state_seq": 1,
            "event_type": EventType.PLAN_STARTED.value, "previous_event_hash": gen["event_hash"],
            "event_hash": GOLDEN_PLAN_STARTED, "actor": "WORKBUDDY",
            "timestamp_iso": "2026-09-09T01:58:00Z", "payload": {"plan": "durable-mission-kernel"}, "digests": {},
        }
        self.assertTrue(verifier.verify_event_chain([gen, ev1]))

    def test_tampered_hash_detected(self):
        gen = _genesis()
        ev1 = {
            "mission_id": "MISSION-GOLDEN-001", "run_id": "RUN-GOLDEN-001", "state_seq": 1,
            "event_type": EventType.PLAN_STARTED.value, "previous_event_hash": gen["event_hash"],
            "event_hash": "0" * 64, "actor": "WORKBUDDY",
            "timestamp_iso": "2026-09-09T01:58:00Z", "payload": {"plan": "durable-mission-kernel"}, "digests": {},
        }
        with self.assertRaises(verifier.ChainVerificationError):
            verifier.verify_event_chain([gen, ev1])

    def test_first_event_must_be_genesis(self):
        gen = _genesis()
        ev0 = dict(gen)
        ev0["event_type"] = EventType.PLAN_STARTED.value
        with self.assertRaises(verifier.ChainVerificationError):
            verifier.verify_event_chain([ev0])


if __name__ == "__main__":
    unittest.main()
