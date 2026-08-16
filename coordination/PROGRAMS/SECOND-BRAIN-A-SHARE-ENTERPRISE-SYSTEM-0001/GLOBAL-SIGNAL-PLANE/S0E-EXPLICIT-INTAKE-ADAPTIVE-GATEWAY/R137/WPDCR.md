# R137 Work Process and Coordination Report

agent_id: `CODEX`
source_agent: `CODEX` · reviewer: `GPT` · task: `CODEX-GLOBAL-SIGNAL-TOWER-R137-AUTHORITY-BOUND-LIVE-OBSERVATION-PROVIDER` · epoch: `137`

Planned difficulty was D3; current observed difficulty is D3. The hardest
mechanism is not issuing an HTTP request: it is keeping independently observed
objects, compact proof validity, and R136's release gate separate. Observable
evidence is the exact-object sequence, first/final main and PR comparisons,
static verifier, and R001-R044 adversarial tests.

The implementation changed the plan only by making endpoint-template
allowlisting explicit in the transport itself (rather than relying solely on
the public request object). This is a bounded hardening change within the
route's allowed source path. No private source, credential, user content,
store, scheduler, live service, or write endpoint was accessed.

Negative results: a compact caller-constructed proof, unknown provider,
expired proof, drifted main/PR/review/control-plane fingerprint, incomplete
pagination, malformed response and missing provider bundle all fail closed.
The provider records raw review facts but never labels a review sufficient.

Coordination boundary: Codex owns this bounded code/test/receipt work; GPT owns
architecture review and any later authorization decision; the user remains the
authority ceiling. Cross-agent impact is intentionally constrained: R136's
existing synthetic verifier seam remains test-only, while R137 adds one static
production verifier route.

Postflight still required: full local Phase-3/safety/scope validation, ordinary
commit/push, implementation PR, and exact-head Python 3.11/3.13 including the
public GitHub runtime proof. The next acceptance gate is GPT inspection of the
exact remote head. No formal release, merge or expansion is implied.

R2 remediation discovery: GPT exact-head review identified that proof fields
for PR number/state had not been tied back to bundle data, that the dedicated
workflow used GitHub's merge ref rather than explicit head checkout, and that a
recursive tree's truncation marker was not examined. The R2 changes bind those
PR facts into invalidation and verifier comparisons, assert the checkout head,
and reject truncated or malformed trees. Their evidence remains pending the new
exact-head CI; no policy or authority boundary changed.

R3 remediation discovery: the fixed R137 route would become stale at a successor
epoch, GitHub may expose a non-null merge commit SHA while an open PR remains
unmerged, and recursive tree completeness cannot be inferred when the API omits
its marker. The implementation now derives and validates the route exclusively
from the exact-main active-task pointer, treats the merge SHA as an independent
observed field, and accepts recursive trees only with explicit `truncated: false`.
All outcomes remain evidence-only and awaiting exact-head CI; no authority or
network surface expanded.

Postflight evidence is now available for reviewed implementation head
`f3b10eea8559dd4445d598ea7efa9b21a0700ac1`: R137 `31947566607`, S0E
`31947566608`, and Phase 3 `31947566619` each passed Python 3.11/3.13. R137
asserted that checkout HEAD exactly equalled the implementation head before its
two public runtime observations. This closes the process evidence only; GPT
review, no merge and all locks remain.
