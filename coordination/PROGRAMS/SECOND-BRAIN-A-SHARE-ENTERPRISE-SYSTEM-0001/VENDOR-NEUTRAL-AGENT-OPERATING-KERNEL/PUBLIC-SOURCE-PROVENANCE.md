# Public Source Provenance

> `agent_id: CODEX`
>
> `source_use: STRUCTURAL_RESEARCH_ONLY`

## Capture

| Field | Value |
|---|---|
| Claimed subject | Claude Opus 5 system prompt |
| Repository | `Eversmile12/leaked-llm-prompts` |
| Path | `Anthropic/opus-5.md` |
| Git blob SHA | `508fcbbb8f74c4aa7437f86b203bfc8a17267937` |
| SHA256 | `a6d256384c62a8ea4113a2edda7977aa1145be4abd1cd8c82b73c2c0eb87a111` |
| Bytes | 135669 |
| Logical lines | 1511 |
| Authenticity | `UNVERIFIED_THIRD_PARTY_CAPTURE` |
| License | `UNKNOWN` |
| Raw import | `PROHIBITED` |

The line count is 1510 line-feed characters with no final line feed, which
corresponds to 1511 logical lines. The repository does not contain the raw
capture or a reconstructed near-copy.

## Use Rule

The capture is not treated as an official specification. It was used only to
identify broad mechanism classes such as:

- memory retrieval before redundant questions;
- provenance-aware memory updates;
- tool discovery and routing;
- interruption recovery;
- progress communication;
- completion evidence.

Each retained mechanism was rewritten from first principles, compared with the
existing SuperBrain architecture, and encoded as new contracts and tests.

## Independent Support

The design was cross-checked against:

- official model prompting guidance for context, tool use, and verification
  behavior;
- ReAct for interleaving reasoning and action;
- MemGPT for tiered memory management;
- Reflexion for feedback-based agent improvement;
- Generative Agents for memory, reflection, and planning;
- AgentBench for multi-environment agent evaluation.

These sources support broad design directions. They do not prove that this
specific runtime is optimal, production-ready, or equivalent to any vendor
system.

## Excluded Content

The following capture content classes were intentionally excluded from the
common kernel:

- vendor identity and product promotion;
- commercial partner preference;
- proprietary app and tool names;
- political or ideological positioning;
- consumer-product persona;
- fixed vendor-specific response rituals;
- proprietary citation markup;
- raw text and distinctive narrative ordering.

Normative consumer policy is kept outside the cognition kernel. Project-level
operational integrity remains governed by W1 and domain controls.

## Links

- Public capture:
  `https://github.com/Eversmile12/leaked-llm-prompts/blob/main/Anthropic/opus-5.md`
- Public report:
  `https://www.ithome.com/0/981/688.htm`
- Official prompting guide:
  `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5`
- ReAct: `https://arxiv.org/abs/2210.03629`
- MemGPT: `https://arxiv.org/abs/2310.08560`
- Reflexion: `https://arxiv.org/abs/2303.11366`
- Generative Agents: `https://arxiv.org/abs/2304.03442`
- AgentBench: `https://arxiv.org/abs/2308.03688`
