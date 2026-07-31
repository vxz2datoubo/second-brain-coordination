# D2 Participant Interface - Frozen Contract
# Reconstructed from D2-INTERFACE-SNAPSHOT.yaml by E23 Gate B R8
# Original commit: d6f9e2e4d38861e91353be177c9ceacedde6d7ee
# Frozen at: 2026-07-30T02:33:00+08:00

D2_PARTICIPANT_FAMILIES = [
    "retail",
    "institutional_quant",
    "active_capital",
    "policy_industrial_foreign_aggregate"
]

D2_PARTICIPANT_SUBTYPES = [
    "retail_liquidity_taker",
    "retail_anchored_holder",
    "systematic_rebalancer",
    "long_horizon_fund",
    "event_driven_active",
    "short_horizon_momentum",
    "policy_aggregate",
    "industrial_aggregate",
    "foreign_aggregate"
]

D2_SUBTYPE_FAMILY_MAP = {
    "retail_liquidity_taker": "retail",
    "retail_anchored_holder": "retail",
    "systematic_rebalancer": "institutional_quant",
    "long_horizon_fund": "institutional_quant",
    "event_driven_active": "active_capital",
    "short_horizon_momentum": "active_capital",
    "policy_aggregate": "policy_industrial_foreign_aggregate",
    "industrial_aggregate": "policy_industrial_foreign_aggregate",
    "foreign_aggregate": "policy_industrial_foreign_aggregate"
}

D2_FAMILIES = set(D2_PARTICIPANT_FAMILIES)
D2_SUBTYPE_SET = set(D2_PARTICIPANT_SUBTYPES)
