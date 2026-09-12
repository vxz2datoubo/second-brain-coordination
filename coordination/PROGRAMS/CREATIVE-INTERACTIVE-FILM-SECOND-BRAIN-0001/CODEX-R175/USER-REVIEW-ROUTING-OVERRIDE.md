# User review-routing override

agent_id: `CODEX`

Effective immediately for this task and its closeout:

1. Codex and WorkBuddy continue long implementation rounds inside their own
   authorized, non-overlapping lanes. Ordinary commits and pushes are safety
   checkpoints, not review requests or reasons to stop.
2. Each executor must continuously verify its own work in a separate clean
   clone or task-owned verification workspace. This is named
   `EXECUTOR_CLEAN_REPRODUCTION`, never `INDEPENDENT_ACCEPTANCE`. It includes
   focused attacks, relevant end-to-end lifecycle paths, regression, scope,
   secret/network scans and exact-head identity checks appropriate to that
   executor's surface.
3. Codex and WorkBuddy do not send direct technical-review prompts or follow-up activation
   messages to any GPT review task.
4. At user-requested `收尾` or `同步`, the current executor publishes one complete GitHub
   review-ready package containing the exact head, baseline identities, changed
   contracts, executor-clean-reproduction receipts, limitations, rollback and
   next step. All work since the previous final review is bundled into one
   stage-level review rather than many small review rounds.
5. The user manually activates the independent GPT reviewer with a short
   project-level command. Detailed technical evidence remains in GitHub and is
   pulled by the reviewer from the canonical project entry.
6. GPT's role in that final round is cross-module and whole-project validation:
   reconcile interfaces, integration assumptions, authority boundaries,
   lifecycle gaps and coordination drift, then write exact corrective actions
   to GitHub. The next Codex/WorkBuddy round reads those durable findings before
   continuing.
7. Recommended activation command:

   `验算实时互动电影游戏项目最新待审候选，按 GitHub 接力协议执行。`

8. A direct executor-to-GPT message is allowed only after a new explicit user
   instruction asks Codex to send it. Delivery acknowledgement is never treated
   as completed review.

This routing override changes coordination only. It does not weaken exact-head,
role-separation, independent-review, merge-authorization or evidence gates.
