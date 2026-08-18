# DeepSeek Harness Upstream Identity Verification

- status: `IDENTITY_AND_ARCHITECTURE_SURFACE_PASS / RUNTIME_SMOKE_PENDING`
- verified_at_design_time: `2026-08-15`
- verifier: `GPT`
- usage: `ARCHITECTURE_EVIDENCE_ONLY / NO_RUNTIME_AUTHORIZATION`

## 1. Canonical repository

GitHub connector exact repository lookup resolves:

- organization: `deepseek-ai`
- repository: `deepseek-harness`
- visibility: `public`
- archived: `false`
- default branch: `master`

This resolves the earlier search ambiguity caused by unrelated repositories using similar names.

## 2. Exact snapshot

Current `refs/heads/master` at verification time:

`47f943859bef60e4160492346772ded9b24f765a`

The exact commit message is:

`release: dsh@0.1.0-rc.5 & publish the dsh family publicly`

Root `package.json` on this exact commit declares:

- root version: `0.1.0-rc.5`
- license: `MIT`
- package manager: `pnpm@11.7.0`
- Node engines: `^22.19.0 || >=24.0.0`

GitHub Releases endpoint returned no latest release and the tags endpoint returned an empty list at verification time. Therefore the implementation pin should bind **exact commit SHA + package family version**, not assume a Git tag/release object exists.

## 3. License

Repository `LICENSE` on the exact commit is MIT License, copyright 2026 DeepSeek.

## 4. Official maturity warning

Official README states:

- DeepSeek Harness (`dsh`) is an open-source agent harness developed by DeepSeek AI;
- architecture uses Cordis and “everything is a plugin”;
- project is currently a **developer preview**;
- compatibility-breaking changes are expected.

Architectural consequence:

- exact-version pin is mandatory;
- domain code may not import concrete Harness providers;
- our Adapter owns compatibility shielding;
- latest upstream is a radar/canary target, never an automatic production upgrade.

## 5. Verified architecture surface

Official architecture documentation says:

- Cordis plugins contribute services, typed events and reversible effects to a shared context;
- model adapter, tool registry, session log and agent loop are plugins and can be replaced through configuration;
- profiles and bundles compose the runtime at boot;
- durable `SessionEvent` log is the source of model-visible context and replay/fork/resume/persistence projections;
- capability seams separate Service Definition, Service Provider and Consumer roles;
- extension plugins should depend on Service Definitions rather than concrete providers.

This strongly supports our Adapter-first topology.

## 6. Verified product API/capability families

Official `packages/README.md` labels these as Product / stable API families at the verified snapshot, including:

- core/session/tools/agent/agent-loop
- llm
- subprocess
- shell
- terminal
- code-runtime
- sandbox
- fs
- lsp
- skill
- context
- subagent
- jobs
- workflow
- web
- attachment/spill
- plan/preset/guard/bundle
- session/session-query
- settings/credentials/storage/workspace
- sdk
- acp
- interaction
- boot/host/client

The same document states:

> Extension plugins depend on Service Definitions, never concrete providers.

This is adopted as a hard integration rule in our architecture.

## 7. Harness concepts we will reuse vs refuse

### Reuse

- plugin composition;
- Service Definition / Provider / Consumer seams;
- append-only runtime session events;
- workflow / jobs / subagent mechanisms;
- tool guarded execution pipeline;
- cancellation/retry/runtime lifecycle hooks;
- SDK / ACP / interaction seams where appropriate;
- provider replaceability through configuration.

### Refuse as authority transfer

Harness session events do not become W3 knowledge truth.
Harness skill registry does not become Formal Skill authority.
Harness workflow does not become Signal Tower Mission authority.
Harness guards do not replace Control Tower or W7.
Harness model/tool output does not become Evidence truth without domain/verification contracts.

## 8. Remaining implementation gates

Identity and public architecture surface are now sufficiently verified for H0 design.

Before H2 runtime PoC still required:

1. reproducible clean install/pack smoke on pinned `47f943... / 0.1.0-rc.5`;
2. exact package names used by our Adapter;
3. generated/public service type signatures for the exact packages we consume;
4. Windows/local compatibility on our execution environment or isolated CI;
5. provider-specific smoke tests;
6. pinned-vs-latest compatibility test design;
7. rollback/no-residual-process test.

Verdict:

`UPSTREAM_IDENTITY_PASS / ARCHITECTURE_SURFACE_PASS / RUNTIME_BINDING_NOT_YET_AUTHORIZED`
