# Explanation layers for the program owner

The purpose of an explanation is to let the owner make a safe decision with the
least unnecessary cognitive load. It is not to hide uncertainty.

## Layer-specific language

### Explicit known

Use: “你已经明确要求……，所以本轮固定为……”。 Include the authority
reference and the observable result.

### Implicit known

Use: “我把……作为暂定推断（置信度 0.xx），因为……；它不会改变代码/预算。
若这个前提不成立，我会在……处停下。” Do not present it as user approval.

### Explainable unknown

Use a four-part mini-brief:

1. what it is in one sentence;
2. what changes if we adopt it;
3. benefit and cost/risk;
4. recommendation and the decision needed.

### Opaque unknown

Use: “底层细节不需要你现在判断；对你可见的是保护线、告警信号和停止条件。”
Still expose the exact evidence and owner if the item can block safety, money,
publication, or user rights.

## Always show these when material

- What the user needs to do now (or “你现在不需要做任何事”).
- Why it matters.
- Expected value / cost effectiveness.
- Remaining concern and the automatic stop condition.
- A copyable forwarding prompt only when another actor really must act.

## Never do these

- Call an executor's own test an independent review.
- Turn a score into a fact without its formula, unit, baseline, and threshold.
- Hide an unresolved uncertainty behind a confident status label.
- Require the owner to relay a message that an available agent-to-agent channel
  can send directly.
