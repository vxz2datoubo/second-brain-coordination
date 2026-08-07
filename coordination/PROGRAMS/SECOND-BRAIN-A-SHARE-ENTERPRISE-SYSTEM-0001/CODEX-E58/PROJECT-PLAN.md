# E58 Project Plan: Semantic Execution and Resource-Lifecycle Closure

## Task identity

| Field | Value |
| --- | --- |
| Task | `CODEX-E57-POST-RECEIPT-SEMANTIC-EXECUTION-VERIFIER-CAPABILITY-RAW-JSONL-AND-DUAL-PROVIDER-CLOSURE-0054-E58` |
| Route epoch | `60` |
| Canonical main at claim | `7ca1e12bec816db33efae31357e2e06b56b874d1` |
| Source input | Frozen E57 at `603768e08e27cf554f9a5ee231b13d51a563abe1` |
| Mode | `project_plan` |
| State | `research_only / synthetic fixtures / NO_TRADE` |

The goal is not to promote E57 as authority. E58 must make every accepted
semantic record depend on issued execution evidence and an externally distinct
verifier-only capability, while preserving exact raw-source ownership and
preventing task-owned process fan-out or orphan accumulation.

## Binding local resource rule

> LOCAL RESOURCE SAFETY IS BINDING: cap local workers/processes, disable nested
> parallelism, clean owned process trees on every exit path, prove return to
> baseline, and never kill unrelated Python processes.

| Limit | E58 implementation default |
| --- | --- |
| Single-agent task-owned Python processes | At most `6` including descendants |
| CPU-bound workers | At most `3`; P0 canary at most `2` |
| Local mutation and Provider work | Sequential by default |
| Nested parallelism | Forbidden; thread-count environment defaults set to `1` |
| Heavy-stage mutex | `SECOND_BRAIN_LOCAL_HEAVY_TEST_LOCK` required |
| CPU / RAM throttle | Stop new workers above `70%` sustained CPU or below `8 GiB` available RAM |
| Termination scope | Only PID + creation-time + command-digest registered task-owned trees |

No task-owned process may be launched before its baseline, ownership registry,
exit ledger, cleanup path and postflight check are in place. A cap violation or
an orphan after the grace period stops heavy execution and requires a visibility
packet and repair.

## Phased execution and recovery gates

### P0: local process incident investigation

1. Capture a read-only Python process baseline: PID, PPID, executable, command
   digest, creation time and ownership classification.
2. Inspect the `119`-process incident evidence and E57 process-launch paths;
   distinguish nested fan-out, leaked pools, repeated launches, duplicate
   daemons and cross-agent collision. Preserve `UNKNOWN` when evidence cannot
   distinguish a cause.
3. Implement an E58-local owned-process registry and Windows process-group or
   Job Object lifecycle abstraction. It must run a bounded two-worker canary
   through success, exception, timeout, cancellation and Ctrl-C paths.
4. Verify zero owned descendants and baseline return after every canary. Only
   then may a heavy local test/mutation stage be considered.

Acceptance: no unrelated process is terminated; process/worker caps are never
exceeded; spawn/exit ledger and root-cause confidence are published to Issue
`#194` and retained in E58 reports.

### P1: source selection and capability boundary

1. Create `E57-SOURCE-SELECTION.yaml` before importing any E57 code. Every
   selected path records source commit, Git blob SHA-1 and content SHA-256.
2. Reuse only low-level public-safe mechanisms whose threat model remains true;
   do not merge or cherry-pick E57.
3. Split the trusted issuer-command channel from a read-only verifier capability.
   Callers may submit inputs for verification but cannot select an issuer,
   register a verifier, issue a receipt or turn a local session into canonical
   authority.

Acceptance: direct construction, same-ID substitution, foreign issuer and
ordinary-import attacks fail under execution-derived evidence, not caller labels.

### P2: semantic execution records and source ownership

1. Issue evaluator receipts from registered evaluator/rule/input/run/outcome/
   output bindings, with verifier-visible transcript commitment.
2. Model proposition identity, polarity, subject/predicate/object, scope and
   time. A conflict requires proven opposition, not distinct source IDs.
3. Derive relation relevance from verified endpoint mappings or issued evaluator
   evidence; register and execute redaction policy/version/lineage.
4. Parse whole-source JSONL as a complete global byte partition, retaining blank
   lines, CR/LF terminators and deterministic isolated-surrogate classification.

Acceptance: every E57 audit blocker has a positive, negative and bypass test;
unsupported constructs fail closed as typed `UNKNOWN` or a stable authority error.

### P3: mutations, deterministic evidence and Provider

1. Add isolated genuine mutations for every surviving semantic or lifecycle
   bypass. Each mutation changes copied production bytes, executes, is killed,
   and restores exact bytes.
2. Run local product checks only after P0, sequentially under the heavy-stage
   mutex. Record process peak, CPU/RAM observations, spawned and cleaned PIDs.
3. Run remote Python `3.11` and `3.13` across seeds `0`, `1`, `777`, plus one
   compare job, for a final tested head and then for one receipt-only child.
4. Independently download all thirteen artifacts per run, verify archive and
   inner bytes, exact head bindings and canonical equality. Publish the literal
   anchor only after receipt evidence and real topology/hygiene verification.

Acceptance: two separate seven-job/thirteen-artifact Provider records, a
receipt-only direct child with no later commit, and independent GPT review. No
merge is authorized by this plan.

## Authorized work and boundaries

Writable paths are restricted to `CODEX-E58/**` and the one E58 workflow.
E57 and QCLAW E45 are read-only. No credentials, private configuration,
accounts, market data, orders, positions or trade execution may be accessed.
AMED A/B improvements remain task-local and tested; deployed process services,
cross-agent authority migration and canonical changes are C proposals only.

## Recovery

Before the receipt: freeze the Draft PR and route a successor if authority or
lifecycle tests fail. After the receipt: never correct in place; preserve the
branch and route a clean successor from the then-current canonical main. A local
resource violation stops launches and terminates only verified task-owned trees.
