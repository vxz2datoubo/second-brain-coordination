from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PHASE_ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ROOT = PHASE_ROOT.parent
for source_root in (PHASE_ROOT / "src", PROGRAM_ROOT / "PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION" / "src", PROGRAM_ROOT / "PHASE-2-OFFLINE-VERTICAL-SLICE" / "src"):
    sys.path.insert(0, str(source_root))

from integrated_offline_memory.memory_store import MemoryStore
from integrated_offline_memory.recurring_candidate_soak import (
    FROZEN_CANARY_STORE_LEAF, LEDGER_LEAF, LOCK_LEAF, OPERATIONAL_STORE_LEAF,
    RecurringCandidateSoakError, load_stable_daily_v2_snapshot, run_recurring_candidate_ingestion,
)
from integrated_offline_memory.retrieval import ContextAssembler, QueryPlan


FIXTURE = PHASE_ROOT / "tests" / "fixtures" / "daily_memory_candidate_v2_enabled_contract.json"


def package() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def write_package(root: Path, value: dict) -> Path:
    source = root / "bound-daily-v2.json"
    source.write_text(json.dumps(value), encoding="utf-8")
    return source


class RecurringCandidateSoakTest(unittest.TestCase):
    def test_persistence_replay_incremental_and_private_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = write_package(root, package())
            first = run_recurring_candidate_ingestion(source, root)
            self.assertEqual(first["status"], "IMPORTED")
            self.assertTrue(first["exact_imported_atom_recalled"])
            replay = run_recurring_candidate_ingestion(source, root)
            self.assertEqual(replay["status"], "NO_CHANGE")
            self.assertEqual(replay["duplicate_count"], 1)
            later = package(); candidate = copy.deepcopy(later["MEMORY_CANDIDATES"][0]); candidate["candidate_id"] = "opaque-later-user-decision"; candidate["statement"] = "synthetic later marker"; later["MEMORY_CANDIDATES"].append(candidate); later["DERIVED_DAILY_PROJECTION"]["supporting_candidate_ids"].append(candidate["candidate_id"]); later["VALIDATION"]["candidate_dispositions"][candidate["candidate_id"]] = "ACCEPTED"; later["VALIDATION"]["sensitivity_by_candidate"][candidate["candidate_id"]] = "PRIVATE_OR_SENSITIVE"; write_package(root, later)
            incremental = run_recurring_candidate_ingestion(source, root)
            self.assertEqual(incremental["imported_count"], 1)
            self.assertEqual(incremental["duplicate_count"], 1)
            ledger = (root / LEDGER_LEAF).read_text(encoding="utf-8")
            self.assertNotIn("statement", ledger)
            self.assertNotIn(package()["MEMORY_CANDIDATES"][0]["statement"], ledger)
            self.assertNotIn("local-private://", ledger)
            store = MemoryStore(root / OPERATIONAL_STORE_LEAF).connect()
            try: self.assertEqual(store.stats()["atoms"], 2)
            finally: store.close()

    def test_correction_atomic_failure_and_zero_noop(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = write_package(root, package()); run_recurring_candidate_ingestion(source, root)
            correction = package(); correction["CONVERSATION_EPISODES"] = [copy.deepcopy(correction["CONVERSATION_EPISODES"][0])]; correction["CONVERSATION_EPISODES"][0]["episode_id"] = "opaque-correction-episode"; correction["MEMORY_CANDIDATES"] = [{"candidate_id":"opaque-correction","candidate_type":"USER_CORRECTION","statement":"synthetic correction","supporting_episode_ids":["opaque-correction-episode"],"valid_from":"2026-08-12T02:00:00+08:00","valid_to":None,"recorded_at":"2026-08-12T02:00:00+08:00","sensitivity_class":"PRIVATE_OR_SENSITIVE","correction_target":{"replaces_candidate_id":"opaque-user-memory-001","relation_provenance":"synthetic"}}]; correction["DERIVED_DAILY_PROJECTION"]["supporting_episode_ids"]=["opaque-correction-episode"]; correction["DERIVED_DAILY_PROJECTION"]["supporting_candidate_ids"]=["opaque-correction"]; correction["VALIDATION"]["candidate_dispositions"]={"opaque-correction":"ACCEPTED"}; correction["VALIDATION"]["sensitivity_by_candidate"]={"opaque-correction":"PRIVATE_OR_SENSITIVE"}; write_package(root, correction); self.assertEqual(run_recurring_candidate_ingestion(source, root)["imported_count"], 1)
            store = MemoryStore(root / OPERATIONAL_STORE_LEAF).connect()
            try:
                current = ContextAssembler(store).assemble(QueryPlan(query_text="synthetic", scopes=("opaque-project-a",), user_scope="opaque-user-a", valid_at="2026-08-12T03:00:00+08:00", truth_states=("candidate",), intent="CURRENT"))
                self.assertEqual(len(current.atoms), 1)
                before = store.stats()
            finally: store.close()
            invalid = copy.deepcopy(correction); invalid["MEMORY_CANDIDATES"].append(copy.deepcopy(correction["MEMORY_CANDIDATES"][0])); invalid["MEMORY_CANDIDATES"][1]["candidate_id"]="opaque-invalid"; invalid["DERIVED_DAILY_PROJECTION"]["supporting_candidate_ids"].append("opaque-invalid"); invalid["VALIDATION"]["candidate_dispositions"]["opaque-invalid"]="ACCEPTED"; invalid["VALIDATION"]["sensitivity_by_candidate"]["opaque-invalid"]="PRIVATE_OR_SENSITIVE"; write_package(root, invalid)
            with self.assertRaises(RecurringCandidateSoakError): run_recurring_candidate_ingestion(source, root)
            store = MemoryStore(root / OPERATIONAL_STORE_LEAF).connect()
            try: self.assertEqual(store.stats(), before)
            finally: store.close()
            zero = package(); zero["VALIDATION"]["candidate_dispositions"]["opaque-user-memory-001"]="NON_DURABLE"; write_package(root, zero); self.assertEqual(run_recurring_candidate_ingestion(source, root)["status"], "NO_ELIGIBLE_USER_MEMORY_CANDIDATES")

    def test_adversarial_guards_and_frozen_canary_protection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = write_package(root, package())
            (root / LOCK_LEAF).write_text("", encoding="ascii")
            with self.assertRaisesRegex(RecurringCandidateSoakError, "CONCURRENT_RUN_REJECTED"): run_recurring_candidate_ingestion(source, root)
            (root / LOCK_LEAF).unlink()
            secret = package(); secret["MEMORY_CANDIDATES"][0]["statement"] = "sk-abcdefghijklmnopqrstuvwxyz012345"; write_package(root, secret)
            with self.assertRaisesRegex(RecurringCandidateSoakError, "INGESTION_REJECTED"): run_recurring_candidate_ingestion(source, root)
            with self.assertRaisesRegex(RecurringCandidateSoakError, "FROZEN_CANARY_STORE_DENIED"): run_recurring_candidate_ingestion(source, root, store_path=root / FROZEN_CANARY_STORE_LEAF)
            self.assertFalse((root / FROZEN_CANARY_STORE_LEAF).exists())

    def test_source_instability_fails_before_store_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = write_package(root, package())
            with patch("integrated_offline_memory.recurring_candidate_soak._stat_signature", side_effect=[(1, 1, 1, 1), (1, 1, 2, 1)]):
                with self.assertRaisesRegex(RecurringCandidateSoakError, "SOURCE_UNSTABLE"):
                    run_recurring_candidate_ingestion(source, root)
            self.assertFalse((root / OPERATIONAL_STORE_LEAF).exists())
