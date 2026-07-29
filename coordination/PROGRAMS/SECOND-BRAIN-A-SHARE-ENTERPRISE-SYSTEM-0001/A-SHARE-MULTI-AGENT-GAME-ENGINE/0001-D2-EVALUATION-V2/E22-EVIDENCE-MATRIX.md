# E22 Executable Evidence Matrix

## Catalog Reconciliation

| Surface | Required | Executed | Mechanism |
| --- | ---: | ---: | --- |
| Synthetic scenarios | 72 | 72 | `scenario_catalog()` and `execute_scenario()` |
| Semantic invariants | 80 | 80 | `invariant_catalog()` with named failure oracle and `run_evaluation()` |
| Negative cases | 37 | 37 | `negative_catalog()` and fail-closed execution |
| Stateful episodes | 24 | 24 | `episode_catalog()` continuation runs |
| Counterfactual pairs | 36 | 36 | `counterfactual_catalog()` bounded synthetic pairs |
| Cross-family cases | 24 | 24 | each row re-activates a mutant and reruns its property |

## Mutation Registry And Kill Matrix

| Mutant | Fault family | Killer |
| --- | --- | --- |
| `MUT-001-ARRIVAL-IDENTIFIER-ORDER` | arrival priority replaced by identifier order | declared-arrival semantic relation |
| `MUT-002-LATE-REPLAY-RESERVATION` | terminal identity reservation removed | independent action/event binding and digest |
| `MUT-003-PARTIAL-PEER-COMMIT` | one peer leg committed | independent peer conservation |
| `MUT-004-EXTERNAL-FLOW-OMITTED` | external offset removed | independent external-flow accounting |
| `MUT-005-STORED-HASH-TRUST` | stored state/hash trusted | independent reconstruction digest and inventory delta |
| `MUT-006-FORWARD-CAUSAL` | forward/self causal parent | independent causal DAG check |
| `MUT-007-CONFLICT-OWNERSHIP-BYPASS` | claim ownership bypass | independent conflict ownership check |
| `MUT-008-NOMINAL-BOUNDARY` | exact primitive/enum/carrier fallback | fail-closed exact-boundary check |

All eight mutations changed an observable behavior and were `KILLED`. The
surviving-mutant inventory is empty; that means only that these eight selected
faults were killed, not that the SUT is defect-free.

## Metamorphic Properties

`MP-001` fixed-arrival permutation, `MP-002` identifier alpha-renaming,
`MP-003` episode continuation, `MP-004` duplicate/replay rejection,
`MP-005` peer conservation, `MP-006` external-flow accounting, `MP-007` tamper
detection, and `MP-008` exact primitive/enum/carrier boundary rejection all
passed in the full synthetic runner.

## Clean Archive Evidence

The substantive commit `696ed005add87301f5f1bdbb13732d154a58da8e` was exported
to three independent Git archive roots. `run_evaluation_v2.py --full` exited
`0` for each process seed and produced the identical canonical report SHA256:

`181ee5012131701e9950f5cbf132c8916958caf6e3cc87b98bfaa67d11d588ef`

| Seed | Elapsed ms | stderr SHA256 |
| ---: | ---: | --- |
| 1 | 2979 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 7 | 2536 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 97 | 2898 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
