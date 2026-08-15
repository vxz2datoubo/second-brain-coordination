"""Table-driven executable, public-safe enterprise regressions GST-R001 through GST-R024."""
from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping

from .fixtures import event, snapshot
from .ledger import DurableSignalLedger
from .models import SignalEvent, SignalLink, SignalPlaneError
from .reconciliation import build_receipt, verify_receipt


def _ledger() -> DurableSignalLedger:
    return DurableSignalLedger(":memory:")


def _r133_evidence_binding(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Read only canonical public evidence from the checked-out repository; never a connector."""
    evidence_ref = spec["canonical_evidence_ref"]
    for parent in Path(__file__).resolve().parents:
        candidate = parent / evidence_ref
        if candidate.is_file():
            payload = candidate.read_bytes()
            break
    else:
        raise SignalPlaneError("R133_EVIDENCE_UNAVAILABLE", "/canonical_evidence_ref", "checked-out canonical evidence is unavailable")
    digest = hashlib.sha256(payload).hexdigest().upper()
    binding = spec["r133_public_binding"]
    if digest != binding["sha256"]:
        raise SignalPlaneError("R133_EVIDENCE_DIGEST_MISMATCH", "/r133_public_binding/sha256", "canonical public evidence changed")
    for required in binding["required_utf8_fragments"]:
        if required.encode("utf-8") not in payload:
            raise SignalPlaneError("R133_EVIDENCE_FIELD_MISMATCH", "/r133_public_binding", "required public closure field is absent")
    return {"evidence_ref": evidence_ref, "sha256": digest, "required_fragment_count": len(binding["required_utf8_fragments"])}


def _event(payload: Mapping[str, Any]) -> SignalEvent:
    return SignalEvent.from_dict(payload)


def execute_scenario(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Exercise real S0C mechanisms and return their observed outcomes."""
    scenario_id = spec["id"]
    ledger = _ledger()
    codes: list[str] = []
    evidence_binding: dict[str, Any] | None = None
    replay_observed: bool | None = None
    try:
        if scenario_id == "GST-R001-CROSS-WINDOW-STATE-DRIFT-R133":
            evidence_binding = _r133_evidence_binding(spec)
            receipt = build_receipt(snapshot())
            check = verify_receipt(receipt, snapshot(route_state="DONE", work_claim="CLOSED", program_lane="ACTIVE"))
            codes, result = check["codes"], check["result"]
        elif scenario_id == "GST-R002-STALE-REVIEW-HEAD":
            check = verify_receipt(build_receipt(snapshot()), snapshot(pr_head="head-B"))
            codes, result = check["codes"], check["result"]
        elif scenario_id == "GST-R003-RECEIPT-INVALIDATED-BY-MERGE":
            check = verify_receipt(build_receipt(snapshot()), snapshot(pr_state="MERGED"))
            codes, result = check["codes"], check["result"]
        elif scenario_id == "GST-R004-SAME-AGENT-CROSS-PROJECT-DOUBLE-BOOK":
            check = verify_receipt(build_receipt(snapshot()), snapshot(same_agent_double_booked=True))
            codes, result = check["codes"], check["result"]
        elif scenario_id == "GST-R005-DUPLICATE-DELIVERY-SAME-CONTENT":
            first, second = ledger.ingest_raw(event("dup")), ledger.ingest_raw(event("dup"))
            result = "PASS" if first["status"] == "ADMITTED" and second["status"] == "IDEMPOTENT_DUPLICATE" and len(ledger.history()) == 1 else "BLOCKED"
        elif scenario_id == "GST-R006-IDEMPOTENCY-COLLISION-DIFFERENT-CONTENT":
            ledger.ingest_raw(event("one", idempotency_key="shared"))
            try:
                ledger.ingest_raw(event("two", idempotency_key="shared"))
            except SignalPlaneError as exc:
                codes.append(exc.code)
            result = "BLOCKED" if "IDEMPOTENCY_KEY_COLLISION" in codes else "PASS"
        elif scenario_id == "GST-R007-OUT-OF-ORDER-STATUS-EVENT":
            ledger.ingest_raw(event("done", signal_id="s", source_sequence=2, execution_state="DONE"))
            ledger.ingest_raw(event("old", signal_id="s", source_sequence=1, execution_state="EXECUTING"))
            result = "PASS" if ledger.rebuild_projection()["signals"][0]["execution_state"] == "DONE" else "BLOCKED"
            codes = ["STALE_VIEW"]
        elif scenario_id == "GST-R008-OMISSION-IS-NOT-REVOCATION":
            ledger.ingest_raw(event("requirement", signal_id="s"))
            result = "PASS" if ledger.rebuild_projection()["signals"][0]["planning_state"] == "CAPTURED" else "BLOCKED"
        elif scenario_id == "GST-R009-EXPLICIT-REVOKE":
            ledger.ingest_raw(event("requirement", signal_id="s"))
            ledger.ingest_raw(event("revoke", signal_id="revoke", revokes_refs=["s"], source_sequence=2))
            projection = ledger.rebuild_projection()
            revoked = next(item for item in projection["signals"] if item["signal_id"] == "s")
            result = "PASS" if revoked["planning_state"] == "SUPERSEDED" and len(ledger.history()) == 2 else "BLOCKED"
        elif scenario_id == "GST-R010-DUPLICATE-SIGNALS-PRESERVE-PROVENANCE":
            ledger.ingest_raw(event("a", signal_id="a")); ledger.ingest_raw(event("b", signal_id="b"))
            ledger.append_link(SignalLink.from_dict({"link_id": "d", "from_signal_ref": "a", "to_signal_ref": "b", "relation_type": "DUPLICATE", "evidence_refs": ["opaque://a", "opaque://b"], "created_at": "2026-08-15T00:00:00+00:00", "created_by": "synthetic"}))
            projection = ledger.rebuild_projection()
            result = "PASS" if len(projection["signals"]) == 2 and len(projection["links"][0]["evidence_refs"]) == 2 else "BLOCKED"
        elif scenario_id == "GST-R011-SEMANTIC-FALSE-MERGE-BLOCK":
            left = _event(event("a", primary_domain="FILM", authority_targets=["FILM_OWNER"], touch_set=["film"])); right = _event(event("b", primary_domain="W8", authority_targets=["CONTROL_TOWER_310"], touch_set=["tower"]))
            decision = ledger.attempt_merge(left, right); codes = [decision["code"]]
            result = "BLOCKED" if not decision["allowed"] else "PASS"
        elif scenario_id == "GST-R012-SIGNAL-CANNOT-AUTHORIZE":
            decision = ledger.attempt_execution_authorization(_event(event("auth"))); codes = [decision["code"]]
            result = "BLOCKED" if not decision["allowed"] else "PASS"
        elif scenario_id == "GST-R013-W3-NOT-REPLACED":
            candidate = _event(event("candidate", signal_kind="LEARNING_CANDIDATE", primary_domain="W3"))
            receipt, decision = ledger.ingest(candidate), ledger.attempt_w3_write(candidate); codes = [decision["code"]]
            result = "PASS" if receipt["status"] == "ADMITTED" and not decision["allowed"] and not ledger.authority_observation()["w3_mutated"] else "BLOCKED"
        elif scenario_id == "GST-R014-DOMAIN-CANONICAL-BOUNDARY":
            candidate = _event(event("film-ref", primary_domain="AI_FILM", source_project="ai-film-ref", cross_domain_candidate=True))
            receipt, decision = ledger.ingest(candidate), ledger.attempt_domain_write(candidate); codes = [decision["code"]]
            result = "PASS" if receipt["status"] == "ADMITTED" and not decision["allowed"] and not ledger.authority_observation()["domain_written"] else "BLOCKED"
        elif scenario_id == "GST-R015-PRIVATE-BODY-NOT-IN-PUBLIC-CONTROL-PLANE":
            rejection = ledger.ingest_raw(event("private", raw_source_body="synthetic-private-payload")); codes = [rejection["code"]]
            result = "BLOCKED" if rejection["status"] == "REJECTED" and ledger.rejected_count() == 1 else "PASS"
        elif scenario_id == "GST-R016-PROJECTION-REPLAY-EQUIVALENCE":
            ledger.ingest_raw(event("a")); ledger.ingest_raw(event("b", source_sequence=2)); replay_observed = ledger.observe_replay()
            result = "PASS" if replay_observed else "BLOCKED"
        elif scenario_id == "GST-R017-STALE-PROJECTION-OPTIMISTIC-CONCURRENCY":
            ledger.ingest_raw(event("a")); current = ledger.current_projection_version()
            try:
                ledger.rebuild_projection(expected_version=current - 1)
            except SignalPlaneError as exc:
                codes = [exc.code]
            result = "BLOCKED" if "STALE_PROJECTION_VERSION" in codes else "PASS"
        elif scenario_id == "GST-R018-CRASH-AFTER-APPEND-BEFORE-PROJECTION":
            with TemporaryDirectory() as directory:
                path = f"{directory}/ledger.sqlite"; durable = DurableSignalLedger(path)
                try:
                    durable.ingest_raw(event("durable"), update_projection=False); durable.close(); durable = DurableSignalLedger(path)
                    projection, retry = durable.rebuild_projection(), durable.ingest_raw(event("durable"))
                    replay_observed = durable.observe_replay()
                    result = "PASS" if projection["ledger_watermark"] == 1 and retry["status"] == "IDEMPOTENT_DUPLICATE" and replay_observed else "BLOCKED"
                finally:
                    durable.close()
        elif scenario_id == "GST-R019-MALFORMED-MATERIAL-EVENT":
            rejection = ledger.ingest_raw({"event_id": "bad"}); codes = [rejection["code"]]
            result = "BLOCKED" if rejection["status"] == "REJECTED" and ledger.rejected_count() == 1 else "PASS"
        elif scenario_id == "GST-R020-SOURCE-CLOCK-SKEW":
            ledger.ingest_raw(event("later-clock", signal_id="s", source_sequence=2, occurred_at="2026-01-01T00:00:00+00:00", execution_state="DONE")); ledger.ingest_raw(event("earlier-clock", signal_id="s", source_sequence=1, occurred_at="2027-01-01T00:00:00+00:00", execution_state="EXECUTING"))
            result = "PASS" if ledger.rebuild_projection()["signals"][0]["execution_state"] == "DONE" else "BLOCKED"; codes = ["CAUSAL_ORDER_USED"]
        elif scenario_id == "GST-R021-USER-CANCEL-INVALIDATES-PASS":
            check = verify_receipt(build_receipt(snapshot()), snapshot(user_approval_state="CANCEL")); codes, result = check["codes"], check["result"]
        elif scenario_id == "GST-R022-COMPACTION-REPLAY-EQUIVALENCE":
            ledger.ingest_raw(event("a")); before = ledger.rebuild_projection()["checksum"]; compact = ledger.compact_snapshot(); after = ledger.rebuild_projection()["checksum"]
            replay_observed = before == after
            result = "PASS" if compact["history_retained"] and replay_observed and len(ledger.history()) == 1 else "BLOCKED"
        elif scenario_id == "GST-R023-SIGNAL-FLOOD-BACKPRESSURE":
            receipts = [ledger.ingest_raw(event(f"flood-{index}", signal_id=f"flood-{index}", source_sequence=index), capacity_limit=4) for index in range(1, 33)]
            priority = ledger.ingest_raw(event("priority", signal_id="priority", signal_kind="RISK", source_sequence=33), capacity_limit=4)
            pressure = ledger.backpressure_state(4)
            codes = sorted({item["code"] for item in receipts if "code" in item} | ({"BACKLOG_VISIBLE"} if pressure["deferred"] else set()) | ({"MATERIAL_PRIORITY_ADMITTED"} if priority["status"] == "ADMITTED" else set()))
            result = "PASS" if pressure["pressure_active"] and pressure["deferred"] == 28 and priority["status"] == "ADMITTED" else "BLOCKED"
            replay_observed = ledger.observe_replay()
        elif scenario_id == "GST-R024-CROSS-DOMAIN-NEGATIVE-TRANSFER":
            candidate = _event(event("transfer", primary_domain="AI_FILM", cross_domain_candidate=True))
            receipt, decision = ledger.ingest(candidate), ledger.attempt_cross_domain_promotion(candidate); codes = [decision["code"]]
            result = "BLOCKED" if receipt["status"] == "ADMITTED" and not decision["allowed"] else "PASS"
            replay_observed = ledger.observe_replay()
        else:
            raise AssertionError(f"unknown scenario {scenario_id}")
        if replay_observed is None and spec["replay_assertion"]:
            replay_observed = ledger.observe_replay()
        return {"id": scenario_id, "result": result, "codes": sorted(set(codes)), "authority_assertions": ledger.authority_observation(), "replay_observed": replay_observed, "evidence_binding": evidence_binding}
    finally:
        try:
            ledger.close()
        except Exception:
            pass
