# Conversational Long-Term Memory Research Ledger v1.0

> `module: CONVERSATIONAL-LONG-TERM-MEMORY-0021`
>
> `agent_id: GPT`
>
> `research_cutoff_for_this_ledger: 2026-08-11`
>
> `rule: implementation MUST re-verify volatile product documentation at execution time`

## 1. Purpose

This ledger records the primary sources and engineering patterns used to design the W3 Conversational Long-Term Memory module. It separates:

- OFFICIAL_PRODUCT_DOC;
- PEER_REVIEWED;
- PREPRINT;
- STANDARD;
- ENGINEERING_PATTERN;
- DESIGN_INFERENCE.

No external benchmark result is treated as a production guarantee for this Second Brain.

## 2. OpenAI official product capabilities

### 2.1 Memory FAQ

Type: `OFFICIAL_PRODUCT_DOC / VOLATILE`

Source:

`https://help.openai.com/en/articles/8590148-memory-in-chatgpt-faq`

Current findings as of 2026-08-11:

- ChatGPT Memory can use relevant context from chats, files and connected apps when enabled and available.
- Saved memories and chat-history-derived context are different mechanisms.
- Chat history does not retain every detail from past chats.
- OpenAI explicitly states that ChatGPT does not search history on every request; it does so when relevant context is likely to improve the response.
- The improved memory system is evolving, so implementation must not freeze product behavior into architecture assumptions.

Design implication:

`ChatGPT Native Memory = HOT_PERSONALIZATION_CACHE / AUXILIARY_RECALL`, not W3 durable audit authority.

### 2.2 Projects in ChatGPT

Type: `OFFICIAL_PRODUCT_DOC / VOLATILE`

Source:

`https://help.openai.com/en/articles/10169521-projects-in-chatgpt`

Current findings:

- Project memory can keep context anchored to a project.
- Project-only memory intentionally prevents cross-project context use.

Design implication:

Projects are useful interaction cockpits and isolation domains, but a user's cross-project autobiographical memory must remain in W3 with explicit scoped retrieval rather than being duplicated into every Project.

### 2.3 Scheduled Tasks in ChatGPT

Type: `OFFICIAL_PRODUCT_DOC / VOLATILE`

Source:

`https://help.openai.com/en/articles/10291617-tasks-in-chatgpt`

Current findings:

- Tasks support recurring/background work.
- Tasks can use connected apps where account/workspace permissions allow.
- A task created in a Project that contains files currently cannot access those project files.
- Tasks do not provide a basis for assuming full account-wide raw conversation capture.

Design implication:

Scheduled Tasks are a `BACKGROUND_CONSOLIDATION_TRIGGER`, not the sole ingestion path. Hot-path capture remains necessary and every task output must record source coverage.

### 2.4 Apps in ChatGPT

Type: `OFFICIAL_PRODUCT_DOC / VOLATILE`

Source:

`https://help.openai.com/en/articles/11487775-connectors-in`

Current findings:

Apps can connect external services and information to ChatGPT for search/reference and, depending on the app and permissions, actions or synced content.

Design implication:

Apps are an integration surface for W3 recall, not a guarantee that every response will execute the same retrieval path.

### 2.5 Developer mode and MCP apps

Type: `OFFICIAL_PRODUCT_DOC / VOLATILE`

Source:

`https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt-beta`

Current findings:

- Full MCP support including modify/write actions is in beta for specified managed-workspace plans.
- Product availability, UI and permissions are explicitly subject to change.

Design implication:

The architecture has three integration levels: Native/Soft Guarantee, MCP App, and Hard-Guarantee Gateway. Formal memory architecture must not depend on a beta product feature remaining unchanged.

## 3. Long-term agent memory research

### 3.1 Generative Agents: Interactive Simulacra of Human Behavior

Type: `PEER_REVIEWED / ACM UIST 2023; arXiv source available`

Authors: Park et al.

Source:

`https://arxiv.org/abs/2304.03442`

Useful pattern:

- store a record of experiences;
- retrieve relevant memories dynamically;
- synthesize higher-order reflections;
- use reflection and memory to influence future behavior.

Adopt:

`Episode → Retrieval → Reflection → Future Context`.

Do not adopt:

simulation believability as our optimization target. Our target is truthful, controllable personal assistance.

### 3.2 MemGPT: Towards LLMs as Operating Systems

Type: `PREPRINT / influential engineering-research pattern`

Authors: Packer et al.

Source:

`https://arxiv.org/abs/2310.08560`

Useful pattern:

hierarchical/virtual context management across small fast context and larger external memory.

Adopt:

separate hot context from durable W3 memory and fetch only task-relevant context.

Do not adopt blindly:

MemGPT implementation details as W3 canonical contracts.

### 3.3 LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory

Type: `PEER_REVIEWED / ICLR 2025`

Authors: Wu et al.

Source:

`https://proceedings.iclr.cc/paper_files/paper/2025/hash/d813d324dbf0598bbdc9c8e79740ed01-Abstract-Conference.html`

Core evaluation dimensions:

- information extraction;
- multi-session reasoning;
- temporal reasoning;
- knowledge updates;
- abstention.

Architecture insight:

memory can be evaluated as `indexing → retrieval → reading` rather than a single black box.

Adopt:

- session decomposition;
- time-aware query handling;
- explicit knowledge-update and abstention tests.

### 3.4 LoCoMo: Evaluating Very Long-Term Conversational Memory of LLM Agents

Type: `PEER_REVIEWED / ACL 2024`

Authors: Maharana et al.

Source:

`https://aclanthology.org/2024.acl-long.747/`

