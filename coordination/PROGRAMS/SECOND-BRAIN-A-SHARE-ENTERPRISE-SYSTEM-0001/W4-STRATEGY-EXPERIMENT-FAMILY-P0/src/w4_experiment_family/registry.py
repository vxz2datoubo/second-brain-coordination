"""Append-only, offline-only W4 StrategyExperimentFamily registry.

The registry deliberately owns only W4 experiment provenance.  It has no market
data, probability, W7 validation, account, position, order, or trade authority.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

TERMINAL = {"SUCCESS", "FAILURE", "ABORTED", "ERROR"}
STATUS_MAP = {
    "SUCCESS": "SUCCESS", "FAILURE": "FAILURE", "FAILED": "FAILURE",
    "ABORTED": "ABORTED", "REJECTED_BY_PRECHECK": "ABORTED",
    "REJECTED_PRECHECK": "ABORTED", "ERROR": "ERROR",
    "NUMERICAL_ERROR": "ERROR", "DATA_INVALID": "ERROR",
    "REGISTERED_NOT_RUN": "REGISTERED", "REGISTERED": "REGISTERED",
    "RUNNING": "STARTED", "STARTED": "STARTED",
}
EVENTS = {"FAMILY_CREATED", "TRIAL_REGISTERED", "SELECTION_RULE_REGISTERED", "FAMILY_FROZEN", "TRIAL_STARTED", "TRIAL_TERMINATED", "RERUN_REGISTERED", "CANDIDATE_FROZEN", "TRIAL_SELECTED", "LEGACY_INCOMPLETE_REGISTERED"}
AUTHORITY_KEYS = ("w4_strategy_experiment_write_authority", "trial_ledger_authority", "backtest_result_authority", "market_data_truth_authority", "w7_validation_authority", "probability_authority", "risk_authority", "position_authority", "order_authority", "trade_authority")
ROOT = Path(__file__).resolve().parents[2]


class RegistryError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}{': ' + detail if detail else ''}")
        self.code = code


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise RegistryError("INVALID_SHA256", name)
    return value


def semantic_digest(event_type: str, payload: Mapping[str, Any]) -> str:
    return digest({"event_type": event_type, "payload": dict(payload)})


def event_digest(*, family_id: str, family_revision_id: str, family_sequence: int, event_id: str, idempotency_key: str, event_type: str, semantic_digest: str, previous_event_digest: str | None) -> str:
    return digest({"family_id": family_id, "family_revision_id": family_revision_id, "family_sequence": family_sequence, "event_id": event_id, "idempotency_key": idempotency_key, "event_type": event_type, "semantic_digest": semantic_digest, "previous_event_digest": previous_event_digest})


def registered_family_digest_v1(*, experiment_family_ref: str, expected_trial_digests: Mapping[str, str], benchmark_ref: str, metric_id: str, horizon_id: str, search_space_ref: str, selection_rule_ref: str) -> str:
    return digest({"experiment_family_ref": experiment_family_ref, "expected_trial_digests": dict(sorted(expected_trial_digests.items())), "benchmark_ref": benchmark_ref, "metric_id": metric_id, "horizon_id": horizon_id, "search_space_ref": search_space_ref, "selection_rule_ref": selection_rule_ref})


def _schema(name: str) -> dict[str, Any]:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def _validate_schema(value: Any, schema: Mapping[str, Any], path: str = "$") -> None:
    """A deliberately small stdlib-only JSON Schema subset for closed W4 objects."""
    expected = schema.get("type")
    expected_types = expected if isinstance(expected, list) else [expected]
    check = {"object": dict, "array": list, "string": str, "boolean": bool, "integer": int, "null": type(None)}
    if expected and not any((typ == "integer" and isinstance(value, int) and not isinstance(value, bool)) or (typ != "integer" and isinstance(value, check[typ])) for typ in expected_types):
        raise RegistryError("SCHEMA_TYPE_INVALID", path)
    if "enum" in schema and value not in schema["enum"]:
        raise RegistryError("SCHEMA_ENUM_INVALID", path)
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0): raise RegistryError("SCHEMA_MIN_LENGTH", path)
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None: raise RegistryError("SCHEMA_PATTERN_INVALID", path)
    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value: raise RegistryError("SCHEMA_REQUIRED_MISSING", f"{path}.{key}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties: raise RegistryError("SCHEMA_ADDITIONAL_PROPERTY", f"{path}.{key}")
        for key, item in value.items():
            if key in properties: _validate_schema(item, properties[key], f"{path}.{key}")
            elif isinstance(schema.get("additionalProperties"), dict): _validate_schema(item, schema["additionalProperties"], f"{path}.{key}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value): _validate_schema(item, schema["items"], f"{path}[{index}]")


def _authority() -> dict[str, bool]:
    # W4 writer identity is represented by producer, never caller-authority flags.
    return {key: False for key in AUTHORITY_KEYS}


def _canonical_status(spelling: Any) -> str:
    if not isinstance(spelling, str) or spelling not in STATUS_MAP:
        raise RegistryError("INVALID_TRIAL_STATUS")
    return STATUS_MAP[spelling]


def _provenance(trial: Mapping[str, Any]) -> tuple[str, list[str]]:
    fields = ("parameter_manifest_ref", "feature_manifest_ref", "dataset_snapshot_refs", "code_version_refs", "rule_snapshot_refs", "seed_or_randomness_ref", "strategy_definition_ref", "cost_model_ref", "search_space_ref")
    missing = [key for key in fields if not trial.get(key)]
    if trial.get("llm_candidate_can_affect_selection") and not trial.get("prompt_model_temperature_ref"):
        missing.append("prompt_model_temperature_ref")
    declared = trial.get("provenance_state")
    if declared == "INVALID": return "INVALID", sorted(set(missing))
    return ("COMPLETE" if not missing else "INCOMPLETE"), sorted(set(missing))


class Registry:
    def __init__(self, connection: sqlite3.Connection):
        self.db = connection; self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS experiment_events (event_offset INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT NOT NULL UNIQUE,idempotency_key TEXT NOT NULL UNIQUE,family_id TEXT NOT NULL,family_revision_id TEXT NOT NULL,family_sequence INTEGER NOT NULL,event_type TEXT NOT NULL,semantic_digest TEXT NOT NULL,previous_event_digest TEXT,event_digest TEXT NOT NULL UNIQUE,record_json TEXT NOT NULL,UNIQUE(family_id,family_revision_id,family_sequence))")
        self.db.commit()

    def _rows(self, family_id: str, revision: str) -> list[sqlite3.Row]:
        return list(self.db.execute("SELECT * FROM experiment_events WHERE family_id=? AND family_revision_id=? ORDER BY family_sequence", (family_id, revision)))

    def append(self, *, family_id: str, family_revision_id: str, expected_sequence: int, event_id: str, idempotency_key: str, event_type: str, payload: Mapping[str, Any], expected_previous_digest: str | None = None) -> dict[str, Any]:
        if event_type not in EVENTS: raise RegistryError("INVALID_EVENT_TYPE")
        if not all(isinstance(x, str) and x for x in (family_id, family_revision_id, event_id, idempotency_key)): raise RegistryError("EMPTY_IDENTITY")
        material = dict(payload)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            rows = self._rows(family_id, family_revision_id)
            # Normalize/default the caller record before it participates in a digest.
            state = self.reduce_rows(rows); self._validate_transition(state, event_type, material, family_id, family_revision_id)
            semantic = semantic_digest(event_type, material)
            old = self.db.execute("SELECT * FROM experiment_events WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if old:
                if all(old[k] == v for k, v in {"family_id": family_id, "family_revision_id": family_revision_id, "event_id": event_id, "event_type": event_type, "semantic_digest": semantic}.items()): self.db.commit(); return {"duplicate": True, "sequence": old["family_sequence"], "event_digest": old["event_digest"]}
                raise RegistryError("IDEMPOTENCY_KEY_COLLISION")
            if self.db.execute("SELECT event_id FROM experiment_events WHERE event_id=?", (event_id,)).fetchone(): raise RegistryError("EVENT_ID_COLLISION")
            previous = rows[-1]["event_digest"] if rows else None
            if expected_sequence != len(rows): raise RegistryError("STALE_FAMILY_SEQUENCE")
            if expected_previous_digest != previous: raise RegistryError("STALE_PREVIOUS_SNAPSHOT")
            sequence = len(rows) + 1; ed = event_digest(family_id=family_id, family_revision_id=family_revision_id, family_sequence=sequence, event_id=event_id, idempotency_key=idempotency_key, event_type=event_type, semantic_digest=semantic, previous_event_digest=previous)
            self.db.execute("INSERT INTO experiment_events(event_id,idempotency_key,family_id,family_revision_id,family_sequence,event_type,semantic_digest,previous_event_digest,event_digest,record_json) VALUES(?,?,?,?,?,?,?,?,?,?)", (event_id, idempotency_key, family_id, family_revision_id, sequence, event_type, semantic, previous, ed, canonical_json(material)))
            self.db.commit(); return {"duplicate": False, "sequence": sequence, "event_digest": ed}
        except Exception:
            self.db.rollback(); raise

    def _validate_transition(self, state: dict[str, Any], typ: str, p: dict[str, Any], family_id: str, revision: str) -> None:
        if typ == "FAMILY_CREATED":
            if state["created"]: raise RegistryError("FAMILY_ALREADY_CREATED")
            p.setdefault("schema", "StrategyExperimentFamily/v1"); p.setdefault("experiment_family_id", family_id); p.setdefault("family_revision_id", revision); p.setdefault("producer", "W4"); p.setdefault("authority", _authority()); p.setdefault("family_status", "REGISTERED")
            p.setdefault("family_schema_version", "v1"); p.setdefault("created_at", "OFFLINE"); p.setdefault("registered_at", "OFFLINE"); p.setdefault("selection_frozen_at", None); p.setdefault("closed_at", None); p.setdefault("supersedes_revision_id", None); p.setdefault("strategy_definition_refs", []); p.setdefault("feature_definition_refs", []); p.setdefault("theory_or_hypothesis_refs", []); p.setdefault("dataset_manifest_refs", []); p.setdefault("code_manifest_refs", []); p.setdefault("parameter_space_ref", "UNRESOLVED"); p.setdefault("cost_model_ref", "UNRESOLVED"); p.setdefault("rule_snapshot_refs", []); p.setdefault("universe_definition_ref", "UNRESOLVED"); p.setdefault("selection_rule_ref", "UNRESOLVED"); p.setdefault("randomness_policy_ref", "UNRESOLVED"); p.setdefault("trial_manifest_digest", None); p.setdefault("trial_id_set_digest", None); p.setdefault("economic_trial_count", 0); p.setdefault("rerun_count", 0); p.setdefault("family_content_digest", None); p.setdefault("selected_trial_id", None); p.setdefault("selection_rule_digest", None); p.setdefault("selection_frozen_before_lockbox", False)
            if p.get("experiment_family_ref") is None: p["experiment_family_ref"] = f"{family_id}@{revision}"
            _validate_schema(p, _schema("STRATEGY-EXPERIMENT-FAMILY.schema.json"))
        elif not state["created"]: raise RegistryError("FAMILY_NOT_CREATED")
        if typ in {"TRIAL_REGISTERED", "LEGACY_INCOMPLETE_REGISTERED"}:
            if state["frozen"]: raise RegistryError("FAMILY_FROZEN_NO_NEW_TRIAL")
            trial = p.get("trial_id")
            if not isinstance(trial, str) or not trial: raise RegistryError("INVALID_TRIAL_ID")
            if trial in state["trials"]: raise RegistryError("TRIAL_ID_COLLISION")
            p.setdefault("schema", "ExperimentTrialRecord/v1"); p.setdefault("experiment_family_id", family_id); p.setdefault("family_revision_id", revision); p.setdefault("trial_kind", "ECONOMIC" if typ == "TRIAL_REGISTERED" else "LEGACY_INCOMPLETE_PROVENANCE"); p.setdefault("trial_status", "REGISTERED"); p.setdefault("registered_at", "OFFLINE"); p.setdefault("started_at", None); p.setdefault("completed_at", None); p.setdefault("failure_class", None); p.setdefault("failure_evidence_ref", None); p.setdefault("rerun_of_trial_id", None); p.setdefault("prompt_model_temperature_ref", None); p.setdefault("llm_candidate_can_affect_selection", False); p.setdefault("provenance_state", "INCOMPLETE"); p.setdefault("missing_provenance", [])
            p["trial_status"] = _canonical_status(p["trial_status"])
            actual_state, missing = _provenance(p); p["provenance_state"] = actual_state; p["missing_provenance"] = missing
            if typ == "TRIAL_REGISTERED" and p.get("selection_affecting") is not True: raise RegistryError("NON_ECONOMIC_REGISTRATION_FORBIDDEN")
            if typ == "LEGACY_INCOMPLETE_REGISTERED": p["selection_affecting"] = True; p["trial_kind"] = "LEGACY_INCOMPLETE_PROVENANCE"; p["provenance_state"] = "INCOMPLETE"
            _validate_schema(p, _schema("EXPERIMENT-TRIAL-RECORD.schema.json"))
        elif typ == "RERUN_REGISTERED":
            trial = p.get("trial_id"); original = p.get("rerun_of") or p.get("rerun_of_trial_id")
            if trial in state["trials"]: raise RegistryError("TRIAL_ID_COLLISION")
            if original not in state["trials"] or p.get("selection_affecting") is not False or p.get("immutable_digest") != state["trials"][original]["immutable_digest"]: raise RegistryError("MISLABELED_RERUN_REJECT")
        elif typ == "SELECTION_RULE_REGISTERED":
            if state["frozen"] or state["selection_rule"]: raise RegistryError("SELECTION_RULE_IMMUTABLE")
            if not isinstance(p.get("selection_rule_ref"), str) or not p["selection_rule_ref"]: raise RegistryError("INVALID_SELECTION_RULE")
        elif typ == "FAMILY_FROZEN":
            if state["frozen"] or not state["trials"] or not state["selection_rule"]: raise RegistryError("FREEZE_PRECONDITION_FAILED")
            expected = dict(sorted((p.get("expected_trial_digests") or {}).items())); actual = dict(sorted((key, value["immutable_digest"]) for key, value in state["trials"].items() if value["selection_affecting"]))
            if expected != actual: raise RegistryError("EXPECTED_MANIFEST_MISMATCH")
            _sha(p.get("registered_family_digest"), "registered_family_digest")
        elif typ == "TRIAL_STARTED":
            if p.get("trial_id") not in state["trials"] or state["trials"][p["trial_id"]]["status"] != "REGISTERED": raise RegistryError("TRIAL_NOT_REGISTERED")
        elif typ == "TRIAL_TERMINATED":
            trial = p.get("trial_id")
            if trial not in state["trials"]: raise RegistryError("INVALID_TERMINATION")
            if state["trials"][trial]["status"] in TERMINAL: raise RegistryError("TRIAL_ALREADY_TERMINAL")
            spelling = p.get("status"); status = _canonical_status(spelling)
            if status not in TERMINAL: raise RegistryError("INVALID_TERMINATION")
            p["status"] = status
            if spelling == "NUMERICAL_ERROR": p.setdefault("failure_class", "NUMERICAL_ERROR")
            if spelling == "DATA_INVALID": p.setdefault("failure_class", "DATA_INVALID")
            if spelling in {"REJECTED_BY_PRECHECK", "REJECTED_PRECHECK"}: p.setdefault("failure_class", "PRECHECK")
            _sha(p.get("configuration_digest"), "configuration_digest")
        elif typ == "CANDIDATE_FROZEN":
            if not state["frozen"] or any(v["selection_affecting"] and v["status"] not in TERMINAL for v in state["trials"].values()): raise RegistryError("TRIAL_HISTORY_NOT_TERMINAL")
        elif typ == "TRIAL_SELECTED":
            trial = p.get("trial_id")
            if not state["candidate_frozen"] or trial not in state["trials"] or state["trials"][trial]["status"] not in TERMINAL: raise RegistryError("SELECTION_PRECONDITION_FAILED")

    @staticmethod
    def reduce_rows(rows: list[sqlite3.Row]) -> dict[str, Any]:
        state = {"created": False, "family": {}, "trials": {}, "selection_rule": None, "frozen": False, "candidate_frozen": False, "selected": None, "manifest": {}}
        for row in rows:
            p = json.loads(row["record_json"]); typ = row["event_type"]
            if typ == "FAMILY_CREATED": state.update(created=True, family=p)
            elif typ in {"TRIAL_REGISTERED", "LEGACY_INCOMPLETE_REGISTERED"}: state["trials"][p["trial_id"]] = dict(p, status="REGISTERED", selection_affecting=True)
            elif typ == "RERUN_REGISTERED": state["trials"][p["trial_id"]] = {"trial_id": p["trial_id"], "immutable_digest": p["immutable_digest"], "selection_affecting": False, "status": "REGISTERED", "rerun_of": p.get("rerun_of") or p.get("rerun_of_trial_id"), "provenance_state": "COMPLETE"}
            elif typ == "SELECTION_RULE_REGISTERED": state["selection_rule"] = p["selection_rule_ref"]
            elif typ == "FAMILY_FROZEN": state.update(frozen=True, manifest=p["expected_trial_digests"], registered_family_digest=p["registered_family_digest"])
            elif typ == "TRIAL_STARTED": state["trials"][p["trial_id"]]["status"] = "STARTED"
            elif typ == "TRIAL_TERMINATED": state["trials"][p["trial_id"]].update(status=p["status"], configuration_digest=p["configuration_digest"], failure_class=p.get("failure_class"))
            elif typ == "CANDIDATE_FROZEN": state["candidate_frozen"] = True
            elif typ == "TRIAL_SELECTED": state["selected"] = p["trial_id"]
        return state

    def read_family_event_stream(self, family_id: str, family_revision_id: str) -> list[dict[str, Any]]: return [dict(row) for row in self._rows(family_id, family_revision_id)]

    def verify_event_chain(self, family_id: str, family_revision_id: str) -> bool:
        previous = None
        for index, row in enumerate(self._rows(family_id, family_revision_id), 1):
            if row["family_sequence"] != index or row["previous_event_digest"] != previous or semantic_digest(row["event_type"], json.loads(row["record_json"])) != row["semantic_digest"]: raise RegistryError("EVENT_CHAIN_INVALID")
            actual = event_digest(family_id=family_id, family_revision_id=family_revision_id, family_sequence=index, event_id=row["event_id"], idempotency_key=row["idempotency_key"], event_type=row["event_type"], semantic_digest=row["semantic_digest"], previous_event_digest=previous)
            if actual != row["event_digest"]: raise RegistryError("EVENT_CHAIN_INVALID")
            previous = actual
        return True

    def read_experiment_family(self, exact_family_revision: str) -> dict[str, Any]:
        if "@" not in exact_family_revision: raise RegistryError("INVALID_EXACT_FAMILY_REVISION")
        family_id, revision = exact_family_revision.rsplit("@", 1)
        return self.reduce_family_snapshot(family_id, revision)

    def reduce_family_snapshot(self, family_id: str, family_revision_id: str) -> dict[str, Any]:
        rows = self._rows(family_id, family_revision_id); self.verify_event_chain(family_id, family_revision_id); state = self.reduce_rows(rows)
        if not state["created"]: raise RegistryError("FAMILY_NOT_FOUND")
        for row in rows:
            if row["event_type"] == "FAMILY_CREATED": _validate_schema(json.loads(row["record_json"]), _schema("STRATEGY-EXPERIMENT-FAMILY.schema.json"))
            if row["event_type"] in {"TRIAL_REGISTERED", "LEGACY_INCOMPLETE_REGISTERED"}: _validate_schema(json.loads(row["record_json"]), _schema("EXPERIMENT-TRIAL-RECORD.schema.json"))
        trials = [{key: value.get(key) for key in ("trial_id", "immutable_digest", "status", "selection_affecting", "rerun_of", "provenance_state", "missing_provenance", "failure_class", "trial_kind")} for _, value in sorted(state["trials"].items())]
        economic = [value for value in state["trials"].values() if value["selection_affecting"]]
        complete = bool(state["frozen"]) and set(state["manifest"]) == {value["trial_id"] for value in economic} and all(value["status"] in TERMINAL and value.get("provenance_state") == "COMPLETE" for value in economic)
        completeness = "COMPLETE" if complete else ("LEGACY_INCOMPLETE_PROVENANCE" if any(value.get("trial_kind") == "LEGACY_INCOMPLETE_PROVENANCE" for value in economic) else "INCOMPLETE_EXPECTED_TRIALS")
        out = {"schema": "ExperimentFamilySnapshot/v1", "exact_family_revision": f"{family_id}@{family_revision_id}", "family_id": family_id, "family_revision_id": family_revision_id, "source_producer": "W4", "registered_family_digest": state.get("registered_family_digest"), "trials": trials, "economic_trial_count": len(economic), "rerun_count": len(trials) - len(economic), "status_counts": dict(sorted(Counter(value["status"] for value in state["trials"].values()).items())), "selected_trial_id": state["selected"], "selection_rule_ref": state["selection_rule"], "selection_frozen": state["candidate_frozen"], "completeness_state": completeness, "ledger_head_digest": rows[-1]["event_digest"] if rows else None, "authority": _authority()}
        out["snapshot_digest"] = digest(out); _validate_schema(out, _schema("EXPERIMENT-FAMILY-SNAPSHOT.schema.json")); out["family_snapshot_digest"] = out["snapshot_digest"]
        return out


def open_store(path: str | Path = ":memory:") -> Registry: return Registry(sqlite3.connect(str(path)))
