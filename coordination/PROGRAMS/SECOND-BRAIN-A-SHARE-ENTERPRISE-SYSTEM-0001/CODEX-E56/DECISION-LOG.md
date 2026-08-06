# E56 Decisions

## D-001: Fresh short task root

The verbose task identifier exceeded Windows path handling during the untracked plan-file attempt. E56 uses `CODEX-E56/` as its task root; the rejected long path never entered Git. This keeps the required first commit path deterministic and avoids changing Git configuration.

## D-002: No E55 branch integration

E55 is a frozen evidence source. E56 records each selected file's exact source commit, blob and content hash, then rewrites only the low-level mechanisms that the review identified as insufficient.

## D-003: Canonical vs environment evidence

Canonical output contains only deterministic production hashes, executed fixture outcomes, graph digest, normalized test result and normalized mutation summary. Python version, seed, job ID, time, stream hashes and archive IDs remain in environment evidence. The compare job requires canonical equality but binds, rather than equates, environmental evidence.

## D-004: Ordinary-caller policy boundary

Python is not a memory-safe security boundary. E56 prevents ordinary API callers from using public object state to substitute policy, seals or registries; a hostile actor able to introspect module internals remains outside the claimed model and is retained as an explicit UNKNOWN.

## D-005: Mutation execution is exclusive

E56 mutations intentionally alter a real E56 source/tool file for one named test, then restore the exact pristine bytes. They must never run concurrently with the ordinary test suite or another mutation. A transient concurrent test failure demonstrated that this is an execution-scheduler requirement, not a product assertion; `provider_runner.py` therefore runs its ordinary suite before a serial mutation matrix.

## D-006: Provider labels bind to observed runtime evidence

Artifact names, logical job names, GitHub job IDs and artifact IDs are not interchangeable. The independent contract supplies expected names; each environment artifact carries a hash-bound job-evidence payload with head, run ID and logical job name; the compare stage checks the actual Python version and hash seed too. The public collector later resolves GitHub job IDs and archive bytes from the exact workflow run.
