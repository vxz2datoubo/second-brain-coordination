# E47 Reference (read-only, no E47 code copied)

E48 **reuses** the E47 candidate-knowledge pattern. We do **NOT** copy E47 code into
this branch; E47 lives in PR #207 and is the upstream of E48 L2.

## Identity (pinned)

- Repository: `vxz2datoubo/second-brain-coordination`
- Issue: 205 (E47 task)
- PR: #207 (E47 implementation, accepted as `ACCEPTED_CANDIDATE_KNOWLEDGE_PATTERN`)
- PR head branch: `qclaw/knowledge-digestion-staging-atomization-0028-e47`
- PR head SHA: `476d2a287cffb084c01b54c1d5e5eaf22016aac7`
- PR merge_commit_sha (per GitHub API, draft, not yet merged): `8800eb1abcd6cead49b8c851df6cbb5ed98c9a20`
- PR base SHA (= PR's parent at creation): `dbf4fd9933dfd12eeb1abe7e5c5818c5a1a77d38`
- semantic canary head: `ce4a259faf5e0b8fd5a6f6a498fe92b62f398c04`
- accepted content hash: `379ccafdf592ac75`

## Path of E47 module on PR #207 head

`coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/QCLAW-KNOWLEDGE-DIGESTION-STAGING-0028-E47/src/qclaw_e47_digest/`

Key files (observed from the PR file list and raw fetch):

- `src/qclaw_e47_digest/schema.py` — `SourceSnapshot`, `SourceSpan`, `Atom`, `Relation`,
  `Contradiction`, `Unknown`, `CandidateMemory`, `CandidateSkill`, `CandidateKnowledgePackage`,
  `EvidenceKind`, `AtomType`, `Confidence`, `RelationType`, `ContradictionClass`.
- `src/qclaw_e47_digest/engine.py` — `ingest_source`, `_make_span`, `source_extract`,
  `inference_atom`, `build_package`, `serialize_package`.
- `canary/build_digest_007_amend.py` — DIGEST-007 AMED canary builder (v11 hygiene revision).
- `tests/` — E47 unit tests.
- `packages/` — E47 produced packages.

## What E48 imports from E47 (intent)

E48 depends on E47 only via the public surface (frozen dataclasses + engine). It does not
copy, fork or amend E47 source. Specifically:

- E48 reuses `Atom`, `Relation`, `Contradiction`, `Unknown`, `CandidateMemory`,
  `CandidateSkill`, `CandidateKnowledgePackage` by **import**.
- E48 adds upstream `NormalizedSemanticView` (L1) that wraps the same `SourceSnapshot`
  and feeds the same `CandidateKnowledgePackage` pipeline.
- E48 adds downstream `KnowledgeGraphProjection` (L3) that consumes the E47 package's
  atoms + relations and produces a derived, library-neutral graph + optional GraphML.

If E47 public surface ever changes incompatibly, E48 must stop and report (no E48 fix
without E47 + GPT second-audit).

## How E48 will integrate

E48 contains a thin `E47 adapter` module `qclaw_e48_reconstruction.e47_adapter.py`
that:

- imports E47 from the path resolved at runtime (the PR #207 worktree location, NOT copied),
- builds an L1 view first, then passes `SourceSnapshot` (verbatim, byte-identical) into
  E47's `ingest_source`,
- reads back the produced `CandidateKnowledgePackage` and uses its atoms / relations as
  L3 input.

A test asserts that **L1 + E47 pipeline** still satisfies E47's content hash and
5-fold evidence separation, i.e. E48 does not regress E47.