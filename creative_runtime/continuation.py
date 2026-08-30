"""One owner for migrated-session continuation and slots.

The legacy file is read once as immutable provenance.  Every later operation
rechecks its bytes and writes only the v2 envelope under ``saves/``.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping
from .contracts import StoryState, canonical_json
from .ledger import CreativeLedger, LedgerViolation, apply_state_patch

SCHEMA = "CreativeSession/v2-continuation"

def _sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def _source(workspace: Path) -> Path: return workspace / "session.json"
def _default(workspace: Path) -> Path: return workspace / "saves" / "default.json"
def _slot(workspace: Path, name: str) -> Path:
    if not name or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in name): raise LedgerViolation("Unsafe save slot")
    return workspace / "saves" / "slots" / f"{name}.json"

def _state(records: list[Mapping[str, Any]], actions: list[str]) -> StoryState:
    ledger=CreativeLedger.from_records(records); state=ledger.replay()
    rules={
      ("arrival","listen"):{"beat_id":"echo","reveal_facts":["a witness is inside"],"risk_delta":1},
      ("arrival","approach"):{"beat_id":"threshold","relationship_delta":{"mira":1},"flags":{"arrival":"announced"}},
      ("arrival","leave"):{"beat_id":"courtyard","risk_delta":-1,"flags":{"arrival":"deferred"}},
      ("echo","approach"):{"beat_id":"threshold","relationship_delta":{"mira":1}},
      ("echo","leave"):{"beat_id":"courtyard","flags":{"clue":"recorded"}},
      ("threshold","listen"):{"beat_id":"resolution","relationship_delta":{"mira":1},"risk_delta":-1},
      ("threshold","leave"):{"beat_id":"courtyard","flags":{"meeting":"offered"}},
    }
    for action in actions:
      patch=rules.get((state.beat_id, action))
      if patch is None: raise LedgerViolation("Illegal v2 continuation action")
      state=apply_state_patch(state,patch)
    return state

def _read(workspace: Path, path: Path) -> dict[str, Any]:
    if not _source(workspace).is_file(): raise LedgerViolation("Migrated session requires immutable legacy source")
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA: raise LedgerViolation("Unsupported v2 continuation schema")
    receipt=data.get("receipt",{})
    raw=_source(workspace).read_bytes()
    if receipt.get("source_digest") != _sha(raw): raise LedgerViolation("Migration receipt does not bind to immutable legacy source bytes")
    legacy=json.loads(raw.decode("utf-8"))
    if receipt.get("legacy_records") != legacy.get("events"): raise LedgerViolation("Migration receipt records do not bind to immutable legacy source bytes")
    if not isinstance(data.get("actions"),list) or not all(isinstance(x,str) for x in data["actions"]): raise LedgerViolation("Malformed v2 continuation")
    _state(receipt["legacy_records"],data["actions"])
    return data

def migrate(workspace: Path) -> dict[str, Any]:
    target=_default(workspace)
    if target.exists(): return _read(workspace,target)
    raw=_source(workspace).read_bytes(); legacy=json.loads(raw.decode("utf-8"))
    if legacy.get("schema") != "CreativeSession/v1": raise LedgerViolation("Unsupported legacy schema")
    data={"schema":SCHEMA,"receipt":{"source_digest":_sha(raw),"legacy_records":legacy.get("events",[])},"actions":[]}
    _state(data["receipt"]["legacy_records"],[])
    target.parent.mkdir(parents=True,exist_ok=True); target.write_text(canonical_json(data)+"\n",encoding="utf-8")
    if _source(workspace).read_bytes()!=raw: raise LedgerViolation("Legacy source changed during migration")
    return data

def load(workspace: Path, slot: str | None=None) -> tuple[dict[str,Any],StoryState]:
    path=_slot(workspace,slot) if slot else _default(workspace)
    data=_read(workspace,path); return data,_state(data["receipt"]["legacy_records"],data["actions"])

def choose(workspace: Path, action: str) -> StoryState:
    data,state=load(workspace); _state(data["receipt"]["legacy_records"],data["actions"]+[action])
    data["actions"].append(action); _default(workspace).write_text(canonical_json(data)+"\n",encoding="utf-8")
    return _state(data["receipt"]["legacy_records"],data["actions"])

def save_slot(workspace: Path,name:str) -> None:
    data,_=load(workspace); path=_slot(workspace,name); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(canonical_json(data)+"\n",encoding="utf-8")
def restore_slot(workspace: Path,name:str) -> StoryState:
    data,state=load(workspace,name); _default(workspace).write_text(canonical_json(data)+"\n",encoding="utf-8"); return state
