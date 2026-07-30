# GPT Review Packet

## Task

Review `VENDOR-NEUTRAL-AGENT-OPERATING-KERNEL-PROPOSAL-0011` as a
candidate PEOS 0010 runtime protocol.

Actual executor: `CODEX`

Requested reviewer: `GPT`

Status: `SUCCESS_WITH_FINDINGS / IMPLEMENTED_CANDIDATE_PENDING_GPT_REVIEW`

## User Decision

The user authorized Codex to complete this candidate workline before GPT review
and requested one combined report afterward. The existing E24 active route and
PR #106 were explicitly isolated and not modified.

## Goal

Extract generalizable mechanisms from a publicly circulated 1511-line
third-party capture while excluding:

- vendor identity and product promotion;
- partner preference;
- proprietary environment and tool names;
- political or ideological positioning;
- consumer-product persona.

Retain operational integrity controls required by a correct engineering system:
truthful evidence, explicit authority, provenance, idempotency, rollback,
completion evidence, and credential isolation.

## Source Status

```yaml
authenticity: UNVERIFIED_THIRD_PARTY_CAPTURE
license_status: UNKNOWN
logical_lines: 1511
bytes: 135669
git_blob_sha: 508fcbbb8f74c4aa7437f86b203bfc8a17267937
sha256: a6d256384c62a8ea4113a2edda7977aa1145be4abd1cd8c82b73c2c0eb87a111
raw_import_allowed: false
```

No raw or reconstructed prompt is committed.

## Architecture Decision

The result is a runtime protocol under PEOS 0010, not a second cognitive OS.

Existing ownership remains:

- W1: task authority and approvals;
- W3/Phase 3: memory, evidence, conflict, UNKNOWN, retrieval, learning;
- W8: Agent and capability orchestration;
- W10: TaskContext and DecisionEpisode;
- existing domain owners: A-share facts, probability, risk, capital, orders.

## Delivered

- Vendor-neutral runtime Prompt.
- Ten public contracts and a complete JSON Schema.
- Deterministic authority resolver.
- Eight-lane epistemic provenance.
- Candidate-only memory proposal.
- Provider-neutral capability routing.
- Idempotent checkpoint recovery.
- Requirement-to-evidence completion auditing.
- PEOS addendum and v1.5 candidate integration index.
- Named project Skill.
- 73 automated tests and validation receipts.

## Important Invariants

1. `MemoryWriteProposal.authority_write=false`.
2. `ModelBehaviorProfile.authority_overrides=[]`.
3. Provider display name cannot affect route score or hash.
4. Inference cannot become an observation.
5. UNKNOWN has confidence 0.
6. Same-rank authority conflicts fail closed.
7. Recovery protects completed side effects by idempotency key.
8. Narrow tests cannot prove broad completion.
9. Runtime activation is disabled.
10. `research_only / NO_TRADE` remains unchanged.

## Verification

```text
tests: PASS 73/73
test_output_sha256: 740adf67176d4fe1dd6c459353c5f5a7b1ffbb44d1e9c0e79ab0e4acadde0139
python_ast: 18 OK
json: 1 OK
yaml: 6 OK
strict_yaml_duplicate_keys: 6 OK
changed_file_secret_scan_matches: 0
common_kernel_named_vendor_matches: 0
```

Tested commit:

`216ff0e053907d5eecad9fe4245cc163991cb69f`

Tested tree:

`663e7392f31c2d70e19042e7a942ea2ccef4c2d2`

## Findings

1. The transferable value of a giant system Prompt is mainly stateful contracts
   and invariants, not its length or brand persona.
2. “Remember only explicit user statements” is too weak for a learning system.
   Typed provenance supports inference without contaminating user memory.
3. Model quirks should live in versioned behavior profiles, not canonical
   project instructions.
4. A common Prompt alone is insufficient. Schema, tests, checkpoints, and
   ownership boundaries are required.
5. The reference router is semantically valid but not production-calibrated.

## Review Questions

GPT should decide:

1. Accept this as a PEOS 0010 runtime subprotocol, revise it, or reject it?
2. Is the proposed authority precedence correct for this repository?
3. Which owners implement W1, W3/Phase 3, and W8 adapters?
4. Should the candidate v1.5 integration index become canonical after revision?
5. What cross-model evaluation threshold is required before feature-flag shadow
   activation?

## Prohibited Review Outcome

Do not treat this candidate as already canonical, production-ready, or enabled.
Do not merge automatically. Do not use it to bypass existing active routes,
memory governance, A-share risk controls, or trading approval.

## Rollback

Close the Draft PR or revert its candidate commits. No canonical blueprint,
memory, service, or trading state has been modified.
