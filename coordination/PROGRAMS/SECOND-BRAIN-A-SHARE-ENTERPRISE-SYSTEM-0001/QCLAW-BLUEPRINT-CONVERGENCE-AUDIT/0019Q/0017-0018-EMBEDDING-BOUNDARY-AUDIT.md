# 0017-0018 EMBEDDING BOUNDARY AUDIT — R1 CORRECTED

**Task ID:** QCLAW-W1-ENTERPRISE-BLUEPRINT-INDEPENDENT-AUDIT-0019Q-R1
**Scope:** 0017 (BAR_ONLY Reference Zone), 0018 (Edge Estimation Subsystem)
**Audit Date:** 2026-07-24T00:35+08:00 (R1 correction of 2026-07-23 original)
**Auditor:** QCLAW Independent Audit Agent
**Safety Classification:** PUBLIC_SAFE / CANDIDATE_ONLY / NO_TRADE
**Core Question:** Do 0017 and 0018 remain embedded capabilities within their parent modules, or have they drifted toward parallel platforms?

---

## R1 CORRECTION NOTICE

> **Original (2026-07-23) INCORRECTLY attributed L2 order-book data and L3 tick
> data as 0017 BAR_ONLY dependencies.** The selected 0017 slice depends only on
> point-in-time bar (OHLCV) data. L2 order-book, L3 tick-by-tick, participant
> identity, and hidden-intent data are NOT 0017 BAR_ONLY dependencies.
> Any mention of L2/L3 in the original audit is hereby corrected: L2/L3 topics
> are preserved below ONLY as future non-BAR_ONLY UNKNOWN items, not as 0017
> dependencies.

---

## 1. EXECUTIVE SUMMARY

**Both 0017 and 0018 pass the embedded-capability audit.** Neither has drifted into parallel-platform territory. Both maintain correct `owns_parallel_runtime: false`, and both operate within their parent modules' boundaries. However, each has a boundary-risk surface that warrants monitoring as development continues.

| Capability | Parent Modules | Embedded? | Boundary Risks Identified | Verdict |
|------------|---------------|-----------|--------------------------|---------|
| 0017 — BAR_ONLY Reference Zone | W4, W7 | ✅ Yes | 1 (probability drift) | PASS with monitoring |
| 0018 — Edge Estimation | W7, W9, W11 | ✅ Yes | 2 (allocation/probability drift) | PASS with monitoring |

---

## 2. 0017 — BAR_ONLY REFERENCE ZONE AUDIT

### 2.1 Architecture Embedding

0017 is embedded within:
- **W4** (Back Testing Engine) — provides historical reference context for back-sweep validation.
- **W7** (Risk Decision Engine) — provides reference-zone context for final-veto decisions.

**Ownership:** W4 and W7 own 0017's lifecycle. No independent runtime exists.

### 2.2 BAR_ONLY Dependency Declaration (R1 CORRECTED)

**0017 BAR_ONLY depends ONLY on:**
- Point-in-time bar data (OHLCV at bar resolution)
- No L2 order-book data
- No L3 tick-by-tick data
- No participant identity data
- No hidden-intent data
- No order-flow data

Any future extension beyond bar-data scope is a non-BAR_ONLY slice and would
require a separate freeze gate.

### 2.3 Boundary Assessment

| Boundary Rule | Compliance | Evidence |
|--------------|------------|---------|
| `owns_parallel_runtime: false` | ✅ PASS | No independent runtime or scheduler |
| BAR_ONLY: depends only on PIT bar data | ✅ PASS | No L2/L3/identity/order-flow dependency |
| `may_write: false` (read-only reference zone) | ✅ PASS | Reference zone is read-only |
| `may_not_write` to order flow | ✅ PASS | Correctly excluded from order pipeline |
| No W14 or hidden platform | ✅ PASS | No independent coordinator, scheduler, or state machine detected |

### 2.4 Boundary Risk: Probability Drift via PostSweepStabilizationAssessment

**Risk Surface Identified:**
The `PostSweepStabilizationAssessment` capability within 0017's NEXT-SLICE raises a boundary concern. Post-sweep stabilization inherently involves assessing whether observed outcomes converge to expected distributions — which is a probability estimation function.

**The "Fresh vs Seasoned Inventory" Language Test:**
0017's NEXT-SLICE documentation uses language around "Fresh vs Seasoned inventory" classification within the reference zone. This is a boundary test: if 0017 begins producing **inventory-conditioned probability estimates** (e.g., "fresh inventory has X% higher adverse outcome rate"), it has crossed into W12 (Probability Engine) territory.

**Current Assessment:** 0017 currently classifies inventory states for reference purposes (labeling, not estimating). The distinction is:
- ✅ **Reference labeling:** "This inventory segment is classified as Fresh" (0017 territory)
- ❌ **Probability estimation:** "Fresh inventory has a 3.2% higher adverse selection probability" (W12 territory)

**Monitoring Trigger:** If 0017's NEXT-SLICE introduces any numeric probability output or distributional comparison, it has crossed the boundary.

### 2.5 Future Non-BAR_ONLY UNKNOWN: Signal-to-Noise Beyond Bar Resolution

**Preserved from original audit as UNKNOWN, NOT as 0017 dependency:**

The 0017 hypothesis tests reference-zone breach/reclaim using PIT bar data.
It is UNKNOWN whether BAR_ONLY data has sufficient signal-to-noise ratio to
distinguish genuine breach-driven reclaim from random bar-level fluctuation.
Higher-resolution data (L2 order-book, L3 tick) would improve signal-to-noise
but is NOT part of the current BAR_ONLY slice. This is a data-adequacy risk,
not a scope violation: 0017 may terminate with NEGATIVE_RESULT due to data
inadequacy, not hypothesis falsity.

