# E54 Discovery Report

## S2: missing route-level TaskImpactForecast

**Verified fact:** canonical `main` contained the active route and full Issue
#170 requirements, but no task-specific E54 forecast. E54 created a task-local,
public-safe forecast without changing the route or task authority.

**Impact:** documentation quality only. The explicit Issue and route satisfy
the engineering scope; this is not a reason to execute a different task.

## S2: a test can fail before exercising its named invariant

**Verified fact:** the first post-receipt fixture made the receipt its root
commit. The test passed because parent resolution failed before final-head
validation. It now uses a base -> receipt -> later-commit chain.

**Impact:** the corrected test is required by the copied-production mutation
matrix and catches a real weakening of the final-head guard.

## S1: local runtime asymmetry

**Verified fact:** Python 3.13.13 is present. `py -3.11` reports no suitable
runtime. No runtime was installed.

**Impact:** local tests provide a 3.13 check only; exact 3.11/3.13 Provider
matrix is a hard completion dependency.
