# Active Discovery And Improvement Record

`agent_id: CODEX`

## Accepted In Current Task

1. **Native process observation over repeated CIM scans.** The initial canary spent its time repeatedly launching PowerShell/CIM to inspect all processes. It did not breach a process cap, but it violated the responsiveness intent. E59 now uses Windows ToolHelp plus `GetProcessTimes` for PID/parent/creation-time discovery and avoids unrelated command-line collection.
2. **Separate ledger bytes from public claims.** The first authority test found that appending raw source bytes to the same mutable object used for a capability claim made JSON signing fail. The ledger now keeps bytes locally and emits digest/length only.
3. **P0 is split into history and present prevention.** Historic causality remains unknown; current bounded prevention is experimentally verified. These cannot be collapsed into one confident root-cause claim.

## Proposal Only

A persistent cross-machine authority service with OS-backed identity and lifecycle ownership would be stronger than E59's local synthetic host. It changes the authority boundary and is therefore `PROPOSAL_ONLY`, requiring a new GPT-approved task.