**This L2/L3 topic is registered as a future non-BAR_ONLY UNKNOWN (QU-004 in
MISSING-EVIDENCE-AND-UNKNOWN-REGISTRY.yaml). It is NOT a 0017 dependency.**

---

## 3. 0018 — EDGE ESTIMATION SUBSYSTEM AUDIT

### 3.1 Architecture Embedding

0018 is embedded within:
- **W7** (Risk Decision Engine) — provides edge estimates for final-veto calibration.
- **W9** (Order Generator) — provides edge estimates for order-sizing decisions.
- **W11** (Capital Allocator) — provides edge estimates for allocation proportioning.

**Ownership:** W7, W9, and W11 own 0018's lifecycle collectively. No independent runtime exists.

### 3.2 Boundary Assessment

| Boundary Rule | Compliance | Evidence |
|--------------|------------|---------|
| `owns_parallel_runtime: false` | ✅ PASS | No independent runtime or scheduler |
| `may_write` boundaries correct per parent | ✅ PASS | Write scope limited to edge estimate outputs within parent modules |
| `may_not_write` to probability or allocation directly | ✅ PASS | Outputs are estimates, not final decisions |
| No W14 or hidden platform | ✅ PASS | No independent coordinator detected |

### 3.3 Boundary Risk A: Allocation Drift via CapitalBufferAndRuinAssessment

**Risk Surface Identified:**
`CapitalBufferAndRuinAssessment` is dangerously close to W11 (Capital Allocator) territory. The boundary question: is 0018 *estimating* the buffer needed, or *allocating* it?

- ✅ **Operational calibration (0018 territory):** "The edge estimate for this allocation suggests a buffer of X bps given current volatility regime"
- ❌ **Allocation decision (W11 territory):** "Allocate 3.2% of capital to this candidate with a 1.5% ruin threshold"

**Current Assessment:** 0018 stays on the correct side. The `CapitalBufferAndRuinAssessment` produces an operational calibration parameter, not an allocation decision. W11 consumes this estimate and makes the allocation — the decision remains with W11.

### 3.4 Boundary Risk B: Probability Drift via HouseEdgeInspiredNetEdgeEstimate

**Risk Surface Identified:**
`HouseEdgeInspiredNetEdgeEstimate` is semantically adjacent to W12 (Probability Engine) territory. The name itself ("HouseEdge") invokes a probabilistic concept.

**Boundary Analysis — The Semantic Distinction:**
The boundary between 0018 and W12 is **semantic**, not functional:
- **0018 Edge Estimates:** Operational calibration parameters derived from microstructure analysis. These are "edges" in the trading sense — small informational advantages that can be acted upon.
- **W12 Probability Estimates:** Statistical probability distributions derived from formal models. These are "probabilities" in the mathematical sense — likelihoods backed by a formal model.

`HouseEdgeInspiredNetEdgeEstimate` is on the correct side: it estimates an operational edge parameter inspired by house-edge concepts, not a formal probability distribution.

**Monitoring Trigger:** If 0018 begins producing confidence intervals, p-values, or distributional forecasts, it has crossed into W12 territory.

---

## 4. NO W14 OR HIDDEN PLATFORM DETECTED

Audit confirms no independent coordinator, scheduler, state machine, or runtime exists that would constitute a W14 module or hidden parallel platform.

**Checks performed:**
- No independent runtime registration found for 0017 or 0018.
- No scheduler or cron-like trigger ownership.
- No independent state persistence beyond parent modules.
- No message bus or event channel ownership.
- No coordinator module mediating between 0017 and 0018.

---

## 5. OVERALL VERDICT

| Dimension | 0017 | 0018 |
|-----------|------|------|
| Embedded in parent modules | ✅ | ✅ |
| Correct write boundaries | ✅ | ✅ |
| Scope exclusion correct | ✅ (order flow + L2/L3 excluded) | ✅ (allocation/probability excluded) |
| Boundary risk — probability drift | ⚠️ MONITOR | ⚠️ MONITOR |
| Boundary risk — allocation drift | N/A | ⚠️ MONITOR |
| Parallel runtime risk | ✅ None | ✅ None |
| W14/hidden platform risk | ✅ None | ✅ None |

**Final Verdict: PASS with monitoring conditions.**

Both capabilities remain correctly embedded. Neither constitutes a parallel platform. The identified boundary risks are forward-looking and should be reviewed at each NEXT-SLICE boundary.

---

## 6. MONITORING RECOMMENDATIONS

1. **Watch 0017 NEXT-SLICE:** If `PostSweepStabilizationAssessment` introduces numeric probability outputs, flag as boundary breach into W12 territory.
2. **Watch 0018 `CapitalBufferAndRuinAssessment`:** If it begins making allocation decisions rather than producing calibration estimates, flag as boundary breach into W11 territory.
3. **Watch 0018 `HouseEdgeInspiredNetEdgeEstimate`:** If it begins producing statistical distributions or confidence intervals, flag as boundary breach into W12 territory.
4. **Watch 0017 data scope:** If any L2/L3/identity/order-flow data enters 0017's dependency list, flag as scope creep beyond BAR_ONLY.
5. **Review at each architecture iteration** (PR merge events) to confirm `owns_parallel_runtime` remains false.

### R1 CORRECTION LOG

| Correction | Original (pre-R1) | R1 Corrected |
|---|---|---|
| 0017 data dependency | Claimed "relies on L2 order book data" and "without L3 tick data" | Depends ONLY on PIT bar (OHLCV) data |
| L2 noise analysis | Presented as 0017 dependency concern | Registered as future non-BAR_ONLY UNKNOWN (QU-004) |
| Scope boundary | "excludes order flow" | "excludes order flow, L2, L3, participant identity, hidden-intent" |
