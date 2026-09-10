"""W4's bounded, append-only StrategyExperimentFamily registry.

This module stores synthetic/offline research provenance only.  It deliberately
has no market-data, replay, validation, probability, allocation, or trade API.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

TERMINAL = {"SUCCESS", "FAILURE", "ABORTED", "NUMERICAL_ERROR", "DATA_INVALID", "REJECTED_PRECHECK"}
EVENTS = {"FAMILY_CREATED", "TRIAL_REGISTERED", "SELECTION_RULE_REGISTERED", "FAMILY_FROZEN", "TRIAL_STARTED", "TRIAL_TERMINATED", "RERUN_REGISTERED", "CANDIDATE_FROZEN", "TRIAL_SELECTED"}

class RegistryError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}{': ' + detail if detail else ''}")
        self.code = code

def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise RegistryError("INVALID_SHA256", name)
    return value

def semantic_digest(event_type: str, payload: Mapping[str, Any]) -> str:
    return digest({"event_type": event_type, "payload": dict(payload)})

def event_digest(*, family_id: str, family_revision_id: str, family_sequence: int, event_id: str, idempotency_key: str, event_type: str, semantic_digest: str, previous_event_digest: str | None) -> str:
    return digest({"family_id": family_id, "family_revision_id": family_revision_id, "family_sequence": family_sequence, "event_id": event_id, "idempotency_key": idempotency_key, "event_type": event_type, "semantic_digest": semantic_digest, "previous_event_digest": previous_event_digest})

def registered_family_digest_v1(*, experiment_family_ref: str, expected_trial_digests: Mapping[str, str], benchmark_ref: str, metric_id: str, horizon_id: str, search_space_ref: str, selection_rule_ref: str) -> str:
    return digest({"experiment_family_ref": experiment_family_ref, "expected_trial_digests": dict(sorted(expected_trial_digests.items())), "benchmark_ref": benchmark_ref, "metric_id": metric_id, "horizon_id": horizon_id, "search_space_ref": search_space_ref, "selection_rule_ref": selection_rule_ref})

class Registry:
    def __init__(self, connection: sqlite3.Connection):
        self.db = connection
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS experiment_events (event_offset INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT NOT NULL UNIQUE,idempotency_key TEXT NOT NULL UNIQUE,family_id TEXT NOT NULL,family_revision_id TEXT NOT NULL,family_sequence INTEGER NOT NULL,event_type TEXT NOT NULL,semantic_digest TEXT NOT NULL,previous_event_digest TEXT,event_digest TEXT NOT NULL UNIQUE,record_json TEXT NOT NULL,UNIQUE(family_id,family_revision_id,family_sequence))")
        self.db.commit()

    def _rows(self, family_id: str, revision: str) -> list[sqlite3.Row]:
        return list(self.db.execute("SELECT * FROM experiment_events WHERE family_id=? AND family_revision_id=? ORDER BY family_sequence", (family_id, revision)))

    def append(self, *, family_id: str, family_revision_id: str, expected_sequence: int, event_id: str, idempotency_key: str, event_type: str, payload: Mapping[str, Any], expected_previous_digest: str | None = None) -> dict[str, Any]:
        if event_type not in EVENTS: raise RegistryError("INVALID_EVENT_TYPE")
        if not all(isinstance(x, str) and x for x in (family_id, family_revision_id, event_id, idempotency_key)): raise RegistryError("EMPTY_IDENTITY")
        material = dict(payload); semantic = semantic_digest(event_type, material)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old = self.db.execute("SELECT * FROM experiment_events WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if old:
                if all(old[k] == v for k, v in {"family_id":family_id,"family_revision_id":family_revision_id,"event_id":event_id,"event_type":event_type,"semantic_digest":semantic}.items()):
                    self.db.commit(); return {"duplicate": True, "sequence": old["family_sequence"], "event_digest": old["event_digest"]}
                raise RegistryError("IDEMPOTENCY_KEY_COLLISION")
            eid = self.db.execute("SELECT event_id FROM experiment_events WHERE event_id=?", (event_id,)).fetchone()
            if eid: raise RegistryError("EVENT_ID_COLLISION")
            rows = self._rows(family_id, family_revision_id); current = len(rows); previous = rows[-1]["event_digest"] if rows else None
            if expected_sequence != current: raise RegistryError("STALE_FAMILY_SEQUENCE")
            if expected_previous_digest != previous: raise RegistryError("STALE_PREVIOUS_SNAPSHOT")
            state = self.reduce_rows(rows)
            self._validate_transition(state, event_type, material)
            sequence = current + 1; ed = event_digest(family_id=family_id, family_revision_id=family_revision_id, family_sequence=sequence, event_id=event_id, idempotency_key=idempotency_key, event_type=event_type, semantic_digest=semantic, previous_event_digest=previous)
            self.db.execute("INSERT INTO experiment_events(event_id,idempotency_key,family_id,family_revision_id,family_sequence,event_type,semantic_digest,previous_event_digest,event_digest,record_json) VALUES(?,?,?,?,?,?,?,?,?,?)", (event_id,idempotency_key,family_id,family_revision_id,sequence,event_type,semantic,previous,ed,canonical_json(material)))
            self.db.commit(); return {"duplicate": False, "sequence": sequence, "event_digest": ed}
        except Exception:
            self.db.rollback(); raise

    def _validate_transition(self, state: dict[str, Any], typ: str, p: Mapping[str, Any]) -> None:
        if typ == "FAMILY_CREATED":
            if state["created"]: raise RegistryError("FAMILY_ALREADY_CREATED")
            for k in ("experiment_family_ref","benchmark_ref","metric_id","horizon_id","search_space_ref"): 
                if not isinstance(p.get(k), str) or not p[k]: raise RegistryError("INVALID_FAMILY_PAYLOAD", k)
        elif not state["created"]: raise RegistryError("FAMILY_NOT_CREATED")
        if typ == "TRIAL_REGISTERED":
            if state["frozen"]: raise RegistryError("FAMILY_FROZEN_NO_NEW_TRIAL")
            if not p.get("selection_affecting", True): raise RegistryError("NON_ECONOMIC_REGISTRATION_FORBIDDEN")
            trial = p.get("trial_id"); _sha(p.get("immutable_digest"), "immutable_digest")
            if not isinstance(trial, str) or trial in state["trials"]: raise RegistryError("TRIAL_ID_COLLISION")
        elif typ == "SELECTION_RULE_REGISTERED":
            if state["frozen"] or state["selection_rule"]: raise RegistryError("SELECTION_RULE_IMMUTABLE")
            if not isinstance(p.get("selection_rule_ref"), str) or not p["selection_rule_ref"]: raise RegistryError("INVALID_SELECTION_RULE")
        elif typ == "FAMILY_FROZEN":
            if state["frozen"] or not state["trials"] or not state["selection_rule"]: raise RegistryError("FREEZE_PRECONDITION_FAILED")
            expected = dict(sorted((p.get("expected_trial_digests") or {}).items()))
            if expected != dict(sorted((k, v["immutable_digest"]) for k,v in state["trials"].items() if v["selection_affecting"])): raise RegistryError("EXPECTED_MANIFEST_MISMATCH")
            _sha(p.get("registered_family_digest"), "registered_family_digest")
        elif typ == "TRIAL_STARTED":
            if p.get("trial_id") not in state["trials"] or state["trials"][p["trial_id"]]["status"] != "REGISTERED": raise RegistryError("TRIAL_NOT_REGISTERED")
        elif typ == "TRIAL_TERMINATED":
            if p.get("trial_id") not in state["trials"] or p.get("status") not in TERMINAL: raise RegistryError("INVALID_TERMINATION")
            _sha(p.get("configuration_digest"), "configuration_digest")
        elif typ == "RERUN_REGISTERED":
            original = p.get("rerun_of")
            if original not in state["trials"] or p.get("selection_affecting") is not False or p.get("immutable_digest") != state["trials"][original]["immutable_digest"]: raise RegistryError("MISLABELED_RERUN_REJECT")
        elif typ == "CANDIDATE_FROZEN":
            if not state["frozen"] or any(v["selection_affecting"] and v["status"] not in TERMINAL for v in state["trials"].values()): raise RegistryError("TRIAL_HISTORY_NOT_TERMINAL")
        elif typ == "TRIAL_SELECTED":
            trial = p.get("trial_id")
            if not state["candidate_frozen"] or trial not in state["trials"] or state["trials"][trial]["status"] not in TERMINAL: raise RegistryError("SELECTION_PRECONDITION_FAILED")

    @staticmethod
    def reduce_rows(rows: list[sqlite3.Row]) -> dict[str, Any]:
        state = {"created":False,"family":{},"trials":{},"selection_rule":None,"frozen":False,"candidate_frozen":False,"selected":None}
        for row in rows:
            p=json.loads(row["record_json"]); typ=row["event_type"]
            if typ == "FAMILY_CREATED": state["created"]=True; state["family"]=p
            elif typ == "TRIAL_REGISTERED": state["trials"][p["trial_id"]]={"immutable_digest":p["immutable_digest"],"selection_affecting":True,"status":"REGISTERED","configuration_digest":None}
            elif typ == "SELECTION_RULE_REGISTERED": state["selection_rule"]=p["selection_rule_ref"]
            elif typ == "FAMILY_FROZEN": state["frozen"]=True; state["manifest"]=p["expected_trial_digests"]; state["registered_family_digest"]=p["registered_family_digest"]
            elif typ == "TRIAL_STARTED": state["trials"][p["trial_id"]]["status"]="STARTED"
            elif typ == "TRIAL_TERMINATED": state["trials"][p["trial_id"]].update(status=p["status"], configuration_digest=p["configuration_digest"])
            elif typ == "RERUN_REGISTERED": state["trials"][p["trial_id"]]={"immutable_digest":p["immutable_digest"],"selection_affecting":False,"status":"RERUN","rerun_of":p["rerun_of"],"configuration_digest":None}
            elif typ == "CANDIDATE_FROZEN": state["candidate_frozen"]=True
            elif typ == "TRIAL_SELECTED": state["selected"]=p["trial_id"]
        return state

    def read_family_event_stream(self, family_id: str, family_revision_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self._rows(family_id, family_revision_id)]
    def verify_event_chain(self, family_id: str, family_revision_id: str) -> bool:
        previous=None
        for index,row in enumerate(self._rows(family_id,family_revision_id),1):
            if row["family_sequence"] != index or row["previous_event_digest"] != previous or semantic_digest(row["event_type"],json.loads(row["record_json"])) != row["semantic_digest"]: raise RegistryError("EVENT_CHAIN_INVALID")
            actual=event_digest(family_id=family_id,family_revision_id=family_revision_id,family_sequence=index,event_id=row["event_id"],idempotency_key=row["idempotency_key"],event_type=row["event_type"],semantic_digest=row["semantic_digest"],previous_event_digest=previous)
            if actual != row["event_digest"]: raise RegistryError("EVENT_CHAIN_INVALID")
            previous=actual
        return True
    def reduce_family_snapshot(self, family_id: str, family_revision_id: str) -> dict[str, Any]:
        rows=self._rows(family_id,family_revision_id); state=self.reduce_rows(rows); self.verify_event_chain(family_id,family_revision_id)
        trials=[{"trial_id":k,"immutable_digest":v["immutable_digest"],"status":v["status"],"selection_affecting":v["selection_affecting"],"rerun_of":v.get("rerun_of"),"configuration_digest":v.get("configuration_digest")} for k,v in sorted(state["trials"].items())]
        economic=[v for v in state["trials"].values() if v["selection_affecting"]]
        complete=bool(state["frozen"]) and len(economic)==len(state.get("manifest",{})) and all(v["status"] in TERMINAL for v in economic)
        out={"schema":"StrategyExperimentFamilySnapshot/v1","family_id":family_id,"family_revision_id":family_revision_id,"registered_family_digest":state.get("registered_family_digest"),"trials":trials,"economic_trial_count":len(economic),"rerun_count":len(trials)-len(economic),"status_counts":dict(sorted(Counter(v["status"] for v in state["trials"].values()).items())),"selected_trial_id":state["selected"],"completeness_state":"COMPLETE" if complete else "INCOMPLETE_EXPECTED_TRIALS","ledger_head_digest":rows[-1]["event_digest"] if rows else None}
        out["family_snapshot_digest"] = digest(out); return out

def open_store(path: str | Path = ":memory:") -> Registry:
    return Registry(sqlite3.connect(str(path)))
