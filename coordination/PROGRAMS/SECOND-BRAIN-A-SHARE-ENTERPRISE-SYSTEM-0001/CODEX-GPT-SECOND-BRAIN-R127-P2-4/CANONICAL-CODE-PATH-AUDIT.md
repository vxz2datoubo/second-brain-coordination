# R127 canonical code-path audit

agent_id: CODEX

| Canonical location | Observed current behavior | P2.4 contract consequence |
| --- | --- | --- |
| `src/integrated_offline_memory/retrieval.py:ContextAssembler.assemble` | Lexical, temporal, relation and provenance candidates call `_consider_candidate` before ranking/budget. | Provider-suggested candidates must enter only here, never after bundle assembly. |
| `retrieval.py:_consider_candidate` | It applies `_caller_observable` and `_admission_decision` through `_CandidateSet`. | It is the single P2.4 candidate gate; no provider or analogy bypass is allowed. |
| `retrieval.py:assemble_gpt_context_bundle_v1` | Current context has `analogies: ()`; evidence/support/counter and trust gate are computed separately. | Analogy may populate only this independent context lane and must not modify evidence/trust structures. |
| `memory_palace.py:retrieve_memory_palace` | Legacy callable output is stringified and concatenated into `expanded` before `QueryPlan`. | This is the only identified second-semantic-authority risk; replace/deprecate via the contract adapter. |
| `memory_palace.py:capture_text` | Capture delegates recall to `retrieve_memory_palace`, while omitted atoms use ContextAssembler exact admission proof. | P2.4 must preserve R125/R126 capture proof and not create a provider-dependent write path. |

Audit result: no existing P2.4 provider or analogy runtime is present. Existing `_consider_candidate` is reusable; legacy callable concatenation is not acceptable as the final provider contract.