Useful insight:

Long-term conversation requires more than isolated fact recall. Temporal and causal dynamics across many sessions remain difficult even with long context or RAG.

Adopt:

multi-session episode timelines and long-range temporal/causal test cases.

### 3.5 LoCoMo-Plus: Beyond-Factual Cognitive Memory Evaluation Framework for LLM Agents

Type: `PEER_REVIEWED / ACL 2026`

Authors: Li et al.

Source:

`https://aclanthology.org/2026.acl-long.1150/`

Useful insight:

A personal assistant may need to apply implicit constraints from earlier user state, goals or values even when the later query does not repeat the original wording.

Adopt:

`IMPLICIT_CONSTRAINT / CONSTRAINT_CONSISTENCY` evaluation.

Control:

An implicit constraint may affect an answer only when provenance, scope, temporal validity and confidence are sufficient. This must not become excuse for hidden profiling or unsupported mind-reading.

### 3.6 Preference-Aware Memory Update for Long-Term LLM Agents

Type: `PEER_REVIEWED / Findings ACL 2026`

Authors: Sun et al.

Source:

`https://aclanthology.org/2026.findings-acl.38/`

Useful topic:

long-term preference memory update rather than static preference storage.

Adopt only as research input:

user preference should evolve through explicit update/correction/version chains, not static profile overwrite.

### 3.7 A-MEM: Agentic Memory for LLM Agents

Type: `PREPRINT 2025`

Authors: Xu et al.

Source:

`https://arxiv.org/abs/2502.12110`

Useful pattern:

structured notes, contextual descriptions, tags, dynamic links and memory evolution as new evidence arrives.

Adopt:

memory linking and evolving derived context.

Hard control:

historical content is not silently rewritten. Evolution must generate versioned derived views or explicit update/supersession events.

### 3.8 HippoRAG

Type: `PREPRINT / research system`

Authors: Gutiérrez et al.

Source:

`https://arxiv.org/abs/2405.14831`

Useful pattern:

graph-based relational retrieval can complement dense retrieval for multi-hop knowledge integration.

Adopt conditionally:

graph retrieval only after benchmark evidence shows incremental value over lexical/entity/time baselines.

Do not adopt:

biological analogy as evidence of correctness.

### 3.9 MemOS

Type: `PREPRINT 2025`

Source:

`https://arxiv.org/abs/2505.22101`

Useful topic:

memory as a first-class managed resource with lifecycle and heterogeneous memory representations.

Adopt conceptually:

memory lifecycle, governance and traceable representation are first-class architecture concerns.

Do not create a competing W3 runtime from MemOS terminology.

## 4. Provenance and temporal architecture

### 4.1 W3C PROV-O

Type: `W3C RECOMMENDATION / STANDARD`

Source:

`https://www.w3.org/TR/prov-o/`

Useful pattern:

provenance can be represented through Entities, Activities, Agents and derivation/attribution relationships.

Adopt:

Every derived memory must be traceable to its Episode/Source and the derivation process.

Do not adopt unnecessarily:

full RDF/OWL machinery where existing W3 contracts can express the same provenance more simply.

### 4.2 Bitemporal History

Type: `ENGINEERING_PATTERN`

Core pattern:

separate when a fact/state was valid in the modeled world from when the system recorded/knew it.

Adopt:

- valid_from / valid_to;
- recorded_at / updated_at;
- current vs historical query semantics.

This is mandatory for preference corrections, temporary states and retroactive user clarification.

### 4.3 Event Sourcing

Type: `ENGINEERING_PATTERN`

Useful pattern:

preserve important historical changes as events and derive current projections instead of silently replacing history.

Adopt selectively:

Correction, Supersession, Resolution and Revocation are first-class changes. W3 need not become a pure event-sourced architecture if existing runtime contracts already provide equivalent audit/version behavior.

## 5. Existing repository evidence that constrains design

### 5.1 Phase 3 canonical candidate memory

PR #57 established an existing integrated candidate-memory path. CLTM must extend it rather than build a second store/query/context runtime.

### 5.2 Issue #38 / #59 / #60

These already define full-knowledge gateway, knowledge atomization and hybrid long-term retrieval. CLTM is a new high-value Source and usage path inside those authorities.

### 5.3 MODULE_0020 / Issue #216

`KNOWLEDGE-SOURCE-SEMANTIC-RECONSTRUCTION-AND-GRAPH-PROJECTION-0020` already owns the derived normalization/projection path for noisy ASR/OCR/oral sources.

CLTM 0021 reuses it when needed.

### 5.4 E61 / Issue #209

Current active Codex route is establishing real durable formal-knowledge authority. CLTM must not unlock formal PROJECT/GLOBAL writes before the E61 gate is accepted.

## 6. Design conclusions

1. Conversation is a first-class Source, not a side log.
2. Preserve Episode/provenance; do not replace experience with lossy summaries.
3. Separate current knowledge from historical versions.
4. Use bitemporal validity for personal-state evolution.
5. Use correction/supersession instead of silent overwrite.
6. Retrieval must combine lexical/entity/time/status with vector/graph where useful.
7. Retrieval and trust are separate stages: relevance does not imply validity or permission.
8. Native ChatGPT memory improves experience but does not replace W3 durable authority.
9. Scheduled consolidation complements but cannot replace hot-path capture.
10. Cross-project personalization must be scoped, not copied into every project.
11. Evaluation must include implicit constraints, temporal update, abstention, leakage and provenance, not just factual recall.
12. Complexity is earned by benchmark value. Vector databases, graph services, Supabase and MCP are not prerequisites for the first vertical slice.
