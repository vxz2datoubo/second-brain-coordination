# R155 — Explicit User Value Evidence

Issue: #469

Base canonical main: `dd134db775ae9ecfd7366322b58bb2712a6b095e`

## Why this exists

R154 intentionally kept `user_value_score=50` because no canonical user-value authority existed. Its accepted independent review named a canonical user-value evidence source as the first future opportunity.

R155 fills only that missing dimension. It does not alter R151 priority classes, selection, release, R150/R149 preflight, R152 apply, S0C truth or owner-domain authority.

## Architecture

R155 deliberately does **not** trust a new R147 caller field. That would reopen the caller-score injection seam closed by R153/R154.

Instead it reuses the already-canonical human-facing Manual Signal Capture control Issue #456 as the declaration surface. A structured comment from the exact trusted connected-user principal is user-value attestation only. It never becomes Signal truth.

Current flow:

`R153 canonical S0C replay + owner gap + R150/R149`
→ accepted R154-neutral opportunity with `r154://ranking/...`
→ `signal_opportunity_materializer_current.py`
→ fixed #456 trusted-user `SIGNAL_USER_VALUE_DECLARATION/v1`
→ `ExplicitUserValueEvidence/v1`
→ R155 ranking-upgrade evidence bound to the exact R154 opportunity digest
→ retained R151 selection/release.

The old `signal_opportunity_materializer.py` remains retained R153 implementation and regression surface. New production consumers must use `signal_opportunity_materializer_current.py`. R155 tests scan current Control Tower production Python consumers so a new direct R153 import cannot silently bypass the successor entrypoint.

## Declaration contract

```yaml
schema: SIGNAL_USER_VALUE_DECLARATION/v1
declaration_id: <stable-id>
signal_id: <exact signal:...>
source: USER_EXPLICIT
value_class: LOW | NORMAL | HIGH
```

The v1 trusted human principal is mechanically bound to the real GitHub provenance observed on Issue #456:

- login: `vxz1datoubo`;
- immutable GitHub user id: `320840467`;
- repository association: `OWNER | MEMBER | COLLABORATOR`;
- `performed_via_github_app.slug`: `chatgpt-codex-connector`.

The repository itself is owned by `vxz2datoubo`, so requiring `author_association=OWNER` for `vxz1datoubo` would make the intended declaration path impossible. Exact user login + immutable id + allowed repository association + connector app is the v1 principal binding.

Untrusted actors, wrong ids, wrong apps, other issues, other Signals and free text are ignored. A malformed trusted declaration that targets the exact Signal fails closed.

The latest trusted exact-Signal declaration wins by GitHub comment id. GitHub comment bodies are editable, so the evidence digest represents the **currently observed** declaration content, not an immutable historical receipt. Stronger edit-history or immutable-declaration replay is a future hardening opportunity, not a v1 authority assumption.

## V1 score mapping

- LOW → 25
- NORMAL → 50
- HIGH → 75
- absent/unavailable → 50 neutral fallback

No numeric user score input exists. No CRITICAL/100 class exists in v1. P0/high-risk semantics stay in the existing priority/control gates.

A neutral fallback is not proof that the user explicitly declared NORMAL. `status` distinguishes verified declaration from provider/control-surface fallback.

## Privacy and inference boundary

R155 never uses:
- sentiment;
- repetition count;
- message length;
- urgency adjectives;
- behavioral history;
- hidden/private conversation state;
- inferred personality or preferences;
- Signal kind as a value proxy.

The evidence object persists only public-safe declaration identity/ref, value class, bounded score, policy version and digest. Raw conversation text is not copied.

## Trust composition

A #456 declaration alone cannot create an opportunity. The current wrapper first requires the retained R153 materializer to return `MATERIALIZED_FOR_R151`, then mechanically requires:
- a valid R151 opportunity;
- existing `r154://ranking/...` evidence;
- R154 neutral user value 50.

Only then may R155 replace that one numeric feature. All other rank features are retained from the accepted R154 opportunity.

This keeps R153's S0C replay and R145/R150/R149 checks upstream of user-value use.

## Observer / caller boundary

The authority-bearing R155 API exposes **no caller-supplied user-value observer/provider parameter**.

`observe_explicit_user_value()` always constructs its GitHub observer internally from the retained R137 provider. `signal_opportunity_materializer_current.py` calls that sealed observer path directly. Production callers therefore cannot mint HIGH/LOW evidence by supplying a fake object whose `_get_json()` fabricates Issue #456.

Unit tests may patch the private provider factory to exercise deterministic fixtures, but that test seam is not part of the production function signature. An adversarial regression requires caller attempts to pass `observer=` or `user_value_observer=` to fail at the API boundary.

## Availability semantics

If #456 or its GitHub observation is temporarily unavailable, R155 returns neutral 50 instead of inventing a value or blocking all idle opportunities. A malformed trusted exact-Signal declaration fails closed because it may represent a corrupted intended declaration.

This availability choice can temporarily suppress a previously explicit HIGH/LOW value. The evidence status must therefore remain visible so fallback 50 is never confused with verified NORMAL. A future sticky-last-verified policy would require its own versioned replay-safe design.

## Authority boundary

R155 evidence and ranking upgrade do not:
- create or mutate Signal truth;
- select an opportunity;
- release a task;
- create Issue/Route/Claim/worker slot;
- grant execution/domain/W3/merge authority;
- mutate owner-domain truth.

R151 remains the only selector/release authority.

## Exact implementation scope

Six additive files only:

1. `coordination/CONTROL-TOWER/signal_user_value.py`
2. `coordination/CONTROL-TOWER/signal_opportunity_materializer_current.py`
3. `coordination/CONTROL-TOWER/tests/test_signal_user_value.py`
4. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R155/PROJECT-PLAN.md`
5. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CONTROL-TOWER/R155/EXPLICIT-USER-VALUE.schema.json`
6. `.github/workflows/program-control-tower-r155-explicit-user-value.yml`

R153/R154 accepted files are not modified in this slice.

## Stop gate

- exact-head Python 3.11 + 3.13;
- R155 adversarial tests including real-shaped trusted principal and caller-injection rejection;
- retained R154/R153/R152/R151/R150/R149;
- full Control Tower;
- exact six-additive-file scope;
- no protected/live authority or S0C mutation;
- independent exact-head review through #453;
- no self-review and no merge before governed ACCEPT.

Completion signal:

`R155_EXPLICIT_USER_VALUE_EVIDENCE_READY_FOR_INDEPENDENT_REVIEW`
