"""Independent accounting checks for public immutable D2 episode records.

The oracle intentionally does not call D2's reducer, verifier, hash helpers,
or total-system helpers. Stored D2 hashes are evidence to compare, never facts
to trust.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from evaluation_v2_contract import OracleReport, canonical_sha256, public_value


def _inventory_quantity(inventory: object) -> int | None:
    lots = getattr(inventory, "lots", None)
    if type(lots) is not tuple:
        return None
    total = 0
    for lot in lots:
        quantity = getattr(lot, "quantity", None)
        if type(quantity) is not int or quantity < 0:
            return None
        total += quantity
    return total


def independent_projection(episode: object) -> dict[str, Any]:
    """Project semantic facts, explicitly excluding stored D2 hash fields."""
    initial_agents = getattr(episode, "initial_agents", ())
    current_agents = getattr(episode, "current_agents", ())
    actions = getattr(episode, "action_registry", ())
    events = getattr(episode, "event_dag", ())
    flows = getattr(episode, "external_liquidity_flows", ())
    return {
        "initial": [(getattr(agent, "agent_id", None), _inventory_quantity(getattr(agent, "inventory", None))) for agent in initial_agents],
        "current": [(getattr(agent, "agent_id", None), _inventory_quantity(getattr(agent, "inventory", None))) for agent in current_agents],
        "actions": [{
            "action_id": getattr(action, "action_id", None), "agent_id": getattr(action, "agent_id", None),
            "arrival_sequence": getattr(action, "arrival_sequence", None),
            "label": getattr(getattr(action, "label", None), "value", getattr(action, "label", None)),
            "conflict_key": getattr(action, "conflict_key", None),
            "transition": getattr(getattr(action, "conflict_transition", None), "value", getattr(action, "conflict_transition", None)),
            "liquidity": getattr(getattr(action, "liquidity_mode", None), "value", getattr(action, "liquidity_mode", None)),
            "counterparty": getattr(action, "counterparty_agent_id", None),
            "peer_transfer_id": getattr(action, "peer_transfer_id", None),
            "parents": tuple(getattr(action, "causal_parent_event_ids", ())),
            "order": None if getattr(action, "order", None) is None else {
                "order_id": getattr(action.order, "order_id", None),
                "side": getattr(getattr(action.order, "side", None), "value", getattr(action.order, "side", None)),
                "quantity": getattr(action.order, "quantity", None),
            },
        } for action in actions],
        "events": [{
            "event_id": getattr(event, "event_id", None), "ordinal": getattr(event, "ordinal", None),
            "agent_id": getattr(event, "agent_id", None), "action_id": getattr(event, "action_id", None),
            "accepted": getattr(event, "accepted", None), "status": getattr(event, "outcome_status", None),
            "filled_quantity": getattr(event, "filled_quantity", None),
            "reasons": tuple(getattr(event, "rejected_reason_codes", ())),
            "parents": tuple(getattr(event, "causal_parent_event_ids", ())),
            "liquidity": getattr(getattr(event, "liquidity_mode", None), "value", getattr(event, "liquidity_mode", None)),
            "transition": getattr(getattr(event, "conflict_transition", None), "value", getattr(event, "conflict_transition", None)),
            "counterparty": getattr(event, "counterparty_agent_id", None), "peer_transfer_id": getattr(event, "peer_transfer_id", None),
            "step_index": getattr(event, "step_index", None),
        } for event in events],
        "flows": [{
            "flow_id": getattr(flow, "flow_id", None), "ledger_event_id": getattr(flow, "ledger_event_id", None),
            "agent_id": getattr(flow, "agent_id", None), "agent_delta": getattr(flow, "agent_inventory_delta", None),
            "external_delta": getattr(flow, "external_inventory_delta", None),
        } for flow in flows],
        "boundaries": [(getattr(item, "step_index", None), tuple(getattr(item, "action_ids", ()))) for item in getattr(episode, "step_boundaries", ())],
    }


def independent_digest(episode: object) -> str:
    return canonical_sha256(independent_projection(episode))


def evaluate_episode(episode: object) -> OracleReport:
    """Reconstruct public ledger/accounting invariants without production helpers."""
    reasons: list[str] = []
    checked = [
        "ORACLE-IDENTITY", "ORACLE-ACTION-EVENT-BINDING", "ORACLE-ACTION-EVENT-COVERAGE",
        "ORACLE-ARRIVAL-SEQUENCE-ORDER", "ORACLE-CAUSAL-DAG",
        "ORACLE-CONFLICT-OWNERSHIP", "ORACLE-PEER-CONSERVATION", "ORACLE-EXTERNAL-FLOW",
        "ORACLE-INVENTORY-DELTA", "ORACLE-INDEPENDENT-DIGEST",
    ]
    initial_agents = getattr(episode, "initial_agents", None)
    current_agents = getattr(episode, "current_agents", None)
    actions = getattr(episode, "action_registry", None)
    events = getattr(episode, "event_dag", None)
    flows = getattr(episode, "external_liquidity_flows", None)
    if not all(type(item) is tuple for item in (initial_agents, current_agents, actions, events, flows)):
        return OracleReport(False, ("ORACLE_INVALID_EPISODE_COLLECTION",), "", tuple(checked))

    initial_by_id = {getattr(agent, "agent_id", None): _inventory_quantity(getattr(agent, "inventory", None)) for agent in initial_agents}
    final_by_id = {getattr(agent, "agent_id", None): _inventory_quantity(getattr(agent, "inventory", None)) for agent in current_agents}
    if None in initial_by_id or None in final_by_id or None in initial_by_id.values() or None in final_by_id.values():
        reasons.append("ORACLE_INVALID_AGENT_INVENTORY")
    if len(initial_by_id) != len(initial_agents) or set(initial_by_id) != set(final_by_id):
        reasons.append("ORACLE_AGENT_IDENTITY_MISMATCH")

    action_by_id = {getattr(action, "action_id", None): action for action in actions}
    if None in action_by_id or len(action_by_id) != len(actions):
        reasons.append("ORACLE_DUPLICATE_OR_INVALID_ACTION_ID")
    event_ids = [getattr(event, "event_id", None) for event in events]
    if None in event_ids or len(set(event_ids)) != len(event_ids):
        reasons.append("ORACLE_DUPLICATE_OR_INVALID_EVENT_ID")
    event_action_ids = [getattr(event, "action_id", None) for event in events]
    if len(event_action_ids) != len(actions) or set(event_action_ids) != set(action_by_id):
        reasons.append("ORACLE_ACTION_EVENT_COVERAGE_MISMATCH")
    boundaries = getattr(episode, "step_boundaries", ())
    if type(boundaries) is not tuple:
        reasons.append("ORACLE_INVALID_STEP_BOUNDARIES")
    else:
        for boundary in boundaries:
            boundary_ids = tuple(getattr(boundary, "action_ids", ()))
            if any(action_id not in action_by_id for action_id in boundary_ids):
                reasons.append("ORACLE_BOUNDARY_UNKNOWN_ACTION")
                continue
            expected_ids = tuple(sorted(boundary_ids, key=lambda action_id: getattr(action_by_id[action_id], "arrival_sequence", None)))
            actual_ids = tuple(
                getattr(event, "action_id", None)
                for event in events
                if getattr(event, "step_index", None) == getattr(boundary, "step_index", None)
            )
            if actual_ids != expected_ids:
                reasons.append("ORACLE_ARRIVAL_SEQUENCE_ORDER")

    prior_event_ids: set[str] = set()
    claimed: dict[str, str] = {}
    signed_delta: dict[str, int] = defaultdict(int)
    peer_events: dict[str, list[tuple[object, object, int]]] = defaultdict(list)
    expected_external: dict[str, int] = {}
    flow_by_event: dict[str, list[object]] = defaultdict(list)
    for flow in flows:
        flow_by_event[getattr(flow, "ledger_event_id", None)].append(flow)

    for event in events:
        action = action_by_id.get(getattr(event, "action_id", None))
        if action is None:
            reasons.append("ORACLE_EVENT_ACTION_MISSING")
            continue
        agent_id = getattr(event, "agent_id", None)
        if agent_id != getattr(action, "agent_id", None) or agent_id not in initial_by_id:
            reasons.append("ORACLE_EVENT_AGENT_BINDING_MISMATCH")
        parents = tuple(getattr(event, "causal_parent_event_ids", ()))
        if getattr(event, "accepted", None) and any(parent not in prior_event_ids for parent in parents):
            reasons.append("ORACLE_FORWARD_OR_CYCLIC_CAUSAL_PARENT")
        prior_event_ids.add(getattr(event, "event_id", None))
        filled = getattr(event, "filled_quantity", None)
        if type(filled) is not int or filled < 0:
            reasons.append("ORACLE_INVALID_FILLED_QUANTITY")
            continue
        accepted = getattr(event, "accepted", None)
        order = getattr(action, "order", None)
        if accepted and order is None:
            reasons.append("ORACLE_ACCEPTED_EVENT_WITHOUT_ORDER")
            continue
        signed = 0
        if accepted and order is not None:
            side = getattr(getattr(order, "side", None), "value", getattr(order, "side", None))
            if side == "BUY":
                signed = filled
            elif side == "SELL":
                signed = -filled
            else:
                reasons.append("ORACLE_UNKNOWN_ORDER_SIDE")
            signed_delta[agent_id] += signed
        elif filled != 0:
            reasons.append("ORACLE_REJECTED_EVENT_WITH_FILL")

        conflict_key = getattr(action, "conflict_key", None)
        transition = getattr(getattr(action, "conflict_transition", None), "value", getattr(action, "conflict_transition", None))
        if accepted and conflict_key:
            if transition == "claim":
                if conflict_key in claimed:
                    reasons.append("ORACLE_CONFLICT_CLAIM_BYPASS")
                else:
                    claimed[conflict_key] = agent_id
            elif transition in ("release", "expire"):
                if claimed.get(conflict_key) != agent_id:
                    reasons.append("ORACLE_CONFLICT_RELEASE_OWNERSHIP_BYPASS")
                else:
                    del claimed[conflict_key]

        liquidity = getattr(getattr(action, "liquidity_mode", None), "value", getattr(action, "liquidity_mode", None))
        event_id = getattr(event, "event_id", None)
        if accepted and filled and liquidity == "external_synthetic_liquidity":
            expected_external[event_id] = signed
        if liquidity == "peer_to_peer_transfer":
            transfer_id = getattr(action, "peer_transfer_id", None)
            if not transfer_id:
                reasons.append("ORACLE_PEER_TRANSFER_ID_MISSING")
            else:
                peer_events[transfer_id].append((event, action, signed))

    for event_id, signed in expected_external.items():
        matching = flow_by_event.get(event_id, [])
        if len(matching) != 1:
            reasons.append("ORACLE_EXTERNAL_FLOW_MISSING_OR_DUPLICATE")
            continue
        flow = matching[0]
        if getattr(flow, "agent_inventory_delta", None) != signed or getattr(flow, "external_inventory_delta", None) != -signed:
            reasons.append("ORACLE_EXTERNAL_FLOW_OFFSET_MISMATCH")
    if any(event_id not in expected_external for event_id in flow_by_event):
        reasons.append("ORACLE_UNEXPLAINED_EXTERNAL_FLOW")

    for transfer_id, legs in peer_events.items():
        accepted_legs = [item for item in legs if getattr(item[0], "accepted", None)]
        if accepted_legs:
            if len(legs) != 2 or len(accepted_legs) != 2:
                reasons.append("ORACLE_PARTIAL_PEER_COMMIT")
            elif sum(item[2] for item in accepted_legs) != 0:
                reasons.append("ORACLE_PEER_DELTA_NOT_CONSERVED")
        for event, _action, _signed in legs:
            if flow_by_event.get(getattr(event, "event_id", None)):
                reasons.append("ORACLE_PEER_HAS_EXTERNAL_FLOW")

    for agent_id, initial_quantity in initial_by_id.items():
        final_quantity = final_by_id.get(agent_id)
        if initial_quantity is None or final_quantity is None:
            continue
        if final_quantity - initial_quantity != signed_delta.get(agent_id, 0):
            reasons.append("ORACLE_INVENTORY_DELTA_MISMATCH")

    digest = independent_digest(episode)
    return OracleReport(not reasons, tuple(sorted(set(reasons))), digest, tuple(checked))


def state_hash_binding_oracle(episode: object, expected_state_hash: str) -> OracleReport:
    """Check one declared stored-hash binding; this is not a generic digest gate."""
    actual = getattr(episode, "state_hash", None)
    valid = type(expected_state_hash) is str and actual == expected_state_hash
    return OracleReport(
        valid,
        () if valid else ("ORACLE_STORED_HASH_BINDING",),
        canonical_sha256({"expected_state_hash": expected_state_hash, "actual_state_hash": actual}),
        ("ORACLE_STORED_HASH_BINDING",),
    )
